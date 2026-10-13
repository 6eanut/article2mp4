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
    from video_agent.config import DESIGN_FRAME_WIDTH
    assert 0 < FRAME_SAFE_WIDTH < DESIGN_FRAME_WIDTH


import pytest
from video_agent.templates import render_scene

FILLER = "超长标题超长标题超长标题超长标题超长标题超长标题"
LONG = "这是一条非常非常长的要点内容用来测试竖屏下会不会被截断掉"

CASES = [
    ("title", {"title": FILLER, "subtitle": FILLER}, 3.0),
    ("section", {"index": 7, "heading": FILLER}, 3.0),
    ("bullets", {"heading": FILLER, "items": [LONG, LONG]}, 4.0),
    ("steps", {"heading": FILLER, "steps": [LONG, LONG, LONG], "done_index": 1}, 4.0),
    ("cycle", {"heading": FILLER, "nodes": [LONG, LONG, LONG]}, 4.0),
    ("tree", {"heading": FILLER, "root": LONG, "children": [[LONG, LONG], [LONG]]}, 4.0),
    ("compare", {"heading": FILLER,
                 "left": {"title": FILLER, "items": [LONG]},
                 "right": {"title": FILLER, "items": [LONG]}}, 4.0),
    ("grid", {"heading": FILLER, "cells": [{"label": LONG, "mark": "tick"},
                                           {"label": LONG, "mark": "cross"}]}, 3.0),
    ("metric", {"heading": FILLER, "value": 1234567, "unit": "%", "label": LONG}, 4.0),
    ("quote", {"text": FILLER + FILLER, "source": FILLER}, 3.0),
    ("summary", {"heading": FILLER, "items": [LONG, LONG, LONG]}, 3.5),
    ("closing", {"text": FILLER, "handle": FILLER}, 3.0),
]


@pytest.mark.parametrize("t,props,dur", CASES)
def test_template_content_fits_frame(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    for a in anims:
        m = getattr(a, "mobject", None)
        if m is not None:
            assert m.width <= FRAME_SAFE_WIDTH + 1e-6, f"{t} overflows: {m.width}"
