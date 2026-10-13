import pytest
from video_agent.templates import TEMPLATES, render_scene

CASES = [
    ("steps", {"heading": "流程", "steps": ["甲", "乙", "丙"], "done_index": 1}, 4.0),
    ("cycle", {"heading": "循环", "nodes": ["推理", "行动", "观察"]}, 4.0),
    ("tree", {"heading": "搜索树", "root": "根", "children": [["a", "b"], ["c"]]}, 4.0),
    ("grid", {"heading": "候选", "cells": [{"label": "A", "mark": "cross"},
                                            {"label": "B", "mark": "tick"}]}, 3.0),
    ("metric", {"heading": "提升", "value": 42, "unit": "%", "label": "准确率"}, 4.0),
]

def test_all_12_registered():
    assert len(TEMPLATES) == 12

@pytest.mark.parametrize("t,props,dur", CASES)
def test_shapes_fill_duration(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    assert abs(sum(a.run_time for a in anims) - dur) < 1e-6