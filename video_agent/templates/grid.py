from manim import FadeIn, VGroup, Text, DOWN, RIGHT
from ..style import FONT, FG, ACCENT, cand_box
from . import entrance_hold
from ._fit import fit_group


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    boxes = VGroup()
    for i, c in enumerate(props["cells"]):
        box = cand_box(c.get("mark", "cross"), ACCENT[i % len(ACCENT)])
        lbl = Text(c["label"], font=FONT, font_size=24, color=FG).next_to(box, DOWN, buff=0.18)
        boxes.add(VGroup(box, lbl))
    boxes.arrange(RIGHT, buff=0.6)
    body = VGroup(h, boxes).arrange(DOWN, buff=0.7)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)