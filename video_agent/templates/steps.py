from manim import FadeIn, VGroup, Text, Dot, Line, DOWN, UP, LEFT, RIGHT
from ..style import FONT, FG, DIM, ACCENT, tick
from . import entrance_hold
from ._fit import fit_group


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    n = len(props["steps"])
    line = Line(LEFT * (n * 0.6), RIGHT * (n * 0.6), color=DIM, stroke_width=3)
    dots = VGroup(*[Dot(radius=0.14, color=ACCENT[0]) for _ in range(n)]).arrange(RIGHT, buff=1.2)
    dots.move_to(line.get_center())
    labels = VGroup(*[Text(s, font=FONT, font_size=26, color=FG) for s in props["steps"]])
    for i in range(n):
        labels[i].next_to(dots[i], DOWN, buff=0.3)
    marks = VGroup()
    if props.get("done_index") is not None:
        for i in range(props["done_index"] + 1):
            marks.add(tick(ACCENT[4]).next_to(dots[i], UP, buff=0.2))
    body = VGroup(h, line, dots, labels, marks).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)