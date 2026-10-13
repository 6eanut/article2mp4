from manim import FadeIn, VGroup, Text, DOWN, RIGHT, LEFT
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def _col(side, color):
    t = Text(side["title"], font=FONT, font_size=34, weight="BOLD", color=color)
    items = VGroup(*[Text(f"· {i}", font=FONT, font_size=26, color=FG) for i in side["items"]]
                   ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
    return VGroup(t, items).arrange(DOWN, buff=0.3)


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    left = _col(props["left"], ACCENT[0])
    right = _col(props["right"], ACCENT[3])
    cols = VGroup(left, right).arrange(RIGHT, buff=1.2)
    body = VGroup(h, cols).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)