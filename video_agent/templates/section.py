from manim import DOWN, FadeIn, Text, VGroup

from ..style import ACCENT, FG, FONT
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    idx = Text(f"{props['index']:02d}", font=FONT, font_size=90, weight="BOLD", color=ACCENT[1])
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=42, color=FG)
    body = VGroup(idx, h).arrange(DOWN, buff=0.25)
    fit_group(body)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.3), duration)
