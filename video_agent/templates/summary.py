from manim import DOWN, RIGHT, FadeIn, VGroup

from ..style import ACCENT, FG, FONT
from . import entrance_hold
from ._fit import fit_group, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=FG)
    item_width = min(4.0, max(2.0, 11.6 / max(len(props["items"]), 1) - 0.4))
    chips = VGroup(*[
        wrapped_text(i, max_width=item_width, font=FONT,
                     font_size=28, color=ACCENT[k % len(ACCENT)])
        for k, i in enumerate(props["items"])
    ]).arrange(RIGHT, buff=0.4)
    body = VGroup(h, chips).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
