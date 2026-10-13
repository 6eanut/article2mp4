from manim import DOWN, LEFT, RIGHT, UP, Dot, FadeIn, Line, VGroup

from ..style import ACCENT, DIM, FG, FONT, tick
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=FG)
    n = len(props["steps"])
    label_width = min(3.0, max(1.8, 11.0 / max(n, 1) - 0.5))
    dots = VGroup(*[Dot(radius=0.14, color=ACCENT[0]) for _ in range(n)]).arrange(
        RIGHT, buff=label_width + 0.25)
    first = dots[0].get_center() if n else LEFT * 0.1
    last = dots[-1].get_center() if n > 1 else RIGHT * 0.1
    line = Line(first, last, color=DIM, stroke_width=3)
    labels = VGroup(*[wrapped_text(s, max_width=label_width,
                                   font=FONT, font_size=26, color=FG)
                      for s in props["steps"]])
    for i in range(n):
        labels[i].next_to(dots[i], DOWN, buff=0.3)
    marks = VGroup()
    if props.get("done_index") is not None:
        for i in range(props["done_index"] + 1):
            marks.add(tick(ACCENT[4]).next_to(dots[i], UP, buff=0.2))
    track = VGroup(line, dots, labels, marks)
    body = VGroup(h, track).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
