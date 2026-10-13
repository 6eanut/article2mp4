from manim import DOWN, RIGHT, UP, FadeIn, Line, VGroup

from ..style import ACCENT, FG, FONT
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=ACCENT[0])
    root = wrapped_text(props["root"], max_width=10.0, font=FONT,
                        font_size=30, color=ACCENT[0]).shift(UP * 1.2)
    kids = VGroup()
    kid_count = sum(len(row) for row in props["children"])
    kid_width = min(3.2, max(1.8, 11.0 / max(kid_count, 1) - 0.5))
    for row in props["children"]:
        for c in row:
            kids.add(wrapped_text(c, max_width=kid_width,
                                  font=FONT, font_size=24, color=FG))
    kids.arrange(RIGHT, buff=1.0).shift(DOWN * 0.6)
    edges = VGroup(*[Line(root.get_bottom(), k.get_top(), color=ACCENT[2], stroke_width=2)
                     for k in kids])
    graph = VGroup(edges, root, kids)
    body = VGroup(h, graph).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
