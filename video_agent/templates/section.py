from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    idx = Text(f"{props['index']:02d}", font=FONT, font_size=90, weight="BOLD", color=ACCENT[1])
    h = Text(props["heading"], font=FONT, font_size=42, color=FG)
    body = VGroup(idx, h).arrange(DOWN, buff=0.25)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.3), duration)