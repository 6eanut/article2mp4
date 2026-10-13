from manim import FadeIn, VGroup, Text, Line, DOWN, UP, RIGHT
from ..style import FONT, FG, ACCENT
from . import entrance_hold
from ._fit import fit_group


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=ACCENT[0])
    root = Text(props["root"], font=FONT, font_size=30, color=ACCENT[0]).shift(UP * 1.2)
    kids = VGroup()
    for row in props["children"]:
        for c in row:
            kids.add(Text(c, font=FONT, font_size=24, color=FG))
    kids.arrange(RIGHT, buff=1.0).shift(DOWN * 0.6)
    edges = VGroup(*[Line(root.get_bottom(), k.get_top(), color=ACCENT[2], stroke_width=2)
                     for k in kids])
    graph = VGroup(edges, root, kids)
    body = VGroup(h, graph).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)