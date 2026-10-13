from manim import DOWN, RIGHT, FadeIn, VGroup

from ..style import ACCENT, FG, FONT, cand_box
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=FG)
    boxes = VGroup()
    label_width = min(4.0, max(2.2, 11.8 / max(len(props["cells"]), 1) - 0.5))
    for i, c in enumerate(props["cells"]):
        box = cand_box(c.get("mark", "cross"), ACCENT[i % len(ACCENT)])
        lbl = wrapped_text(c["label"], max_width=label_width,
                           font=FONT, font_size=24, color=FG).next_to(box, DOWN, buff=0.18)
        boxes.add(VGroup(box, lbl))
    boxes.arrange(RIGHT, buff=0.6)
    body = VGroup(h, boxes).arrange(DOWN, buff=0.7)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
