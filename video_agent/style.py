from __future__ import annotations
import numpy as np
from manim import (
    VGroup, Text, RoundedRectangle, Line, Cross, DOWN, NORMAL, BOLD, config,
)

FONT = "Noto Sans SC"
BG = "#0F172A"
PANEL = "#1E293B"
FG = "#F8FAFC"
MUTED = "#94A3B8"
DIM = "#475569"
RED = "#F87171"
ACCENT = ["#38BDF8", "#818CF8", "#A78BFA", "#F472B6", "#34D399"]


def apply_manim_config() -> None:
    config.background_color = BG
    config.disable_caching = True


def chip(text, color=ACCENT[0], font_size=30, fill=PANEL):
    t = Text(text, font=FONT, font_size=font_size, color=FG)
    box = RoundedRectangle(
        corner_radius=0.16, width=t.width + 0.8, height=t.height + 0.5,
        fill_color=fill, fill_opacity=1, stroke_color=color, stroke_width=2,
    )
    t.move_to(box.get_center())
    return VGroup(box, t)


def badge(text, color):
    g = chip(text, color=color, font_size=30, fill=BG)
    g[1].set_weight(BOLD)
    return g


def heading(main, sub=None, sub_color=ACCENT[0]):
    m = Text(main, font=FONT, font_size=40, weight=BOLD, color=FG)
    if sub is None:
        return VGroup(m)
    s = Text(sub, font=FONT, font_size=25, color=sub_color)
    return VGroup(m, s).arrange(DOWN, buff=0.18)


def tick(color, scale=1.0):
    p1 = np.array([-0.16, 0.02, 0])
    p2 = np.array([-0.02, -0.14, 0])
    p3 = np.array([0.2, 0.16, 0])
    g = VGroup(
        Line(p1, p2, color=color, stroke_width=5),
        Line(p2, p3, color=color, stroke_width=5),
    )
    return g.scale(scale)


def cand_box(mark, color, size=0.68):
    box = RoundedRectangle(
        corner_radius=0.12, width=size, height=size,
        fill_color=PANEL, fill_opacity=1, stroke_color=color, stroke_width=2,
    )
    if mark == "tick":
        g = tick(color).scale(0.9).move_to(box)
    else:
        g = Cross(color=RED, stroke_width=5).scale(0.5).move_to(box)
    return VGroup(box, g)