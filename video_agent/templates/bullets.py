from manim import DOWN, LEFT, FadeIn, VGroup

from ..style import ACCENT, FG, FONT
from . import entrance_hold
from ._fit import fit_width, wrapped_text


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=FG)
    items = VGroup(*[
        wrapped_text(f"· {it}", max_width=11.3, font=FONT,
                     font_size=30, color=ACCENT[i % len(ACCENT)])
        for i, it in enumerate(props["items"])
    ]).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    body = VGroup(fit_width(h), items).arrange(DOWN, buff=0.5)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)
