from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, ACCENT, MUTED
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    val = Text(f"{props['value']}{props.get('unit', '')}",
               font=FONT, font_size=90, weight="BOLD", color=ACCENT[3])
    lbl = Text(props["label"], font=FONT, font_size=26, color=MUTED)
    body = VGroup(h, val, lbl).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)