from manim import DOWN, LEFT, RIGHT, FadeIn, VGroup

from ..style import ACCENT, FG, FONT
from . import entrance_hold
from ._fit import FRAME_SAFE_WIDTH, fit_group, wrapped_text


def _col(side, color):
    # Two columns sit side by side, so each column may use only about half the
    # safe width.
    col_max = FRAME_SAFE_WIDTH / 2 - 0.3
    t = wrapped_text(side["title"], max_width=col_max, font=FONT,
                     font_size=34, weight="BOLD", color=color)
    items = VGroup(*[wrapped_text(f"· {i}", max_width=col_max,
                                  font=FONT, font_size=26, color=FG)
                     for i in side["items"]]
                   ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
    return VGroup(t, items).arrange(DOWN, buff=0.3)


def render(props, duration, subtitle=None):
    h = wrapped_text(props["heading"], max_width=11.8, font=FONT,
                     font_size=38, weight="BOLD", color=FG)
    left = _col(props["left"], ACCENT[0])
    right = _col(props["right"], ACCENT[3])
    cols = VGroup(left, right).arrange(RIGHT, buff=1.2)
    body = VGroup(h, cols).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
