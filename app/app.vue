<script setup lang="ts">
// Uma página: conecta ao Companion pelo Web Bluetooth, mostra o estado (os olhos da tela imitam os de verdade), a
// bateria e os superpoderes, e ajusta volume e brilho. Os comandos são os mesmos do plugin (docs/protocolo.md).
import {
  COMMAND_UUID,
  SERVICE_UUID,
  STATES,
  STATE_INFO,
  STATUS_UUID,
  brightnessCommand,
  hex,
  parseStatus,
  volumeCommand,
  type State,
  type Status,
} from '#shared/protocol'

type Conn = 'idle' | 'unsupported' | 'connecting' | 'ready' | 'lost' | 'failed'
const CONN_TEXT: Record<Conn, string> = {
  idle: 'Desconectado',
  unsupported: 'Este navegador não tem Web Bluetooth. Use o Chrome ou o Edge, no computador ou no Android.',
  connecting: 'Conectando…',
  ready: 'Conectado',
  lost: 'A conexão caiu. O Companion está ligado e por perto?',
  failed: 'Não deu para conectar. Ligue o Companion (segure o botão por 1 s) e tente de novo.',
}

const conn = ref<Conn>('idle')
const status = ref<Status | null>(null)
const preview = ref<State>('thinking') // sem conexão, os botões mudam só os olhos da tela
const volume = ref(60)
const brightness = ref(40)
let sliding = false // não puxa o controle da mão de quem está arrastando
const { baseURL } = useRuntimeConfig().app
let device: BluetoothDevice | undefined
let commandChar: BluetoothRemoteGATTCharacteristic | undefined
let statusChar: BluetoothRemoteGATTCharacteristic | undefined

const ready = computed(() => conn.value === 'ready')
const face = computed<State | 'off'>(() => (ready.value ? (status.value?.state ?? 'off') : preview.value))
const battery = computed(() => {
  const s = status.value
  if (!s) return ''
  if (s.bat === null) return 'Sem bateria (USB)'
  const volts = (s.mv / 1000).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return `Bateria ${s.bat}% · ${volts} V`
})

onMounted(() => {
  if (!navigator.bluetooth) conn.value = 'unsupported'
})

// O Chrome recusa duas operações GATT ao mesmo tempo: tudo passa por esta fila
let queue: Promise<unknown> = Promise.resolve()
function gatt<T>(op: () => Promise<T>): Promise<T> {
  const next = queue.then(op)
  queue = next.catch(() => {})
  return next
}

async function connect() {
  conn.value = 'connecting'
  try {
    device = await navigator.bluetooth.requestDevice({ filters: [{ services: [SERVICE_UUID] }] })
    device.addEventListener('gattserverdisconnected', onLost)
    const server = await device.gatt!.connect()
    const service = await server.getPrimaryService(SERVICE_UUID)
    commandChar = await service.getCharacteristic(COMMAND_UUID)
    statusChar = await service.getCharacteristic(STATUS_UUID)
    statusChar.addEventListener('characteristicvaluechanged', () => refresh())
    await statusChar.startNotifications()
    await refresh()
    conn.value = 'ready'
  } catch (e) {
    // fechar a janela de escolha do navegador não é erro
    conn.value = (e as DOMException).name === 'NotFoundError' ? 'idle' : 'failed'
  }
}

function disconnect() {
  device?.removeEventListener('gattserverdisconnected', onLost)
  device?.gatt?.disconnect()
  status.value = null
  conn.value = 'idle'
}

function onLost() {
  status.value = null
  conn.value = 'lost'
}

// A notificação só avisa que mudou; o JSON vem inteiro pela leitura, qualquer que seja o MTU
async function refresh() {
  if (!statusChar) return
  try {
    const value = await gatt(() => statusChar!.readValue())
    const s = parseStatus(new TextDecoder().decode(value))
    if (!s) return
    status.value = s
    if (!sliding) {
      volume.value = s.vol
      brightness.value = s.bri
    }
  } catch {
    // a conexão caiu no meio: o gattserverdisconnected cuida
  }
}

async function send(text: string) {
  if (!commandChar) return
  try {
    await gatt(() => commandChar!.writeValueWithResponse(new TextEncoder().encode(text)))
  } catch {
    // idem
  }
}

function setState(s: State) {
  preview.value = s
  send(s)
}

function startSlide() {
  sliding = true
}

function slid(text: string) {
  sliding = false
  send(text)
}

function powerOff() {
  if (confirm('Desligar o Companion? Para ligar de novo, segure o botão dele por 1 s.')) send('off')
}
</script>

<template>
  <main>
    <header class="top">
      <img :src="`${baseURL}logo.svg`" alt="" width="52" height="52" />
      <div>
        <h1>Claude Code Companion</h1>
        <p class="muted">Os olhos do Claude na sua mesa</p>
      </div>
    </header>

    <section class="card hero">
      <!-- o mascote em pixel art: corpo 16×10, olhos de 1×2 com os LEDs atrás de um difusor branco -->
      <svg
        class="clawd"
        :class="face"
        viewBox="-1 -1 18 12"
        role="img"
        :aria-label="`Companion com os olhos ${face === 'off' || face === 'idle' ? 'apagados' : STATE_INFO[face].label.toLowerCase()}`"
      >
        <defs>
          <filter id="glow" x="-300%" y="-150%" width="700%" height="400%">
            <feGaussianBlur stdDeviation="0.35" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path class="body" d="M2 0h12v4h2v2h-2v2h-1v2h-1v-2h-1v2h-1v-2H6v2H5v-2H4v2H3v-2H2V6H0V4h2z" />
        <rect class="eye" x="4" y="2" width="1" height="2" />
        <rect class="eye" x="11" y="2" width="1" height="2" />
      </svg>
      <p class="state">
        <template v-if="face === 'off'">Olhos apagados</template>
        <template v-else>
          <strong>{{ STATE_INFO[face].label }}</strong>
          <span class="muted"> · {{ STATE_INFO[face].hint }}{{ ready ? '' : ' (prévia)' }}</span>
        </template>
      </p>
      <div class="connect">
        <button v-if="!ready" :disabled="conn === 'unsupported' || conn === 'connecting'" @click="connect">
          Conectar ao Companion
        </button>
        <button v-else class="ghost" @click="disconnect">Desconectar</button>
        <span class="status" :class="conn">{{ CONN_TEXT[conn] }}</span>
        <span v-if="battery" class="battery">{{ battery }}</span>
      </div>
    </section>

    <section class="card">
      <h2>Testar os olhos</h2>
      <div class="states">
        <button v-for="s in STATES" :key="s" class="ghost state-btn" :class="{ on: face === s }" @click="setState(s)">
          <span class="dot" :class="s" />{{ STATE_INFO[s].label }}
        </button>
      </div>
      <p v-if="!ready" class="muted hint">Sem conexão, os botões mudam só os olhos da tela.</p>
    </section>

    <section class="card">
      <h2>Som e luz</h2>
      <label class="slider">
        <span>Volume</span>
        <input
          v-model.number="volume"
          type="range"
          min="0"
          max="100"
          :disabled="!ready"
          @input="startSlide"
          @change="slid(volumeCommand(volume))"
        />
        <output>{{ volume }}</output>
      </label>
      <label class="slider">
        <span>Brilho</span>
        <input
          v-model.number="brightness"
          type="range"
          min="5"
          max="100"
          :disabled="!ready"
          @input="startSlide"
          @change="slid(brightnessCommand(brightness))"
        />
        <output>{{ brightness }}</output>
      </label>
      <div class="power-off">
        <button class="danger" :disabled="!ready" @click="powerOff">Desligar o Companion</button>
        <span class="muted">Para ligar, segure o botão dele por 1 s.</span>
      </div>
    </section>

    <section class="card">
      <h2>Superpoderes</h2>
      <div class="powers">
        <div>
          <h3>Cabeça</h3>
          <p>
            Três pinos (VLED, dados, GND) que continuam a corrente dos olhos: LEDs endereçáveis ligados ali acendem
            junto. Um chapéu de Natal, uma antena, uma coroa.
          </p>
        </div>
        <div>
          <h3>Costas</h3>
          <p>
            Conector I2C no padrão Qwiic/STEMMA QT (GND, 3V3, SDA no D4, SCL no D5) para sensores e telinhas.
            <span class="muted">
              <template v-if="!status">Conecte para ver o que está ligado.</template>
              <template v-else-if="status.i2c.length">Encontrados: {{ status.i2c.map(hex).join(', ') }}.</template>
              <template v-else>Nada ligado agora.</template>
            </span>
          </p>
        </div>
      </div>
    </section>

    <section class="card">
      <h2>Ligar ao Claude Code</h2>
      <ol class="steps">
        <li>
          Instale o plugin:
          <pre><code>claude plugin marketplace add patogordo/ClaudeCodeCompanion
claude plugin install companion@companion</code></pre>
        </li>
        <li>
          Abra o Claude Code. A ponte Bluetooth sobe sozinha e procura o Companion; no macOS, permita o Bluetooth para o
          terminal na primeira vez.
        </li>
        <li>Os olhos passam a acompanhar o Claude. O portal pode ficar aberto ao mesmo tempo.</li>
      </ol>
      <table>
        <tbody>
          <tr v-for="s in STATES" :key="s">
            <td><span class="dot" :class="s" />{{ STATE_INFO[s].label }}</td>
            <td class="muted">{{ STATE_INFO[s].when }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <footer class="muted">
      Projeto independente, sem relação com a Anthropic. Claude é marca da Anthropic.
      <template v-if="status"> Firmware {{ status.fw }}.</template>
    </footer>
  </main>
</template>

<style>
:root {
  --bg: #111315;
  --surface: #1b1e21;
  --line: #2c3035;
  --text: #e8e6e3;
  --muted: #9aa0a6;
  --brand: #d97757;
  --clawd: #d97757;
  --diffuser: #f4f1ea;
  --ok: #5fc27e;
  --danger: #ff5a5a;
  --yellow: #ffbe00;
  --orange: #ff4800;
  --green: #00e65a;
  --blue: #2f7bff;
  --red: #ff1f1f;
  color-scheme: dark;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font:
    16px/1.5 system-ui,
    sans-serif;
}
main {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 16px 64px;
}
h1 {
  margin: 0;
  font-size: 1.6rem;
}
h2 {
  margin: 0 0 12px;
  font-size: 1.15rem;
}
h3 {
  margin: 0 0 4px;
  font-size: 0.95rem;
  color: var(--brand);
}
p {
  margin: 0;
}
.muted {
  color: var(--muted);
  font-size: 0.9rem;
}
.top {
  display: flex;
  align-items: center;
  gap: 14px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
}
button {
  background: var(--brand);
  color: #1c0f0a;
  border: 0;
  border-radius: 8px;
  padding: 8px 16px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
button.ghost {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--line);
}
button.danger {
  background: transparent;
  color: var(--danger);
  border: 1px solid var(--danger);
}

/* O mascote: olhos brancos (o difusor) quando apagados, e na cor do estado quando acesos */
.clawd {
  display: block;
  width: min(100%, 340px);
  margin: 8px auto 4px;
  shape-rendering: crispEdges;
}
.clawd .body {
  fill: var(--clawd);
}
.clawd .eye {
  fill: currentColor;
  color: var(--diffuser);
}
.clawd:not(.idle):not(.off) .eye {
  filter: url(#glow);
}
.clawd.thinking .eye {
  animation: think 1.2s ease-in-out infinite;
}
.clawd.done .eye {
  color: var(--green);
}
.clawd.question .eye {
  color: var(--blue);
  animation: pulse 1.6s ease-in-out infinite;
}
.clawd.error .eye {
  color: var(--red);
}
@keyframes think {
  0%,
  100% {
    color: var(--yellow);
  }
  50% {
    color: var(--orange);
  }
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .clawd .eye {
    animation: none !important;
  }
}

.state {
  text-align: center;
  margin-bottom: 16px;
}
.connect {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.status.ready {
  color: var(--ok);
}
.status.unsupported,
.status.lost,
.status.failed {
  color: var(--danger);
}
.battery {
  margin-left: auto;
  font-size: 0.9rem;
}
.states {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.state-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.state-btn.on {
  border-color: var(--brand);
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 8px;
  border-radius: 50%;
  vertical-align: middle;
}
.state-btn .dot {
  margin-right: 0;
}
.dot.idle {
  background: var(--diffuser);
}
.dot.thinking {
  background: linear-gradient(90deg, var(--yellow), var(--orange));
}
.dot.done {
  background: var(--green);
}
.dot.question {
  background: var(--blue);
}
.dot.error {
  background: var(--red);
}
.hint {
  margin-top: 10px;
}
.slider {
  display: grid;
  grid-template-columns: 64px 1fr 36px;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.slider input {
  width: 100%;
  accent-color: var(--brand);
}
.slider output {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.power-off {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.powers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}
.steps {
  margin: 0 0 16px;
  padding-left: 20px;
}
.steps li + li {
  margin-top: 6px;
}
pre {
  margin: 8px 0;
  padding: 10px 12px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.85rem;
}
table {
  width: 100%;
  border-collapse: collapse;
}
td {
  padding: 8px 0;
  border-top: 1px solid var(--line);
  vertical-align: top;
}
td:first-child {
  white-space: nowrap;
  padding-right: 16px;
}
footer {
  margin-top: 24px;
  text-align: center;
}
</style>
