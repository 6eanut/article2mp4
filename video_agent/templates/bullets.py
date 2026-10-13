from manim import FadeIn, VGroup, Text, DOWN, LEFT
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    items = VGroup(*[
        Text(f"· {it}", font=FONT, font_size=30, color=ACCENT[i % len(ACCENT)])
        for i, it in enumerate(props["items"])
    ]).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    body = VGroup(h, items).arrange(DOWN, buff=0.5)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)