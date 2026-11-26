# Protocolo

O Companion entende comandos de texto, iguais pelo Bluetooth (BLE) e pela serial. Os UUIDs e os estados aparecem em
três lugares: `firmware/firmware.ino`, `plugin/bin/companion` e `shared/protocol.ts`. O `pnpm test` confere que os três
batem e que os hooks só mandam comandos que existem.

## BLE

| O quê | Valor |
| --- | --- |
| Nome anunciado | `Claude Companion` |
| Serviço | `5d1e0000-23fd-4dbe-89ca-ba268b36c947` |
| Comando (escrita, com ou sem resposta) | `5d1e0001-23fd-4dbe-89ca-ba268b36c947` |
| Status (leitura e notificação) | `5d1e0002-23fd-4dbe-89ca-ba268b36c947` |

- Um comando por escrita, em UTF-8, com até 31 bytes.
- A notificação do status só avisa que algo mudou: leia o valor para ter o JSON inteiro. A notificação é cortada no MTU
  (20 bytes no mínimo), e a leitura não.
- O Companion continua anunciando depois de conectar, então a ponte do plugin e o portal ficam conectados ao mesmo
  tempo.
- Não há pareamento: quem estiver no alcance do Bluetooth consegue mudar os olhos ou desligar o Companion. Nada do
  Claude passa por aqui além do estado (nem prompt, nem código).

## Serial

115200 baud pelo USB-C, uma linha por comando (termine com `\n`). É como o Wokwi conversa com o firmware.

## Comandos

| Comando | Efeito |
| --- | --- |
| `idle` | Repouso: LEDs apagados (o difusor deixa os olhos brancos) |
| `thinking` | Pensando: os olhos alternam entre amarelo e laranja vibrante |
| `done` | Pronto: verde, com dois bipes subindo |
| `question` | Dúvida: azul pulsando |
| `error` | Erro: vermelho, com dois bipes descendo |
| `vol N` | Volume de 0 a 100 (0 é mudo). Bipa para conferir e fica guardado na flash |
| `bri N` | Brilho de 5 a 100. Fica guardado na flash |
| `music N` | Toca a música N (1 a 24, a ordem de `SONGS` em `shared/protocol.ts`) com os olhos piscando; um toque no botão para |
| `off` | Desliga (deep sleep). Para ligar, segure o botão por 1 s |
| `status` | Só na serial: imprime o status (no BLE, leia a característica de status) |

Comando desconhecido não muda nada; na serial, aparece `comando desconhecido: ...`.

## Status

```json
{ "fw": "1.0.0", "state": "done", "vol": 60, "bri": 40, "bat": 87, "mv": 4012, "i2c": [60] }
```

| Campo | O quê |
| --- | --- |
| `fw` | Versão do firmware |
| `state` | Um dos cinco estados |
| `vol`, `bri` | Volume (0 a 100) e brilho (5 a 100) |
| `bat` | Carga da bateria em %, ou `-1` sem bateria (só USB, ou no Wokwi) |
| `mv` | Tensão da bateria em mV |
| `i2c` | Endereços (decimal) encontrados no boot no superpoder das costas |

O portal confere cada campo em `parseStatus` (`shared/protocol.ts`) antes de mostrar.

## Quando o plugin manda cada estado

Os hooks estão em `plugin/hooks/hooks.json`. Todos rodam com `"async": true`: o Claude nunca espera pelo Companion.

| Evento do Claude Code | Comando |
| --- | --- |
| `SessionStart` | `companion start` (sobe a ponte) e `idle` |
| `UserPromptSubmit`, `PostToolUse` | `thinking` |
| `PermissionRequest`, `Elicitation`, `PreToolUse` de `AskUserQuestion` e `ExitPlanMode` | `question` |
| `PostToolUseFailure`, `StopFailure` | `error` |
| `Stop` | `done` |
| `SessionEnd` | `idle` |

Recusar um pedido de permissão não dispara nenhum hook: os olhos ficam azuis até o próximo passo do Claude. Todo
comando que termina com erro (inclusive um `grep` sem resultado) dispara `PostToolUseFailure`, então o vermelho com som
aparece no meio do trabalho e volta ao laranja no passo seguinte.

## Ponte do plugin

`plugin/bin/companion bridge` segura uma conexão só, para todas as sessões do Claude na máquina, e ouve comandos
por UDP em `127.0.0.1:47321` (mude com `COMPANION_PORT`). Cada datagrama é um comando. Para `status`, a ponte responde
ao remetente com o JSON do Companion, ou `{"connected":false}` se ele não estiver conectado. Quando a conexão volta, a
ponte reenvia o último estado. O log fica em `~/.cache/claude-companion/bridge.log`.

A conexão é pela serial da USB quando o Companion está no cabo, senão pelo BLE. A ponte procura `/dev/cu.usbmodem*`
(macOS) e `/dev/ttyACM*` (Linux), manda `status` e só fica com a porta se a resposta for o JSON do Companion; outra
placa recebe esse `status` uma vez e é deixada em paz até ser desligada. Conectada pelo BLE, a ponte troca para o cabo
assim que ele aparece; sem o cabo, volta ao BLE.

A ponte também atende HTTP na mesma porta (TCP), para o portal, que não fala UDP: `GET /status` devolve o JSON e
`POST /send`, com o comando no corpo, manda o comando. Só o portal local (`http://localhost:*`) e o publicado
(`https://patogordo.github.io`) passam no CORS; outra origem recebe 403.

Com `COMPANION_SIM=localhost:4000` no ambiente, a ponte fala com o firmware rodando no Wokwi em vez do Bluetooth: manda
os comandos pela serial simulada (a porta `rfc2217ServerPort` do `firmware/wokwi.toml`) e responde ao `status` com a
linha de status que o firmware imprime.
