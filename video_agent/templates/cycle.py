import numpy as np
from manim import FadeIn, VGroup, Text, CurvedArrow, DOWN
from ..style import FONT, ACCENT
from . import entrance_hold
from ._fit import fit_group


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=ACCENT[0])
    n = len(props["nodes"])
    r = 1.6
    pos = [np.array([r * np.cos(2 * np.pi * i / n), r * np.sin(2 * np.pi * i / n), 0])
           for i in range(n)]
    nodes = VGroup(*[
        Text(props["nodes"][i], font=FONT, font_size=26, color=ACCENT[i % len(ACCENT)]).move_to(pos[i])
        for i in range(n)
    ])
    arrows = VGroup(*[
        CurvedArrow(pos[i], pos[(i + 1) % n], angle=-np.pi / 4, color=ACCENT[0])
        for i in range(n)
    ])
    ring = VGroup(arrows, nodes)
    body = VGroup(h, ring).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)