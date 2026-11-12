# AGENTS.md

Guia para agentes de código (e pessoas) neste repositório. O que o projeto faz está no `README.md`; o circuito, em
`docs/hardware.md`; o protocolo, em `docs/protocolo.md`.

## O projeto

O mascote do Claude Code em pixel art, de mesa, com um XIAO ESP32-C3 dentro: os olhos (dois LEDs atrás de um difusor
branco em cada janelinha) mostram o que o Claude Code está fazendo. Três partes falam o mesmo protocolo de texto:

- **Firmware** em Arduino (`firmware/firmware.ino`), simulado no Wokwi (`firmware/diagram.json`).
- **Plugin do Claude Code** (`plugin/`): hooks em `hooks/hooks.json` que chamam `bin/companion`, um script Python sem
  dependência para mandar comandos e com o bleak (via `uv run --script`) para a ponte BLE. Com
  `COMPANION_SIM=localhost:4000`, a ponte fala com o firmware no Wokwi pela serial simulada, sem Bluetooth.
- **Portal** em Nuxt 4 como SPA (`ssr: false`), TypeScript estrito, Web Bluetooth, sem servidor (`pnpm generate`).

## Comandos

```bash
pnpm install
pnpm dev                 # portal em http://localhost:3500
pnpm test                # node --test tests/*.test.ts
pnpm typecheck           # vue-tsc
pnpm format              # Prettier (Markdown, firmware e plugin/bin ficam de fora)
pnpm firmware            # arduino-cli compile para firmware/build
pnpm sim                 # Wokwi no terminal, comandos pela serial (precisa de WOKWI_CLI_TOKEN)
pnpm sim:test            # cenário do Wokwi: liga, obedece, desliga e liga
claude plugin validate . # marketplace e plugin
uv run 3d/gerar.py       # STL do corpo (3d/), a partir das medidas no começo do script
```

Antes de entregar: `pnpm format`, `pnpm typecheck`, `pnpm test`; se mexeu no firmware, `pnpm firmware` e
`pnpm sim:test`; se mexeu no plugin, `claude plugin validate .`.

## Invariantes (não quebre)

- **O protocolo mora em três lugares** (`firmware/firmware.ino`, `plugin/bin/companion`, `shared/protocol.ts`), na mesma
  ordem de estados. Mudou um? Mude os três e o `docs/protocolo.md`; o `pnpm test` confere UUIDs, estados e hooks.
- **Hooks nunca seguram o Claude.** Todos com `"async": true`, menos o `start` do `SessionStart`, que só dispara a ponte
  em segundo plano e sai. O `send` só manda um datagrama UDP: não importa o bleak nem espera resposta.
- **Repouso é LED apagado:** o difusor é que deixa o olho branco. Os olhos mudam de cor inteiros (com o difusor, LEDs
  do mesmo olho em cores diferentes viram uma cor só).
- **LEDs numa corrente só, no D3.** Nada de LED em D6 e D7 (UART0, log do boot) nem em D8 e D9 (strapping: o C3 não
  dá boot). Ligações novas seguem a tabela de `docs/hardware.md`.
- **O loop nunca bloqueia**, fora as animações de ligar e desligar. Som é a fila de `play()`/`soundTick()`, não
  `delay()`. O callback do BLE só põe o comando na fila `inbox`; quem mexe nos LEDs é o loop.
- **O que vem do Companion passa pelo `parseStatus`** antes de ir para a tela do portal.
- **Bateria:** desliga sozinho abaixo de `LOW_BATTERY_MV` por três leituras seguidas. Não tire essa proteção.
- **O 3D sai do `3d/gerar.py`**: mude as medidas lá e gere de novo, nunca edite um STL na mão. As peças saem na
  posição de imprimir sem suporte; o script confere o tamanho de cada uma. O furo do USB-C da tampa depende da altura
  do XIAO (`USB_Y`).
- **Nada de dado pessoal** em código, commits, exemplos ou testes. O protocolo só leva o estado, nunca conteúdo do
  Claude.
- O nome do plugin é `companion`: o Claude Code recusa nomes de plugin que começam com `claude-`.
