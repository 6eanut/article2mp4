from manim import Text, VGroup, DOWN
from video_agent.templates._fit import fit_width, fit_group, FRAME_SAFE_WIDTH


def test_fit_width_shrinks_oversized_text():
    t = Text("x" * 100)
    assert t.width > FRAME_SAFE_WIDTH
    assert fit_width(t) is t                       # chainable, same object
    assert t.width <= FRAME_SAFE_WIDTH + 1e-6


def test_fit_width_leaves_small_text_untouched():
    t = Text("hi")
    before = t.width
    fit_width(t)
    assert abs(t.width - before) < 1e-9


def test_fit_group_shrinks_group_uniformly():
    g = VGroup(Text("x" * 100), Text("x" * 60)).arrange(DOWN)
    assert g.width > FRAME_SAFE_WIDTH
    fit_group(g)
    assert g.width <= FRAME_SAFE_WIDTH + 1e-6
    # uniform scaling preserves the size ratio between the two texts
    assert abs(g[1].width / g[0].width - 60 / 100) < 0.02


def test_frame_safe_width_is_below_design_width():
    from video_agent.render import DESIGN_FRAME_WIDTH
    assert 0 < FRAME_SAFE_WIDTH < DESIGN_FRAME_WIDTH