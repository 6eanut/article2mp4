from manim import DOWN, FadeIn, Text, VGroup

from ..style import ACCENT, FG, FONT, MUTED
from . import entrance_hold
from ._fit import fit_group, fit_width, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=FG)
    val = Text(f"{props['value']}{props.get('unit', '')}",
               font=FONT, font_size=90, weight="BOLD", color=ACCENT[3])
    lbl = wrapped_text(props["label"], max_width=11.0, font=FONT,
                       font_size=26, color=MUTED)
    body = VGroup(fit_width(h), fit_width(val), fit_width(lbl)).arrange(DOWN, buff=0.4)
    fit_group(body)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)
