from manim import DOWN, FadeIn, VGroup

from ..style import FG, FONT, MUTED
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    q = wrapped_text(f"“{props['text']}”", max_width=11.8, font=FONT,
                     font_size=46, weight="BOLD", color=FG)
    parts = VGroup(q)
    if props.get("source"):
        s = wrapped_text(f"— {props['source']}", max_width=11.0, font=FONT,
                         font_size=26, color=MUTED)
        parts = VGroup(q, s).arrange(DOWN, buff=0.4)
    fit_group(parts)
    return entrance_hold(FadeIn(parts), duration)
