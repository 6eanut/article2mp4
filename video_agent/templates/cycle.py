import numpy as np
from manim import DOWN, CurvedArrow, FadeIn, VGroup

from ..style import ACCENT, FONT
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=ACCENT[0])
    n = len(props["nodes"])
    r = 2.8
    pos = [np.array([r * np.cos(2 * np.pi * i / n), r * np.sin(2 * np.pi * i / n), 0])
           for i in range(n)]
    node_width = min(3.0, 2 * r * np.sin(np.pi / max(n, 2)) - 0.35)
    nodes = VGroup(*[
        wrapped_text(props["nodes"][i], max_width=node_width, font=FONT,
                     font_size=26, color=ACCENT[i % len(ACCENT)]).move_to(pos[i])
        for i in range(n)
    ])
    def boundary_gap(node, direction):
        dx, dy = abs(direction[0]), abs(direction[1])
        edges = [node.width / (2 * dx) if dx > 1e-9 else float("inf"),
                 node.height / (2 * dy) if dy > 1e-9 else float("inf")]
        return min(edges) + 0.35

    arrows = VGroup()
    for i in range(n):
        next_i = (i + 1) % n
        delta = pos[next_i] - pos[i]
        length = np.linalg.norm(delta)
        if length < 1e-9:
            continue
        direction = delta / length
        start = pos[i] + direction * boundary_gap(nodes[i], direction)
        end = pos[next_i] - direction * boundary_gap(nodes[next_i], direction)
        arrows.add(CurvedArrow(start, end, angle=-np.pi / 4, color=ACCENT[0]))
    ring = VGroup(arrows, nodes)
    body = VGroup(h, ring).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
