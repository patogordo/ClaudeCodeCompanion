# Hardware

O corpo é o mascote do Claude Code em pixel art, impresso em 3D. Os olhos são as duas janelinhas dele, fechadas com um
difusor branco, com dois LEDs atrás de cada uma: apagados, os olhos ficam brancos; acesos, ficam da cor do estado.
Dentro, um Seeed XIAO ESP32-C3, um buzzer, um botão e uma bateria que carrega pelo USB-C do próprio XIAO. O diagrama do
Wokwi (`firmware/diagram.json`) é a versão simplificada deste circuito; as diferenças estão no fim da página.

## Peças

| Peça | Qtd. | Para quê |
| --- | --- | --- |
| Seeed Studio XIAO ESP32-C3 | 1 | O cérebro. Use a antena que vem junto: sem ela o Bluetooth fica fraco |
| Corpo, tampa, difusores, tampinhas dos olhos e trava do botão, impressos em 3D | 1 jogo | `3d/*.stl`: 128 × 80 × 52 mm, olhos de 8 × 16 mm. Material, cores e montagem em [`impressao-3d.md`](impressao-3d.md) |
| Plaquinhas de LED WS2812B (fita de 30 LEDs/m, 10 × 33 mm, um LED cada) | 4 | Duas em cada olho, deitadas, uma em cima da outra, coladas na tampinha do tubo de luz |
| Mini protoboard de 170 furos | 1 | Cabe no chão do corpo. Para a versão final, placa perfurada soldada |
| Adaptador SOT-23 para DIP | 2 | Para usar os MOSFETs (que são SMD) na protoboard |
| Parafuso M2 × 8 autoatarraxante | 4 | Só com a tampa de parafusos; a de encaixe não usa |
| Bateria LiPo 1S 3,7 V, 500 a 1000 mAh, com proteção | 1 | Soldada nos pads BAT+ e BAT− embaixo do XIAO, que carrega pelo USB-C |
| Buzzer piezo passivo de 12 mm | 1 | Os sons. Piezo puxa pouca corrente e vai direto no pino; buzzer magnético precisa de transistor |
| Chave táctil de 12 × 12 × 7,3 mm (4 pernas), com capa redonda de 13 mm | 1 | Liga e desliga. Fica num berço por dentro da tampa de trás, com a capa para fora; só a chave, sem a plaquinha do módulo |
| MOSFET P AO3401 e MOSFET N 2N7002 | 1 + 1 | Cortam a alimentação dos LEDs com o Companion desligado |
| Resistor 220 kΩ | 2 | Divisor para medir a bateria |
| Resistor 100 kΩ | 2 | Pull-up do gate do AO3401 e pull-down do gate do 2N7002 |
| Resistor 10 kΩ | 1 | Pull-up do botão (o interno do C3 não é garantido no deep sleep) |
| Resistor 330 Ω | 2 | Em série no fio de dados de cada olho |
| Capacitor eletrolítico 470 µF, 6,3 V | 1 | No VLED, perto dos LEDs |

## Pinagem

A ESP32-C3 SuperMini também serve (o firmware compilado para o XIAO roda nela): nela, ligue pelo número do GPIO. Sem
bateria, o esquema é o [`esquema-usb.svg`](esquema-usb.svg): LEDs no 5V, o GPIO2 no 3V3 e nada de MOSFET. O suporte
da placa na tampa (`3d/`) é do tamanho da SuperMini.

| GPIO (XIAO) | Ligação |
| --- | --- |
| 2 (D0, A0) | Meio do divisor 220 kΩ + 220 kΩ entre BAT+ e GND |
| 3 (D1) | Botão para o GND, com 10 kΩ para o 3V3. Só os GPIO0 a 5 acordam o C3 do deep sleep |
| 4 (D2) | Buzzer (o outro terminal no GND) |
| 5 (D3) | 330 Ω até o DIN do LED de cima do olho esquerdo (o de quem olha de frente), que segue para o de baixo |
| 6 (D4) | 330 Ω até o DIN do LED de cima do olho direito, que segue para o de baixo |
| 10 (D10) | Gate do 2N7002, com 100 kΩ para o GND |
| 20, 21 (D7, D6) | Livres. São a UART0, onde o boot escreve o log: LED aqui pisca lixo ao ligar |
| 8, 9 (D8, D9) | Livres. São pinos de strapping (o 9 é o botão BOOT): um LED apagado no fio puxaria o pino e o C3 não daria boot |

Cada olho tem o próprio fio de dados. No firmware, `EYE_PIXELS` é quantos LEDs cada olho tem, de cima para baixo
(`firmware/firmware.ino`).

## Energia

![Ligações de energia: bateria nos pads do XIAO, divisor no A0, botão no D1 e os MOSFETs que cortam os LEDs](energia.svg)

1. **Bateria:** solde o fio vermelho (+) no pad BAT+ e o preto (−) no BAT−, os dois embaixo do XIAO. Confira a
   polaridade com um multímetro antes: conectores JST de bateria não têm padrão entre fabricantes, e o XIAO não tem
   proteção contra inversão. O USB-C do próprio XIAO carrega a bateria e, plugado, alimenta tudo.
2. **Medição:** dois resistores de 220 kΩ em série entre o BAT+ e o GND, com o meio no A0.
3. **Botão:** entre o D1 e o GND, com 10 kΩ do D1 para o 3V3.
4. **Corte dos LEDs:** o AO3401 (MOSFET P) fica entre o BAT+ e o VLED, que alimenta os olhos e o capacitor de
   470 µF. O gate dele tem 100 kΩ para o BAT+ e vai ao dreno do 2N7002 (MOSFET N), que tem a fonte no GND e o gate no
   D10, com 100 kΩ para o GND.
5. **Chave de transporte (opcional):** uma chave deslizante no fio + da bateria corta tudo. Desligada, a bateria não
   carrega pelo USB-C.

Ligado, o firmware põe o D10 em nível alto: o 2N7002 conduz, puxa o gate do AO3401 para o GND e os LEDs recebem a
bateria. Desligado, o C3 entra em deep sleep, o D10 fica solto e os dois resistores de 100 kΩ apagam os MOSFETs. Sem
esse corte, cada WS2812B apagado ainda consome perto de 1 mA: os 4 dos olhos esvaziariam a bateria em algumas
semanas, com o Companion desligado. Com ele, desligado fica em dezenas de µA (o deep sleep do C3 e os
10 µA do divisor), o que dá meses. Ligado, o repouso deixa os LEDs apagados, então quem mais gasta é o tempo em que o
Claude está trabalhando.

Ligado, o C3 com o Bluetooth gasta dezenas de mA, e os LEDs acesos somam mais: na mesa, deixe no USB-C, que carrega
enquanto usa.

Os LEDs vão na bateria, não no pino 5V: o 5V do XIAO só tem tensão com o USB ligado. Com a bateria cheia (4,2 V), o dado
de 3,3 V fica no limite do que o WS2812B entende como nível alto; se os olhos piscarem cores erradas, ponha um 74AHCT125
como conversor de nível no fio de dados.

Abaixo de 3,3 V, por três leituras seguidas (uma a cada 10 s), o Companion desliga sozinho para não descarregar a LiPo
demais. A porcentagem é uma reta entre 3,3 V e 4,15 V: serve de indicação, não de medida. Com o USB ligado, a leitura
sobe porque a bateria está carregando.

## Botão

- **Ligar:** segure por 1 s. Os olhos abrem em branco, de baixo para cima, piscam duas vezes e se apagam devagar, com
  uma escala subindo. Um toque rápido acorda o C3, mas ele volta a dormir sem acender nada.
- **Desligar:** segure por 1 s. Os olhos acendem em branco e a pálpebra fecha, de cima para baixo, com a escala
  descendo.
- **Toque curto, ligado:** volta os olhos ao repouso (apaga o verde ou o vermelho).

## No Wokwi

O diagrama simplifica o circuito:

- Cada olho são dois NeoPixels, um em cima do outro. O simulador não tem difusor: apagado, o LED fica escuro, e não
  branco.
- Os LEDs ficam no pino 5V, sem MOSFET (o simulador não gasta bateria).
- O A0 vai no GND: sem bateria, o status mostra `"bat":-1`.
- O Wokwi não simula o rádio Bluetooth: o firmware sobe o BLE, mas nada conecta. Os comandos vão pela serial, com o
  mesmo texto do BLE. O `wokwi.toml` publica essa serial na porta TCP 4000, e a ponte do plugin fala com ela quando
  `COMPANION_SIM=localhost:4000` (veja o README).
