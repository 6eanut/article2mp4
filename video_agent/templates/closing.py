from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, MUTED
from . import entrance_hold


def render(props, duration, subtitle=None):
    t = Text(props["text"], font=FONT, font_size=44, weight="BOLD", color=FG)
    parts = VGroup(t)
    if props.get("handle"):
        h = Text(props["handle"], font=FONT, font_size=24, color=MUTED)
        parts = VGroup(t, h).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(parts), duration)