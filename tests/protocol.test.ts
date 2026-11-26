// node --test (Node 22.18+ roda TypeScript direto). O protocolo mora em três lugares (firmware, plugin e portal):
// estes testes conferem que eles não divergem.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import {
  COMMAND_UUID,
  SERVICE_UUID,
  STATES,
  STATUS_UUID,
  brightnessCommand,
  hex,
  parseStatus,
  volumeCommand,
  SONGS,
} from '../shared/protocol.ts'

const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')
const firmware = read('firmware/firmware.ino')
const bridge = read('plugin/bin/companion')
const hooks = JSON.parse(read('plugin/hooks/hooks.json'))

test('firmware e ponte usam os mesmos UUIDs do portal', () => {
  for (const uuid of [SERVICE_UUID, COMMAND_UUID, STATUS_UUID]) {
    assert.ok(firmware.includes(`"${uuid}"`), `firmware: ${uuid}`)
    assert.ok(bridge.includes(`"${uuid}"`), `ponte: ${uuid}`)
  }
})

test('firmware e ponte conhecem os mesmos estados, na mesma ordem', () => {
  const quoted = STATES.map(s => `"${s}"`).join(', ')
  assert.ok(firmware.includes(`{${quoted}}`), 'STATE_NAMES do firmware')
  assert.ok(bridge.includes(`(${quoted})`), 'STATES da ponte')
})

test('os hooks só mandam comandos que o firmware entende', () => {
  const commands = Object.values(hooks.hooks)
    .flat()
    .flatMap((group: any) => group.hooks.map((h: any) => h.command as string))
  assert.ok(commands.length > 0)
  for (const command of commands) {
    const m = command.match(/^"\$\{CLAUDE_PLUGIN_ROOT\}\/bin\/companion" (start|send (\w+))$/)
    assert.ok(m, command)
    if (m[2]) assert.ok((STATES as readonly string[]).includes(m[2]), command)
  }
})

test('parseStatus aceita o JSON do firmware', () => {
  assert.deepEqual(parseStatus('{"fw":"1.0.0","state":"done","vol":60,"bri":40,"bat":87,"mv":4012,"i2c":[60]}'), {
    fw: '1.0.0',
    state: 'done',
    vol: 60,
    bri: 40,
    bat: 87,
    mv: 4012,
    i2c: [60],
  })
  assert.equal(parseStatus('{"fw":"1.0.0","state":"idle","vol":0,"bri":5,"bat":-1,"mv":0,"i2c":[]}')?.bat, null)
})

test('parseStatus recusa o que não veio do firmware', () => {
  const ok = { fw: '1.0.0', state: 'idle', vol: 60, bri: 40, bat: 50, mv: 3900, i2c: [] }
  for (const bad of [
    'não é json',
    'null',
    '[]',
    JSON.stringify({ ...ok, state: 'dancing' }),
    JSON.stringify({ ...ok, vol: 101 }),
    JSON.stringify({ ...ok, bri: 1.5 }),
    JSON.stringify({ ...ok, bat: -2 }),
    JSON.stringify({ ...ok, i2c: [200] }),
    JSON.stringify({ ...ok, fw: 1 }),
  ]) {
    assert.equal(parseStatus(bad), null, bad)
  }
})

test('volume e brilho saem dentro da faixa do firmware', () => {
  assert.equal(volumeCommand(150), 'vol 100')
  assert.equal(volumeCommand(-3), 'vol 0')
  assert.equal(brightnessCommand(0), 'bri 5')
  assert.equal(brightnessCommand(42.6), 'bri 43')
  assert.equal(hex(60), '0x3C')
})

test('o portal lista as mesmas músicas do firmware', () => {
  const list = read('firmware/songs.h').match(/SONG_LIST\[\] = \{([^}]*)\}/)![1]!
  assert.equal(list.split(',').length, SONGS.length)
})
