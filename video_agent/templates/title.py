from manim import FadeIn, VGroup, Text, DOWN, UP
from ..style import FONT, FG, ACCENT
from . import entrance_hold
from ._fit import fit_group


def render(props, duration, subtitle=None):
    t = Text(props["title"], font=FONT, font_size=56, weight="BOLD", color=FG)
    parts = VGroup(t)
    if props.get("subtitle"):
        s = Text(props["subtitle"], font=FONT, font_size=30, color=ACCENT[0])
        parts = VGroup(t, s).arrange(DOWN, buff=0.3)
    fit_group(parts)
    return entrance_hold(FadeIn(parts, shift=UP * 0.4), duration)