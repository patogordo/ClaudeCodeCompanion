---
name: companion
description: Controla o Claude Code Companion, o mascote do Claude Code de mesa, com olhos de LED, ligado por Bluetooth. Muda a cor dos olhos, toca os sons de pronto e de erro, ajusta volume e brilho, mostra bateria e superpoderes, e desliga. Use quando a pessoa pedir algo ao Companion ou ao robô ("deixa os olhos azuis", "abaixa o volume do companion", "quanto tem de bateria?", "desliga o robô").
allowed-tools: Bash(companion *)
---

O comando `companion` (do plugin, já no PATH) conversa com a ponte BLE local, que segura a conexão com o Companion.
Os hooks do plugin já mudam os olhos sozinhos a cada passo; use esta skill só para o que a pessoa pedir.

| Pedido | Comando |
| --- | --- |
| Ver bateria, volume, brilho, estado e superpoderes | `companion status` |
| Repouso (LEDs apagados: os olhos ficam brancos) | `companion send idle` |
| Pensando (alternando entre amarelo e laranja) | `companion send thinking` |
| Pronto (verde, com som) | `companion send done` |
| Dúvida (azul pulsando) | `companion send question` |
| Erro (vermelho, com som) | `companion send error` |
| Volume de 0 a 100 (bipa para conferir) | `companion send vol 40` |
| Brilho de 5 a 100 | `companion send bri 60` |
| Desligar (liga de novo segurando o botão por 1 s) | `companion send off` |

O `status` devolve JSON, por exemplo
`{"fw":"1.0.0","state":"done","vol":60,"bri":40,"bat":87,"mv":4012,"i2c":[60]}`:

- `bat` é a carga em % e `mv` a tensão; `bat: -1` quer dizer que não há bateria (só USB).
- `i2c` lista, em decimal, os endereços encontrados no superpoder das costas (60 = 0x3C, um display OLED comum).
- `{"connected":false}`: a ponte está rodando, mas não achou o Companion. Peça para ligar (segurar o botão 1 s) e
  chegar perto do computador.
- Se a ponte não estiver rodando, `companion start` sobe ela em segundo plano; o log fica em
  `~/.cache/claude-companion/bridge.log`.

Responda em uma linha o que mudou; para o status, diga bateria, volume e brilho em texto corrido.
