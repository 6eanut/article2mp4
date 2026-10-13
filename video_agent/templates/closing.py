from manim import DOWN, FadeIn, VGroup

from ..style import FG, FONT, MUTED
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    t = wrapped_text(props["text"], max_width=11.8, font=FONT,
                     font_size=44, weight="BOLD", color=FG)
    parts = VGroup(t)
    if props.get("handle"):
        h = wrapped_text(props["handle"], max_width=11.0, font=FONT,
                         font_size=24, color=MUTED)
        parts = VGroup(t, h).arrange(DOWN, buff=0.4)
    fit_group(parts)
    return entrance_hold(FadeIn(parts), duration)
