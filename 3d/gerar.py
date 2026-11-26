# /// script
# requires-python = ">=3.10"
# dependencies = ["manifold3d>=3.0", "numpy"]
# ///
"""Gera os STL do Companion: o mascote do Claude Code em pixel art, oco, para imprimir sem suporte.

    uv run 3d/gerar.py

Medidas em milímetros. Cada peça sai na posição de imprimir. Montagem, material e onde vai cada componente em
docs/impressao-3d.md. Coordenadas de montagem: x da esquerda para a direita olhando por trás, y de baixo para cima,
z do rosto (z = 0) para as costas.
"""

from pathlib import Path

import numpy as np
from manifold3d import Manifold

P = 8.0  # tamanho do pixel: o mascote tem 16 × 10 pixels (128 × 80 mm)
D = 53.0  # profundidade total, do rosto às costas: cabe a protoboard de 48 mm deitada, com 0,5 mm de folga
FACE = 2.0  # espessura do rosto (o difusor fica rente a ele)
WALL = 2.4  # paredes dos lados, do topo e do chão
LID = 2.0  # espessura da tampa de trás
FIT = 0.125  # folga de cada lado do difusor na janela do olho
SKIN = 0.6  # o difusor é oco: só a frente (3 camadas de 0,2 mm) e as laterais de 1,2 mm, para a luz passar
FLANGE = 0.8  # aba do difusor, por dentro do rosto

# Atrás de cada olho, duas plaquinhas de LED (WS2812B de fita de 30 LEDs/m: 33 × 10 mm, o LED no meio) deitadas, uma
# em cima da outra, coladas no rebaixo da tampinha do olho, que encaixa no tubo de luz
LED_PCB = (33.0, 10.0)
POCKET_FIT = 0.3  # folga de cada lado das plaquinhas no rebaixo
POCKET_DEPTH = 0.6
WIRES = 2.5  # canal dos fios na ponta da tampinha que fica para o meio do corpo
PW = 1.2  # paredes da tampinha e do tubo de luz
PLUG_FIT = 0.15  # folga de cada lado da tampinha no tubo; as nervuras passam disso e apertam
RIB = 0.3  # quanto cada nervura sai da tampinha
LED_Z = 9.0  # frente da tampinha, onde as plaquinhas colam: os LEDs ficam a uns 5 mm do difusor
TUBE_END = 13.0  # o tubo vai do rosto até aqui; a aba da tampinha encosta na ponta dele

# Botão: chave táctil de 12 × 12 × 7,3 mm (4 pernas) com capa redonda. A chave fica num berço por dentro da tampa,
# encostada nela e presa por trás pela trava; a capa passa pelo furo e fica para fora
BTN = (36.0, 64.0)  # centro, visto por trás (em cima, à esquerda)
BTN_SIZE = 12.0
BTN_BODY = 3.5  # da base da chave até a chapa de metal
BTN_FIT = 0.2  # folga de cada lado da chave no berço
CAP_D = 13.0  # diâmetro da capa (meça a sua): o furo tem 0,4 mm de folga de cada lado, para a capa não raspar
LEGS_SLOT = 7.2  # rasgo das pernas (5 mm entre elas) nas duas paredes da esquerda e da direita do berço
LATCH = 3.0  # espessura da trava
CRADLE = BTN_BODY + LATCH + 1.0  # altura do berço: a trava entra até encostar na chave, seja qual for a altura dela

# Placa: ESP32-C3 SuperMini, deitada num suporte na tampa, com o USB-C rente à tampa por fora. A placa entra por cima
# no fundo do suporte e desliza até o USB-C entrar no furo; a trava da placa ocupa a folga que sobra atrás
MCU = (18.0, 22.52)  # largura (x) e comprimento (z)
MCU_PCB = 0.8  # espessura da placa; com o USB-C dá 4 mm (medido). A trava assenta em cima da placa e se ajusta
MCU_Y = 46.0  # face de baixo da placa: as pernas ficam a 9 mm da protoboard, com espaço para os componentes
MCU_LEGS = 10.0  # as pernas (barra de pinos) passam isso da placa, dos lados do apoio do meio
PB_PARTS = 8.0  # altura dos componentes na protoboard embaixo das pernas
MCU_FIT = 0.25  # folga de cada lado da placa entre as guias
MCU_RIB = 5.0  # meia largura do apoio embaixo da placa: os pinos (a 7,62 mm do meio) ficam livres
USB_C = (8.94, 3.2)  # largura e altura do conector, montado em cima da placa
USB_OVERHANG = 1.0  # quanto o USB-C passa da borda da placa (meça a sua): a tampa fica com essa espessura em volta
USB_FIT = 0.25  # folga de cada lado do USB-C no furo
SLACK = USB_OVERHANG + 1.5  # espaço atrás da placa para ela entrar sem o USB-C bater na tampa
GUIDE = 1.6  # espessura das guias, do apoio e da parede de trás do suporte

# Protoboard de 170 furos no chão, entre dois trilhos com uma aba por cima da borda (que não tem furos). Entra
# deslizando por trás, com a tampa aberta, e fica presa entre o rosto e a tampa; a fita dupla face vira opcional
PB = (36.0, 48.0, 8.5)  # largura (x, com os dentinhos), comprimento (z) e altura: medidas de uma de 170 furos
PB_GAP = 0.3  # folga de cada lado: a largura já conta os dentinhos, então o trilho fica justo
PB_TOOTH = 1.0  # quanto o dentinho sai da lateral (36 mm com ele, 35 sem)
PB_LIP = 2.5  # quanto a aba do trilho cobre a borda de cima (a borda sem furos tem uns 4 mm)

# Tampa de encaixe: quatro linguetas, em cima e embaixo, com um dente que entra num rebaixo das paredes do corpo. A
# tampa de parafusos continua valendo; o corpo serve para as duas
TAB_X = (34.0, 94.0)  # longe das torres dos parafusos, da protoboard e do buzzer
TAB_W, TAB_T, TAB_L = 8.0, 1.2, 8.0  # largura, espessura e comprimento de cada lingueta
TAB_FIT = 0.2  # folga entre a lingueta e a parede
BUMP, CREST = 0.6, 1.0  # dente: altura (com rampas de 45°) e topo reto; a lingueta dobra BUMP - TAB_FIT ao entrar

# O mascote em pixels: (coluna, linha) a partir do canto de baixo à esquerda (ele é simétrico)
BODY = (2, 2, 14, 10)
ARMS = [(0, 4, 2, 6), (14, 4, 16, 6)]
LEGS = [(c, 0, c + 1, 2) for c in (3, 5, 10, 12)]
EYES = [(4, 6, 5, 8), (11, 6, 12, 8)]

SHELL = D - LID  # o corpo vai de z = 0 até aqui; a tampa fecha o resto
CX = 8 * P  # centro do mascote em x
IN = (BODY[0] * P + WALL, BODY[1] * P + WALL, BODY[2] * P - WALL, BODY[3] * P - WALL)  # a cavidade (x0, y0, x1, y1)
OUT = Path(__file__).parent


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl(x, y, z0, z1, d, d1=None):
    return Manifold.cylinder(z1 - z0, d / 2, (d1 or d) / 2, circular_segments=48).translate((x, y, z0))


def pixels(rect, z0, z1):
    c0, r0, c1, r1 = rect
    return box(c0 * P, r0 * P, z0, c1 * P, r1 * P, z1)


def stadium(x, y, z0, z1, w, h):
    """Retângulo de pontas redondas (w × h, deitado), como o USB-C."""
    return (cyl(x - (w - h) / 2, y, z0, z1, h) + cyl(x + (w - h) / 2, y, z0, z1, h)).hull()


def union(parts):
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


def rbox(rect, z0, z1):
    x0, y0, x1, y1 = rect
    return box(x0, y0, z0, x1, y1, z1)


def grow(rect, d):
    x0, y0, x1, y1 = rect
    return (x0 - d, y0 - d, x1 + d, y1 + d)


def eye_parts(eye):
    """Retângulos (x0, y0, x1, y1) de um olho: o rebaixo das plaquinhas, o canal dos fios, a tampinha e o tubo (por
    dentro). O tubo encosta na parede lateral do corpo; o canal dos fios fica do lado do meio."""
    c0, r0, c1, r1 = eye
    ey = (r0 + r1) / 2 * P
    pw, ph = LED_PCB[0] + 2 * POCKET_FIT, 2 * LED_PCB[1] + 2 * POCKET_FIT
    x0 = IN[0] + PLUG_FIT  # olho da esquerda (visto por trás); o da direita é o espelho
    parts = {
        "pocket": (x0 + PW, ey - ph / 2, x0 + PW + pw, ey + ph / 2),
        "wires": (x0 + PW + pw, ey - ph / 2, x0 + PW + pw + WIRES, ey + ph / 2),
        "plug": (x0, ey - ph / 2 - PW, x0 + PW + pw + WIRES, ey + ph / 2 + PW),
    }
    parts["tube"] = grow(parts["plug"], PLUG_FIT)
    if (c0 + c1) / 2 * P > CX:
        parts = {k: (2 * CX - x1, y0, 2 * CX - x0, y1) for k, (x0, y0, x1, y1) in parts.items()}
    return parts


def eye_flange(eye):
    """Aba do difusor: maior que a janela, para a peça não passar por ela."""
    c0, r0, c1, r1 = eye
    return (c0 * P - 2.8, r0 * P - 1.8, c1 * P + 2.8, r1 * P + 1.8)


BOSSES = [(x, y) for x in (IN[0] + 3.25, IN[2] - 3.25) for y in (IN[1] + 3.25, IN[3] - 3.25)]


def corpo() -> Manifold:
    solid = union([pixels(r, 0, SHELL) for r in [BODY, *ARMS, *LEGS]])  # braços e pernas maciços
    cavity = box(IN[0], IN[1], FACE, IN[2], IN[3], SHELL + 1)
    shell = solid - cavity
    for eye in EYES:  # tubo de luz: a tampinha com os LEDs encaixa nele, e ele não deixa vazar luz para dentro
        tube = eye_parts(eye)["tube"]
        shell += rbox(grow(tube, PW), FACE, TUBE_END) - rbox(tube, 0, TUBE_END + 1)
        shell -= pixels(eye, -1, FACE + 1)  # a janela do olho
    for x, y in BOSSES:  # torres dos parafusos da tampa (M2 × 8 autoatarraxante)
        shell += cyl(x, y, FACE, SHELL, 6.5)
        shell -= cyl(x, y, SHELL - 10, SHELL + 1, 1.7)
    shell += trilhos()
    shell -= union([notch for _, notch in snaps()])  # rebaixos dos dentes da tampa de encaixe
    # fenda embaixo, no meio da borda de trás: uma moeda ou chave de fenda ali levanta a tampa
    shell -= box(CX - 6, BODY[1] * P - 1, SHELL - 1, CX + 6, IN[1] - 1, SHELL + 1)
    return shell


def trilhos() -> Manifold:
    """Os dois trilhos da protoboard: uma parede de cada lado e uma aba por cima da borda. Vão do rosto até a tampa,
    então imprimem sem suporte."""
    lip_y = IN[1] + PB[2] + 0.3  # 0,3 mm de folga entre a protoboard e a aba
    rails = []
    for side in (-1, 1):
        edge = CX + side * PB[0] / 2  # lado da protoboard
        wall = sorted((edge + side * PB_GAP, edge + side * (PB_GAP + GUIDE)))
        lip = sorted((edge - side * PB_LIP, wall[1] if side < 0 else wall[0]))
        rails += [box(wall[0], IN[1] - 0.01, FACE, wall[1], lip_y + GUIDE, SHELL),
                  box(min(lip[0], wall[0]), lip_y, FACE, max(lip[1], wall[1]), lip_y + GUIDE, SHELL)]
    return union(rails)


def snaps() -> list[tuple[Manifold, Manifold]]:
    """(lingueta com o dente, rebaixo na parede do corpo) de cada encaixe, na posição montada. Dente e rebaixo têm
    rampas de 45°: a tampa entra e sai com a mão, e as peças imprimem sem suporte."""
    out = []
    for xc in TAB_X:
        yo = IN[3] - TAB_FIT  # face de fora da lingueta de cima
        z0, w = SHELL - TAB_L, TAB_W / 2
        tab = box(xc - w, yo - TAB_T, z0, xc + w, yo, SHELL)
        tooth = [(z0, yo - 0.2), (z0, yo), (z0 + BUMP, yo + BUMP), (z0 + BUMP + CREST, yo + BUMP),
                 (z0 + 2 * BUMP + CREST, yo), (z0 + 2 * BUMP + CREST, yo - 0.2)]
        deep, open_ = yo + BUMP + 0.1, IN[3] - 0.5  # o rebaixo passa 0,1 mm do dente e começa dentro da cavidade
        spread = deep - open_
        notch = [(z0 + BUMP - 0.2, deep), (z0 + BUMP + CREST + 0.2, deep),
                 (z0 + BUMP - 0.2 - spread, open_), (z0 + BUMP + CREST + 0.2 + spread, open_)]
        top = (tab + prism(tooth, xc - w, xc + w), prism(notch, xc - w - 0.3, xc + w + 0.3))
        bottom = tuple(m.mirror((0, 1, 0)).translate((0, IN[1] + IN[3], 0)) for m in top)  # o de baixo é o espelho
        out += [top, bottom]
    return out


def prism(profile, x0, x1):
    """Prisma de x0 a x1 com o perfil convexo [(z, y)]."""
    return Manifold.hull_points(np.array([(x, y, z) for z, y in profile for x in (x0, x1)], dtype=float))


def mcu_z():
    """Onde a placa fica em z: a borda da frente (dentro da tampa), a de trás e a frente da parede do suporte."""
    front = D - USB_OVERHANG  # assim o USB-C fica rente à tampa por fora
    back = front - MCU[1]
    return front, back, back - SLACK


def tampa(encaixe: bool = True) -> Manifold:
    """A tampa de trás, de encaixe (com as linguetas) ou de parafusos (M2 × 8 nas torres do corpo)."""
    plate = box(BODY[0] * P, BODY[1] * P, SHELL, BODY[2] * P, BODY[3] * P, D)
    front, _, _ = mcu_z()
    usb_y = MCU_Y + MCU_PCB + USB_C[1] / 2
    hw = MCU[0] / 2 + MCU_FIT
    holes = [
        # o furo do USB-C tem o tamanho do conector, que fica rente à tampa; o cabo encosta nela por fora
        stadium(CX, usb_y, SHELL - 1, D + 1, USB_C[0] + 2 * USB_FIT, USB_C[1] + 2 * USB_FIT),
        # rebaixo por dentro, para a borda da frente da placa (com o que estiver perto dela) entrar na tampa
        box(CX - hw, MCU_Y - 0.3, SHELL - 1, CX + hw, usb_y + USB_C[1] / 2 + USB_FIT + 0.5, front),
        cyl(*BTN, SHELL - 1, D + 1, CAP_D + 0.8),  # a capa do botão (liga e desliga) passa por aqui
    ]
    holes += [  # furos do som, na frente do buzzer
        cyl(96 + 3.2 * np.cos(a), 30 + 3.2 * np.sin(a), SHELL - 1, D + 1, 1.6) for a in np.arange(6) * np.pi / 3
    ] + [cyl(96, 30, SHELL - 1, D + 1, 1.6)]
    if not encaixe:
        for x, y in BOSSES:  # parafusos escareados
            holes += [cyl(x, y, SHELL - 1, D + 1, 2.3), cyl(x, y, D - 1.1, D + 0.01, 2.2, 4.4)]
    # berço do botão: a chave encosta na tampa por dentro, e a trava entra por trás e a segura
    inner = grow((*BTN, *BTN), BTN_SIZE / 2 + BTN_FIT)
    cradle = rbox(grow(inner, PW), SHELL - CRADLE, SHELL) - rbox(inner, SHELL - CRADLE - 1, SHELL + 1)
    legs = (inner[0] - PW - 1, BTN[1] - LEGS_SLOT / 2, inner[2] + PW + 1, BTN[1] + LEGS_SLOT / 2)
    cradle -= rbox(legs, SHELL - CRADLE - 1, SHELL + 1)
    lid = plate - union(holes) + cradle + suporte_da_placa()
    return lid + union([tab for tab, _ in snaps()]) if encaixe else lid


def suporte_da_placa() -> Manifold:
    """Guias dos lados, um apoio no meio, embaixo da placa (os pinos ficam livres), e a parede de trás."""
    _, _, wall = mcu_z()
    hw = MCU[0] / 2 + MCU_FIT
    top = MCU_Y + MCU_PCB + 2.5
    z0 = wall - GUIDE
    parts = [box(CX - MCU_RIB, MCU_Y - GUIDE, z0, CX + MCU_RIB, MCU_Y, SHELL)]
    parts += [box(x0, MCU_Y - GUIDE, z0, x0 + GUIDE, top, SHELL) for x0 in (CX - hw - GUIDE, CX + hw)]
    parts.append(box(CX - hw - GUIDE, MCU_Y - GUIDE, z0, CX + hw + GUIDE, top, wall))
    return union(parts)


def trava_da_placa() -> Manifold:
    """Entra por cima entre a placa e a parede de trás do suporte: empurra a placa contra a tampa e, com as duas
    linguetas, a segura por cima. As linguetas ficam fora do meio (a antena) e antes dos primeiros pinos."""
    _, back, wall = mcu_z()
    hw = MCU[0] / 2 + MCU_FIT
    pcb_top = MCU_Y + MCU_PCB
    x0, x1, z1 = CX - hw + PLUG_FIT, CX + hw - PLUG_FIT, back - 0.1
    latch = box(x0, pcb_top - 0.8, wall, x1, pcb_top + 4.0, z1)
    latch += union([box(CX + a, pcb_top + 0.05, z1 - 0.01, CX + b, pcb_top + 1.05, back + 1.0)
                    for a, b in ((-8.0, -4.5), (4.5, 8.0))])
    rib = Manifold.cylinder(pcb_top + 2.5 - (pcb_top - 0.2), 0.5, 0.5, 24).rotate((-90, 0, 0))  # nervura em pé (y)
    return latch + union([rib.translate((x, pcb_top - 0.2, (wall + z1) / 2)) for x in (x0 - RIB + 0.5, x1 + RIB - 0.5)])


def trava_do_botao() -> Manifold:
    """Entra no berço por trás até encostar na chave e a segura contra a tampa, com nervuras que apertam sem cola. Os
    entalhes das pontas deixam passar as pernas, já com os fios soldados."""
    bx, by = BTN
    x0, y0, x1, y1 = grow((bx, by, bx, by), BTN_SIZE / 2 + BTN_FIT - PLUG_FIT)
    z0, z1 = SHELL - BTN_BODY - LATCH, SHELL - BTN_BODY  # z1 encosta na chave
    latch = box(x0, y0, z0, x1, y1, z1)
    for nx0, nx1 in ((x0 - 1, bx - 5.2), (bx + 5.2, x1 + 1)):  # as pernas saem a 6,25 mm do centro
        latch -= box(nx0, by - LEGS_SLOT / 2, z0 - 1, nx1, by + LEGS_SLOT / 2, z1 + 1)
    ribs = [(bx + dx, y) for dx in (-3.5, 3.5) for y in (y0 - RIB + 0.5, y1 + RIB - 0.5)]
    return latch + union([cyl(x, y, z0, z1 - 0.6, 1.0) for x, y in ribs])  # a ponta sem nervura entra alinhada


def difusores() -> Manifold:
    """Os olhos brancos: rentes ao rosto, ocos e abertos atrás, com uma aba por dentro que não deixa a peça passar
    pela janela."""
    parts = []
    for eye in EYES:
        c0, r0, c1, r1 = eye
        window = (c0 * P + FIT, r0 * P + FIT, c1 * P - FIT, r1 * P - FIT)
        solid = rbox(window, 0, FACE) + rbox(eye_flange(eye), FACE, FACE + FLANGE)
        parts.append(solid - rbox(grow(window, -PW), SKIN, FACE + FLANGE + 1))
    return union(parts)


def tampas_dos_olhos() -> Manifold:
    """Encaixam no tubo de luz por trás, com nervuras que apertam sem cola e uma aba que para na ponta do tubo. As duas
    plaquinhas de LED colam no rebaixo da frente, viradas para o olho; os fios saem pelo canal."""
    parts = []
    for eye in EYES:
        r = eye_parts(eye)
        x0, y0, x1, y1 = r["plug"]
        px0, _, px1, _ = r["pocket"]
        outer_x = x0 if r["wires"][0] > px0 else x1  # a ponta sem canal, encostada na parede do corpo
        # a aba para na ponta do tubo, menos do lado da parede do corpo, onde ela bateria
        flange = grow(r["tube"], PW)
        flange = (x0, *flange[1:]) if outer_x == x0 else (*flange[:2], x1, flange[3])
        plug = rbox(r["plug"], LED_Z, TUBE_END) + rbox(flange, TUBE_END, TUBE_END + PW)
        plug -= rbox(r["pocket"], LED_Z - 1, LED_Z + POCKET_DEPTH)
        plug -= rbox(r["wires"], LED_Z - 1, TUBE_END + PW + 1)
        ribs = [(px0 + (px1 - px0) * f, y) for f in (0.25, 0.75) for y in (y0 - RIB + 0.5, y1 + RIB - 0.5)]
        ribs.append((outer_x - RIB + 0.5 if outer_x == x0 else outer_x + RIB - 0.5, (y0 + y1) / 2))
        # nervuras de 1 mm, começando 0,6 mm atrás da frente para a tampinha entrar alinhada
        plug += union([cyl(x, y, LED_Z + 0.6, TUBE_END, 1.0) for x, y in ribs])
        parts.append(plug)
    return union(parts)


def check_eyes() -> None:
    """Confere que as peças do olho cabem umas nas outras e no corpo."""
    for eye in EYES:
        r = eye_parts(eye)
        c0, r0, c1, r1 = eye
        led = ((r["pocket"][0] + r["pocket"][2]) / 2, (r["pocket"][1] + r["pocket"][3]) / 2)
        assert abs(led[0] - (c0 + c1) / 2 * P) < 1 and abs(led[1] - (r0 + r1) / 2 * P) < 0.01, "LEDs fora do olho"
        tube, flange = r["tube"], eye_flange(eye)
        assert tube[0] >= IN[0] - 1e-9 and tube[2] <= IN[2] + 1e-9, "tubo fora do corpo"
        inside = tube[0] < flange[0] and tube[1] < flange[1] and flange[2] < tube[2] and flange[3] < tube[3]
        assert inside, "a aba do difusor não cabe no tubo"
        assert grow(tube, PW)[3] < BOSSES[1][1] - 3.25, "tubo encosta nas torres dos parafusos"
    led_gap = LED_Z + POCKET_DEPTH - 0.3 - 1.6 - (FACE + FLANGE)  # plaquinha de fita (0,3 mm) e LED 5050 (1,6 mm)
    assert 3 < led_gap < 7, f"LEDs a {led_gap:.1f} mm do difusor"
    # montados, o difusor não entra no corpo, e a tampinha só entra no tubo pelo aperto das nervuras (uns 2,5 mm³)
    body = corpo()
    assert (body ^ difusores()).volume() < 0.01, "difusor bate no corpo"
    assert (body ^ tampas_dos_olhos()).volume() < 5, "tampinha do olho bate no corpo"


def check_button() -> None:
    """Confere o botão montado: a chave e as pernas cabem no berço, a capa passa livre pelo furo e a trava só aperta
    pelas nervuras."""
    bx, by = BTN
    s = BTN_SIZE / 2
    switch = box(bx - s, by - s, SHELL - BTN_BODY, bx + s, by + s, SHELL)
    base = SHELL - BTN_BODY
    legs = union([box(bx + x - 0.4, by + y - 0.4, base - 3.5, bx + x + 0.4, by + y + 0.4, base + 0.5)
                  for x in (-6.25, 6.25) for y in (-2.5, 2.5)])  # 12,5 × 5 mm entre as pernas
    cap = cyl(bx, by, SHELL + 0.3, D + 6, CAP_D)  # a borda da capa fica um pouco acima da chapa da chave
    lid, latch = tampa(), trava_do_botao()
    for name, part in [("a chave", switch), ("as pernas", legs), ("a capa", cap)]:
        assert (lid ^ part).volume() < 1e-6, f"{name} bate na tampa"
    assert (latch ^ (switch + legs)).volume() < 1e-6, "a trava bate na chave"
    assert 0 < (lid ^ latch).volume() < 3, "a trava não aperta só pelas nervuras"
    assert (corpo() ^ lid).volume() < 1e-6, "o berço do botão bate no corpo"


def check_lids() -> None:
    """As duas tampas fecham no mesmo corpo sem bater; a de encaixe com os dentes dentro dos rebaixos."""
    body = corpo()
    for encaixe in (True, False):
        assert (body ^ tampa(encaixe)).volume() < 1e-6, f"a tampa ({encaixe=}) bate no corpo"
    assert 0.3 <= BUMP - TAB_FIT <= 0.5, "a lingueta precisa dobrar uns 0,4 mm para o dente passar"
    for tab, _ in snaps():
        assert (body ^ tab.translate((0, 0, -BUMP - CREST))).volume() > 0.1, "o dente não segura a tampa"


def check_mcu() -> None:
    """A placa entra no suporte e fica com o USB-C rente à tampa; a trava só aperta pelas nervuras."""
    front, back, wall = mcu_z()
    pcb_top = MCU_Y + MCU_PCB
    board = box(CX - MCU[0] / 2, MCU_Y, back, CX + MCU[0] / 2, pcb_top, front)
    board += stadium(CX, pcb_top + USB_C[1] / 2, D - 7.35, D, *USB_C)  # o USB-C, rente à tampa
    lid, latch = tampa(), trava_da_placa()
    assert (lid ^ board).volume() < 1e-6, "a placa bate na tampa"
    loose = board.translate((0, 0, -SLACK))  # antes de deslizar: entra por cima, encostada na parede de trás
    assert (lid ^ (loose + loose.translate((0, 25, 0))).hull()).volume() < 1e-6, "a placa não entra por cima"
    assert (latch ^ board).volume() < 1e-6, "a trava bate na placa"
    assert 0 < (lid ^ latch).volume() < 3, "a trava não aperta só pelas nervuras"
    assert (lid ^ latch.translate((0, 6, 0))).volume() < 1e-6, "a trava não sai por cima"
    parts = box(CX - PB[0] / 2 + 3, IN[1] + PB[2], FACE + 0.5, CX + PB[0] / 2 - 3, IN[1] + PB[2] + 11, SHELL)
    assert (lid ^ parts).volume() < 1e-6, "o suporte da placa bate nos componentes da protoboard (11 mm)"
    # as pernas: duas fileiras de 8, a 7,62 mm do meio, a primeira a 2,37 mm da borda de trás
    rows = [box(CX + x - 1.27, MCU_Y - MCU_LEGS, back + 1.1, CX + x + 1.27, MCU_Y, back + 21.4) for x in (-7.62, 7.62)]
    legs = union(rows)
    assert (lid ^ legs).volume() < 1e-6 and (latch ^ legs).volume() < 1e-6, "as pernas batem no suporte ou na trava"
    sweep = union([(r + r.translate((0, 25, 0))).hull().translate((0, 0, -SLACK)) for r in rows])
    assert (lid ^ sweep).volume() < 1e-6, "as pernas não passam ao pôr a placa por cima"
    assert MCU_Y - MCU_LEGS >= IN[1] + PB[2] + PB_PARTS, "as pernas batem nos componentes da protoboard"


def check_protoboard() -> None:
    """A protoboard cabe entre os trilhos, entra deslizando por trás e não bate na tampa."""
    body, board = corpo(), box(CX - PB[0] / 2, IN[1], FACE + 0.5, CX + PB[0] / 2, IN[1] + PB[2], FACE + 0.5 + PB[1])
    assert FACE + 0.5 + PB[1] <= SHELL, "a protoboard não cabe entre o rosto e a tampa"
    assert (body ^ board).volume() < 1e-6, "a protoboard bate nos trilhos"
    assert (body ^ (board + board.translate((0, 0, D))).hull()).volume() < 1e-6, "a protoboard não entra por trás"
    assert (tampa() ^ board).volume() < 1e-6, "a protoboard bate na tampa"
    assert PB_LIP < 3.5, "a aba passaria dos furos da protoboard (a borda sem furos tem uns 4 mm)"
    # do lado sem dentinho, mesmo com a protoboard encostada no outro trilho, a aba ainda cobre 1 mm da borda
    assert PB_LIP - PB_TOOTH - PB_GAP >= 1, "a protoboard pode escorregar de lado e soltar de uma aba"


def flip(m: Manifold, z_top: float) -> Manifold:
    """Vira a peça de cabeça para baixo (gira 180° em y) mantendo o lugar em x: o que era z_top encosta na mesa."""
    return m.rotate((0, 180, 0)).translate((16 * P, 0, z_top))


def save(m: Manifold, name: str, size: tuple[float, float, float]) -> None:
    lo, hi = np.array(m.bounding_box()[:3]), np.array(m.bounding_box()[3:])
    assert not m.is_empty() and np.allclose(lo[2], 0, atol=1e-6), f"{name}: precisa encostar na mesa (z = 0)"
    assert np.allclose(hi - lo, size, atol=0.01), f"{name}: tamanho {hi - lo}, esperado {size}"
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3]
    tri = v[np.asarray(mesh.tri_verts)]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    data = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"], data["v"] = n, tri
    with open(OUT / name, "wb") as f:
        f.write(b"Claude Code Companion".ljust(80))
        f.write(np.uint32(len(tri)).tobytes())
        f.write(data.tobytes())
    print(f"{name}: {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} x {hi[2] - lo[2]:.1f} mm, {len(tri)} triângulos")


def at(m: Manifold, x: float, y: float) -> Manifold:
    """Põe o canto da peça em (x, y) na mesa."""
    lo = m.bounding_box()
    return m.translate((x - lo[0], y - lo[1], 0))


if __name__ == "__main__":
    check_eyes()
    check_button()
    check_lids()
    check_mcu()
    check_protoboard()
    diff_w = eye_flange(EYES[1])[2] - eye_flange(EYES[0])[0]
    cap = grow(eye_parts(EYES[0])["tube"], PW)
    latch_w = BTN_SIZE + 2 * (BTN_FIT - PLUG_FIT)
    lid_size = (12 * P, 8 * P, D - mcu_z()[2] + GUIDE)
    mcu_latch_w = MCU[0] + 2 * (MCU_FIT - PLUG_FIT + RIB)
    cap_w, cap_h = 2 * CX - 2 * (eye_parts(EYES[0])["plug"][0] - RIB), cap[3] - cap[1]  # com as nervuras das pontas
    parts = {
        "corpo.stl": (corpo(), (16 * P, 10 * P, SHELL)),
        # o lado de fora na mesa; o berço do botão e o suporte da placa para cima
        "tampa-encaixe.stl": (flip(tampa(True), D), lid_size),
        "tampa-parafusos.stl": (flip(tampa(False), D), lid_size),
        "difusores.stl": (flip(difusores(), FACE + FLANGE), (diff_w, 2 * P + 3.6, FACE + FLANGE)),
        # com a aba na mesa e o rebaixo dos LEDs para cima
        "tampas-dos-olhos.stl": (flip(tampas_dos_olhos(), TUBE_END + PW), (cap_w, cap_h, TUBE_END + PW - LED_Z)),
        "trava-do-botao.stl": (
            trava_do_botao().translate((0, 0, LATCH + BTN_BODY - SHELL)),
            (latch_w, latch_w + 2 * RIB, LATCH),
        ),
        # deitada, com as linguetas para cima
        "trava-da-placa.stl": (trava_da_placa().translate((0, 0, -mcu_z()[2])), (mcu_latch_w, 4.8, SLACK + 1)),
    }
    for name, (m, size) in parts.items():
        save(m, name, size)
    # Uma mesa com as seis peças de um Companion (com a tampa de encaixe), 10 mm entre elas: cabe em 220 × 220 mm (a
    # menor mesa da linha Anycubic Kobra). No fatiador, "dividir em objetos" separa as peças para dar o branco aos
    # difusores.
    gap = 10
    body, lid, _, diff, caps, latch, mcu_latch = (parts[n][0] for n in parts)
    side = 16 * P + gap
    plate = union([at(body, 0, 0), at(lid, 0, 10 * P + gap), at(diff, side, 0), at(caps, 12 * P + gap, 10 * P + gap),
                   at(latch, side, 2 * P + 3.6 + gap), at(mcu_latch, side + latch_w + gap, 2 * P + 3.6 + gap)])
    save(plate, "mesa.stl", (max(side + diff_w, 12 * P + gap + cap_w), 10 * P + gap + 8 * P, SHELL))
