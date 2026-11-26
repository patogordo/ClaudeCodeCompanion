# Impressão 3D

O corpo é o mascote do Claude Code em pixel art, oco, com 128 × 80 × 52 mm montado (16 × 10 pixels de 8 mm). Os STL
estão em `3d/` e saem do script `3d/gerar.py`, já na posição de imprimir: **nenhuma peça precisa de suporte**.

<p align="center">
  <img src="screenshots/3d-frente.png" alt="O Companion impresso, de frente: corpo laranja com os dois olhos brancos" width="400">
  <img src="screenshots/3d-tras.png" alt="As costas: botão, conector Qwiic, furo do USB-C, furos do som e os quatro parafusos" width="400">
</p>

## Peças

| Arquivo | Cor | Na mesa |
| --- | --- | --- |
| `corpo.stl` | Laranja | Com o rosto para baixo. O rosto pega a textura da mesa (numa PEI texturizada fica fosco e bonito) |
| `tampa.stl` | Laranja | Com o lado de fora para baixo (o berço do botão fica em cima) |
| `difusores.stl` (os 2 olhos, ocos) | Branco | Com a aba para baixo |
| `tampas-dos-olhos.stl` (as 2) | Qualquer; branco reflete mais luz | Com a aba para baixo (o rebaixo dos LEDs fica em cima) |
| `trava-do-botao.stl` | Qualquer | Deitada |

O corpo tem 128 × 80 × 50 mm na mesa e cabe em qualquer impressora, até numa de 180 × 180 mm.

**Tudo de uma vez:** `mesa.stl` traz as cinco peças de um Companion lado a lado, em 208 × 154 mm (cabe em qualquer
Anycubic Kobra, a partir de 220 × 220 mm). No fatiador (Anycubic Slicer Next, Orca, Bambu Studio), use **Dividir →
Para objetos** para separar as peças. Com multicor (o ACE da Anycubic), dê o branco aos difusores. Sem multicor,
imprima os difusores à parte, em branco, ou só a `mesa.stl` sem eles. Para 3 Companions, são 3 impressões: três corpos
não cabem juntos nem numa mesa de 250 mm.

## Material e cores

- **PLA fosco (matte)** em tudo: não empena, imprime fácil, e o fosco esconde as camadas, combinando com o pixel art.
  Se o Companion for ficar no sol ou num lugar quente, use PETG (o PLA amolece perto de 55 °C).
- **Corpo e tampa:** laranja terracota, o mais perto possível do laranja do mascote (`#D97757`). Procure por
  "terracota", "coral" ou "laranja queimado" fosco; laranja vivo demais fica parecendo cone de trânsito.
- **Difusores:** PLA **branco**, não o "natural" translúcido. Apagado, o olho fica branco, como você quer; aceso, o
  branco espalha a luz por igual. O difusor é oco, com 0,6 mm na frente (3 camadas) e 1,2 mm nos lados, então a luz
  passa de sobra. Se achar fraco, aumente o brilho no portal; se der para ver os dois LEDs como pontos, aumente `SKIN`
  no `gerar.py`.
- **Com impressora multicor** (AMS ou troca de filamento na camada), dá para imprimir os olhos brancos junto com o
  rosto, sem os difusores avulsos.

## Configurações

| Ajuste | Valor |
| --- | --- |
| Altura de camada | 0,2 mm (bico de 0,4 mm) |
| Paredes (perímetros) | 3 |
| Camadas de topo e de fundo | 4 |
| Preenchimento | 15%, giroide (só os braços e as pernas, que são maciços, usam) |
| Suportes | Nenhum |
| Brim | Não precisa |

As espessuras já vêm do modelo: paredes de 2,4 mm nos lados, no topo e no chão, e 2 mm no rosto e na tampa. Com 3
perímetros elas saem praticamente sólidas. As únicas pontes são o rasgo do superpoder da cabeça (8,4 mm) e a frente
dos difusores, que são ocos (5,4 mm); qualquer impressora faz.

## Onde vai cada componente

<p align="center">
  <img src="screenshots/3d-dentro.png" alt="Por dentro, sem a tampa: protoboard no chão com o XIAO, bateria na lateral, buzzer, botão, Qwiic, superpoder da cabeça e as tampinhas dos olhos, com os LEDs, encaixadas nos tubos de luz" width="560">
</p>

Visto por trás, com a tampa aberta:

- **Olhos:** atrás de cada janela há um tubo de luz. Encaixe o difusor por dentro, com a aba para trás, e prenda a
  aba com uma gota de cola. Cada olho leva duas plaquinhas de LED WS2812B (de fita de 30 LEDs/m, 10 × 33 mm, um LED
  cada), deitadas, uma em cima da outra, coladas no rebaixo da tampinha com os LEDs virados para fora. Na de cima, a
  entrada (DIN) fica na ponta do canal dos fios, a que aponta para o meio do corpo; a de baixo vai girada, com a DIN
  na outra ponta, junto da DO da de cima: ligue as duas com três fios curtos (+5V com +5V, DO com DIN, GND com GND).
  Os três fios do olho saem pelo canal. Empurre a tampinha no tubo até a aba encostar: as nervuras seguram sem cola, e
  os LEDs ficam a uns 5 mm do difusor.
- **Fios dos olhos:** GPIO5 → olho que fica à esquerda de quem olha de frente; GPIO6 → o outro. Por trás, o olho do
  GPIO5 é o da direita.
- **Mini protoboard de 170 furos:** no chão, no meio, encostada na tampa. A fita dupla face que vem embaixo dela
  segura.
- **XIAO:** na ponta de trás da protoboard, com o USB-C virado para a tampa. Ele sai pelo furo de baixo, no meio.
- **MOSFETs, resistores e capacitor:** na protoboard. O AO3401 e o 2N7002 são SMD (SOT-23): use um adaptador SOT-23
  para DIP em cada um.
- **Bateria:** em pé, na parede da esquerda, atrás do tubo do olho (a partir de uns 15 mm do rosto), com fita dupla
  face de espuma. Uma 803040 (8 × 30 × 40 mm, 1000 mAh) cabe com os 40 mm na vertical, entre a torre de baixo e a de
  cima.
- **Buzzer:** colado na tampa, atrás dos furos do som (embaixo, à direita).
- **Botão:** uma chave táctil de 12 × 12 mm, só a chave, sem a plaquinha do módulo. Solde os fios em duas pernas
  em diagonal (assim pega os dois contatos, qualquer que seja o lado) e encaixe a chave por dentro da tampa, no
  berço em cima à esquerda, com as pernas para os lados abertos do berço. Empurre a trava atrás dela até encostar: as
  nervuras seguram sem cola, e os entalhes deixam passar as pernas. Ponha a capa por fora, pelo furo. O furo conta com
  uma capa redonda de 13 mm; se a sua for de outro tamanho, meça e mude o `CAP_D` no `gerar.py`.
- **Rasgos dos superpoderes** (topo e tampa): ficam vazios por enquanto.
- **Tampa:** 4 parafusos M2 × 8 autoatarraxantes nas torres dos cantos.

## Protoboard ou placa soldada

A mini protoboard de 170 furos (47 × 35 × 8,5 mm) cabe e é ótima para o protótipo, mas com o tempo os jumpers e os
componentes soltam. Para a versão final, solde tudo numa placa perfurada do mesmo tamanho. A altura do furo do USB-C
na tampa conta com a protoboard (`USB_Y` no `gerar.py`); se o XIAO ficar em outra altura, mude o valor e gere a tampa
de novo.

## Mudar o tamanho

Os números ficam no começo do `3d/gerar.py`: `P` (tamanho do pixel), `D` (profundidade), `FACE`, `WALL` e `LID`
(espessuras). Depois de mudar:

```bash
uv run 3d/gerar.py
```

O script confere o tamanho de cada peça antes de salvar. Com o `D` menor que 52 mm, a protoboard (47 mm) não cabe
mais deitada no fundo.
