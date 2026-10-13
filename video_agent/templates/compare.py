from manim import FadeIn, VGroup, Text, DOWN, RIGHT, LEFT
from ..style import FONT, FG, ACCENT
from . import entrance_hold
from ._fit import fit_group, fit_width, FRAME_SAFE_WIDTH


def _col(side, color):
    # Two columns sit side by side, so each column may use only about half the
    # safe width.
    col_max = FRAME_SAFE_WIDTH / 2 - 0.3
    t = fit_width(Text(side["title"], font=FONT, font_size=34, weight="BOLD", color=color),
                  col_max)
    items = VGroup(*[fit_width(Text(f"· {i}", font=FONT, font_size=26, color=FG), col_max)
                     for i in side["items"]]
                   ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
    return VGroup(t, items).arrange(DOWN, buff=0.3)


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    left = _col(props["left"], ACCENT[0])
    right = _col(props["right"], ACCENT[3])
    cols = VGroup(left, right).arrange(RIGHT, buff=1.2)
    body = VGroup(fit_width(h), cols).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)