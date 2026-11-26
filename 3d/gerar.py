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
D = 52.0  # profundidade total, do rosto às costas
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

# O mascote em pixels: (coluna, linha) a partir do canto de baixo à esquerda (ele é simétrico)
BODY = (2, 2, 14, 10)
ARMS = [(0, 4, 2, 6), (14, 4, 16, 6)]
LEGS = [(c, 0, c + 1, 2) for c in (3, 5, 10, 12)]
EYES = [(4, 6, 5, 8), (11, 6, 12, 8)]

SHELL = D - LID  # o corpo vai de z = 0 até aqui; a tampa fecha o resto
CX = 8 * P  # centro do mascote em x
IN = (BODY[0] * P + WALL, BODY[1] * P + WALL, BODY[2] * P - WALL, BODY[3] * P - WALL)  # a cavidade (x0, y0, x1, y1)
USB_Y = IN[1] + 8.5 + 2.5 + 1.0 + 1.6  # chão + protoboard + espaçador dos pinos + placa + metade do USB-C
OUT = Path(__file__).parent


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl(x, y, z0, z1, d, d1=None):
    return Manifold.cylinder(z1 - z0, d / 2, (d1 or d) / 2, circular_segments=48).translate((x, y, z0))


def pixels(rect, z0, z1):
    c0, r0, c1, r1 = rect
    return box(c0 * P, r0 * P, z0, c1 * P, r1 * P, z1)


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
    # superpoder da cabeça: rasgo para uma barra de pinos fêmea de 3 vias (VLED, dados, GND)
    shell -= box(CX - 4.2, BODY[3] * P - WALL - 1, SHELL / 2 - 1.6, CX + 4.2, BODY[3] * P + 1, SHELL / 2 + 1.6)
    return shell


def tampa() -> Manifold:
    plate = box(BODY[0] * P, BODY[1] * P, SHELL, BODY[2] * P, BODY[3] * P, D)
    holes = [
        # USB-C do XIAO, que fica na protoboard encostada na tampa
        box(CX - 7 + 4.5, USB_Y - 4.5, SHELL - 1, CX + 7 - 4.5, USB_Y + 4.5, D + 1),
        cyl(CX - 7 + 4.5, USB_Y, SHELL - 1, D + 1, 9),
        cyl(CX + 7 - 4.5, USB_Y, SHELL - 1, D + 1, 9),
        cyl(36, 64, SHELL - 1, D + 1, 7.2),  # botão de painel de 7 mm (liga e desliga)
        box(92 - 4, 64 - 2.5, SHELL - 1, 92 + 4, 64 + 2.5, D + 1),  # superpoder das costas: conector Qwiic
    ]
    holes += [  # furos do som, na frente do buzzer
        cyl(96 + 3.2 * np.cos(a), 30 + 3.2 * np.sin(a), SHELL - 1, D + 1, 1.6) for a in np.arange(6) * np.pi / 3
    ] + [cyl(96, 30, SHELL - 1, D + 1, 1.6)]
    for x, y in BOSSES:  # parafusos escareados
        holes += [cyl(x, y, SHELL - 1, D + 1, 2.3), cyl(x, y, D - 1.1, D + 0.01, 2.2, 4.4)]
    return plate - union(holes)


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
    diff_w = eye_flange(EYES[1])[2] - eye_flange(EYES[0])[0]
    cap = grow(eye_parts(EYES[0])["tube"], PW)
    cap_w, cap_h = 2 * CX - 2 * (eye_parts(EYES[0])["plug"][0] - RIB), cap[3] - cap[1]  # com as nervuras das pontas
    parts = {
        "corpo.stl": (corpo(), (16 * P, 10 * P, SHELL)),
        "tampa.stl": (flip(tampa(), D), (12 * P, 8 * P, LID)),
        "difusores.stl": (flip(difusores(), FACE + FLANGE), (diff_w, 2 * P + 3.6, FACE + FLANGE)),
        # com a aba na mesa e o rebaixo dos LEDs para cima
        "tampas-dos-olhos.stl": (flip(tampas_dos_olhos(), TUBE_END + PW), (cap_w, cap_h, TUBE_END + PW - LED_Z)),
    }
    for name, (m, size) in parts.items():
        save(m, name, size)
    # Uma mesa com as quatro peças de um Companion, 10 mm entre elas: cabe em 220 × 220 mm (a menor mesa da linha
    # Anycubic Kobra). No fatiador, "dividir em objetos" separa as peças para dar o branco aos difusores.
    gap = 10
    body, lid, diff, caps = (parts[n][0] for n in parts)
    side = 16 * P + gap
    plate = union([at(body, 0, 0), at(lid, 0, 10 * P + gap), at(diff, side, 0), at(caps, 12 * P + gap, 10 * P + gap)])
    save(plate, "mesa.stl", (max(side + diff_w, 12 * P + gap + cap_w), 10 * P + gap + 8 * P, SHELL))
