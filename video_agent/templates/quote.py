from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, MUTED
from . import entrance_hold
from ._fit import fit_group, fit_width


def render(props, duration, subtitle=None):
    q = fit_width(Text(f"“{props['text']}”", font=FONT, font_size=46, weight="BOLD", color=FG))
    parts = VGroup(q)
    if props.get("source"):
        s = fit_width(Text(f"— {props['source']}", font=FONT, font_size=26, color=MUTED))
        parts = VGroup(q, s).arrange(DOWN, buff=0.4)
    fit_group(parts)
    return entrance_hold(FadeIn(parts), duration)