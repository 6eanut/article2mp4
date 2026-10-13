from manim import FadeIn, VGroup, Text, DOWN, RIGHT
from ..style import FONT, FG, ACCENT
from . import entrance_hold
from ._fit import fit_group, fit_width


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    chips = VGroup(*[
        Text(i, font=FONT, font_size=28, color=ACCENT[k % len(ACCENT)])
        for k, i in enumerate(props["items"])
    ]).arrange(RIGHT, buff=0.4)
    body = VGroup(fit_width(h), chips).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)