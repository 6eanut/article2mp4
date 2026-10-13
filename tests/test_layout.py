import pytest
from manim import DOWN, Text, VGroup

from video_agent.templates import render_scene
from video_agent.templates._fit import FRAME_SAFE_WIDTH, fit_group, fit_width, wrapped_text


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


def test_wrapped_cjk_preserves_readable_size_and_all_characters():
    source = "这是一条非常非常长的要点内容用来测试竖屏下的文字换行与阅读体验"
    text = wrapped_text(source, max_width=5.0, font_size=30)
    assert text.width <= 5.0 + 1e-6
    assert "\n" in text.original_text
    assert text.original_text.replace("\n", "") == source
    assert text.height > Text("短句", font_size=30).height * 1.5


def test_wrapped_english_uses_word_boundaries():
    source = "Good typography makes short videos easier to follow"
    text = wrapped_text(source, max_width=4.2, font_size=30)
    assert text.width <= 4.2 + 1e-6
    assert text.original_text.replace("\n", " ") == source


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


def _text_descendants(mobject):
    if isinstance(mobject, Text):
        return [mobject]
    return [text for child in mobject.submobjects
            for text in _text_descendants(child)]


@pytest.mark.parametrize("t,props,dur", CASES)
def test_long_template_text_boxes_do_not_overlap(t, props, dur):
    body = render_scene(t, props, duration=dur)[0].mobject
    texts = _text_descendants(body)
    for i, first in enumerate(texts):
        for second in texts[i + 1:]:
            overlap_x = min(first.get_right()[0], second.get_right()[0]) - max(
                first.get_left()[0], second.get_left()[0])
            overlap_y = min(first.get_top()[1], second.get_top()[1]) - max(
                first.get_bottom()[1], second.get_bottom()[1])
            assert overlap_x <= 0.08 or overlap_y <= 0.08, f"{t} text boxes overlap"
