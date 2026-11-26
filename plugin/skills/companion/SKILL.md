---
name: companion
description: Controla o Claude Code Companion, o mascote do Claude Code de mesa, com olhos de LED, ligado pelo cabo USB ou por Bluetooth. Muda a cor dos olhos, toca os sons de pronto e de erro, ajusta volume e brilho, mostra bateria e superpoderes, e desliga. Use quando a pessoa pedir algo ao Companion ou ao robô ("deixa os olhos azuis", "abaixa o volume do companion", "quanto tem de bateria?", "desliga o robô").
allowed-tools: Bash(companion *)
---

O comando `companion` (do plugin, já no PATH) conversa com a ponte local, que segura a conexão com o Companion (pelo cabo USB, se estiver ligado, senão Bluetooth).
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
| Tocar música: 1 Korobeiniki, 2 Ode à Alegria, 3 Für Elise, 4 Parabéns a Você, 5 Brilha, Brilha Estrelinha, 6 Jingle Bells, 7 Frère Jacques, 8 Pequena Serenata Noturna, 9 Quinta Sinfonia, 10 When the Saints, 11 Marcha Nupcial, 12 We are Charlie Kirk, 13 Zelda's Lullaby, 14 Epona's Song, 15 Saria's Song, 16 Sun's Song, 17 Song of Time, 18 Song of Storms, 19 Minuet of Forest, 20 Bolero of Fire, 21 Serenade of Water, 22 Nocturne of Shadow, 23 Requiem of Spirit, 24 Prelude of Light | `companion send music 2` |
| Desligar (liga de novo segurando o botão por 1 s) | `companion send off` |

O `status` devolve JSON, por exemplo
`{"fw":"1.0.0","state":"done","vol":60,"bri":40,"bat":87,"mv":4012,"i2c":[60]}`:

- `bat` é a carga em % e `mv` a tensão; `bat: -1` quer dizer que não há bateria (só USB).
- `i2c` lista, em decimal, os endereços encontrados no superpoder das costas (60 = 0x3C, um display OLED comum).
- `{"connected":false}`: a ponte está rodando, mas não achou o Companion. Peça para ligar (segurar o botão 1 s) e
  ligar o cabo USB ou chegar perto do computador.
- Se a ponte não estiver rodando, `companion start` sobe ela em segundo plano; o log fica em
  `~/.cache/claude-companion/bridge.log`.

Responda em uma linha o que mudou; para o status, diga bateria, volume e brilho em texto corrido.
