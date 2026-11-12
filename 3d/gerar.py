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
CHAMBER = 10.0  # o tubo de luz de cada olho vai do rosto até aqui (z)
FIT = 0.125  # folga de cada lado do difusor na janela do olho

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


def chamber(eye, grow=0.0):
    """Retângulo do tubo de luz: a janela do olho com 3 mm de folga nos lados e 2 mm em cima e embaixo."""
    c0, r0, c1, r1 = eye
    return (c0 * P - 3 - grow, r0 * P - 2 - grow, c1 * P + 3 + grow, r1 * P + 2 + grow)


BOSSES = [(x, y) for x in (IN[0] + 3.25, IN[2] - 3.25) for y in (IN[1] + 3.25, IN[3] - 3.25)]


def corpo() -> Manifold:
    solid = union([pixels(r, 0, SHELL) for r in [BODY, *ARMS, *LEGS]])  # braços e pernas maciços
    cavity = box(IN[0], IN[1], FACE, IN[2], IN[3], SHELL + 1)
    shell = solid - cavity
    for eye in EYES:  # tubo de luz: segura os LEDs a uns 6 mm do difusor e não deixa vazar luz para dentro
        shell += box(*chamber(eye, 1.2)[:2], FACE, *chamber(eye, 1.2)[2:], CHAMBER) - box(
            *chamber(eye)[:2], 0, *chamber(eye)[2:], CHAMBER + 1
        )
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
    """Os olhos brancos: rentes ao rosto, com uma aba por dentro que não deixa a peça passar pela janela."""
    parts = []
    for eye in EYES:
        c0, r0, c1, r1 = eye
        parts.append(box(c0 * P + FIT, r0 * P + FIT, 0, c1 * P - FIT, r1 * P - FIT, FACE))
        x0, y0, x1, y1 = chamber(eye, -0.2)
        parts.append(box(x0, y0, FACE, x1, y1, FACE + 0.8))
    return union(parts)


def tampas_dos_olhos() -> Manifold:
    """Fecham o tubo de luz por trás; o pedaço de fita de LED cola no lado de dentro, virado para o olho."""
    parts = []
    for eye in EYES:
        x0, y0, x1, y1 = chamber(eye, 1.2)
        cx = (x0 + x1) / 2
        parts.append(box(x0, y0, CHAMBER, x1, y1, CHAMBER + 1.2) - box(cx - 2.5, y0 - 1, CHAMBER - 1, cx + 2.5, y0 + 3, CHAMBER + 2))
    return union(parts)


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
    eye_w = EYES[1][2] * P + 3 + 1.2 - (EYES[0][0] * P - 3 - 1.2)
    diff_w = EYES[1][2] * P + 3 - 0.2 - (EYES[0][0] * P - 3 + 0.2)
    parts = {
        "corpo.stl": (corpo(), (16 * P, 10 * P, SHELL)),
        "tampa.stl": (flip(tampa(), D), (12 * P, 8 * P, LID)),
        "difusores.stl": (flip(difusores(), FACE + 0.8), (diff_w, 2 * P + 4 - 0.4, FACE + 0.8)),
        "tampas-dos-olhos.stl": (tampas_dos_olhos().translate((0, 0, -CHAMBER)), (eye_w, 2 * P + 4 + 2.4, 1.2)),
    }
    for name, (m, size) in parts.items():
        save(m, name, size)
    # Uma mesa com as quatro peças de um Companion, 10 mm entre elas: cabe em 220 × 220 mm (a menor mesa da linha
    # Anycubic Kobra). No fatiador, "dividir em objetos" separa as peças para dar o branco aos difusores.
    gap = 10
    body, lid, diff, caps = (parts[n][0] for n in parts)
    side = 16 * P + gap
    plate = union([at(body, 0, 0), at(lid, 0, 10 * P + gap), at(diff, side, 0), at(caps, side, 2 * P + 4 + gap)])
    save(plate, "mesa.stl", (side + max(diff_w, eye_w), 10 * P + gap + 8 * P, SHELL))
