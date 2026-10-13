from manim import DOWN, UP, FadeIn, VGroup

from ..style import ACCENT, FG, FONT
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    t = wrapped_text(props["title"], max_width=11.8, font=FONT,
                     font_size=56, weight="BOLD", color=FG)
    parts = VGroup(t)
    if props.get("subtitle"):
        s = wrapped_text(props["subtitle"], max_width=11.0, font=FONT,
                         font_size=30, color=ACCENT[0])
        parts = VGroup(t, s).arrange(DOWN, buff=0.3)
    fit_group(parts)
    return entrance_hold(FadeIn(parts, shift=UP * 0.4), duration)
