// O protocolo do Companion (docs/protocolo.md). Os mesmos UUIDs e estados estão no firmware e na ponte do plugin;
// tests/protocol.test.ts confere.
export const SERVICE_UUID = '5d1e0000-23fd-4dbe-89ca-ba268b36c947'
export const COMMAND_UUID = '5d1e0001-23fd-4dbe-89ca-ba268b36c947'
export const STATUS_UUID = '5d1e0002-23fd-4dbe-89ca-ba268b36c947'

export const STATES = ['idle', 'thinking', 'done', 'question', 'error'] as const
export type State = (typeof STATES)[number]

// `when`: o que faz o plugin mandar cada estado (plugin/hooks/hooks.json)
export const STATE_INFO: Record<State, { label: string; hint: string; when: string }> = {
  idle: {
    label: 'Repouso',
    hint: 'Apagados: o difusor deixa os olhos brancos',
    when: 'A sessão abre ou fecha, ou você dá um toque curto no botão',
  },
  thinking: {
    label: 'Pensando',
    hint: 'Alternando entre amarelo e laranja',
    when: 'Você manda um prompt e a cada ferramenta que o Claude usa',
  },
  done: { label: 'Pronto', hint: 'Verde, com som', when: 'O Claude termina a resposta' },
  question: {
    label: 'Dúvida',
    hint: 'Azul pulsando',
    when: 'O Claude pede permissão, faz uma pergunta ou apresenta um plano',
  },
  error: { label: 'Erro', hint: 'Vermelho, com som', when: 'Um comando falha ou a API dá erro' },
}

export interface Status {
  fw: string
  state: State
  vol: number
  bri: number
  bat: number | null // null: sem bateria (só USB)
  mv: number
  i2c: number[]
}

const isInt = (v: unknown, min: number, max: number): v is number =>
  Number.isInteger(v) && (v as number) >= min && (v as number) <= max

// O JSON que vem do Companion passa por aqui antes de ir para a tela
export function parseStatus(text: string): Status | null {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return null
  }
  if (!raw || typeof raw !== 'object') return null
  const { fw, state, vol, bri, bat, mv, i2c } = raw as Record<string, unknown>
  if (typeof fw !== 'string' || !STATES.includes(state as State)) return null
  if (!isInt(vol, 0, 100) || !isInt(bri, 0, 100) || !isInt(bat, -1, 100) || !isInt(mv, 0, 10_000)) return null
  if (!Array.isArray(i2c) || !i2c.every(a => isInt(a, 0, 127))) return null
  return { fw, state: state as State, vol, bri, bat: bat < 0 ? null : bat, mv, i2c }
}

const clamp = (v: number, min: number, max: number) => Math.round(Math.min(max, Math.max(min, v)))
export const volumeCommand = (v: number) => `vol ${clamp(v, 0, 100)}`
export const brightnessCommand = (v: number) => `bri ${clamp(v, 5, 100)}`
export const hex = (address: number) => '0x' + address.toString(16).toUpperCase().padStart(2, '0')
