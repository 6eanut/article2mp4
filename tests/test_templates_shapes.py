import pytest
from video_agent.templates import TEMPLATES, render_scene

CASES = [
    ("steps", {"heading": "Flow", "steps": ["one", "two", "three"], "done_index": 1}, 4.0),
    ("cycle", {"heading": "Loop", "nodes": ["Reason", "Act", "Observe"]}, 4.0),
    ("tree", {"heading": "Search tree", "root": "root", "children": [["a", "b"], ["c"]]}, 4.0),
    ("grid", {"heading": "Candidates", "cells": [{"label": "A", "mark": "cross"},
                                            {"label": "B", "mark": "tick"}]}, 3.0),
    ("metric", {"heading": "Improvement", "value": 42, "unit": "%", "label": "Accuracy"}, 4.0),
]

def test_all_12_registered():
    assert len(TEMPLATES) == 12

@pytest.mark.parametrize("t,props,dur", CASES)
def test_shapes_fill_duration(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    assert abs(sum(a.run_time for a in anims) - dur) < 1e-6