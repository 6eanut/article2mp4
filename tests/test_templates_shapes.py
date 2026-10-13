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


def test_steps_keep_labels_under_their_dots():
    body = render_scene("steps", CASES[0][1], duration=4.0)[0].mobject
    _, track = body.submobjects
    line, dots, labels, _ = track.submobjects
    assert abs(line.get_center()[1] - dots.get_center()[1]) < 0.1
    for dot, label in zip(dots, labels):
        assert abs(dot.get_center()[0] - label.get_center()[0]) < 0.1
        assert label.get_top()[1] < dot.get_bottom()[1]


def test_cycle_arrows_stay_outside_node_labels():
    props = {"heading": "版本管理", "nodes": ["提交", "对比", "迭代"]}
    body = render_scene("cycle", props, duration=3.0)[0].mobject
    ring = body[1]
    arrows, nodes = ring[0], ring[1]
    for arrow in arrows:
        for node in nodes:
            points = arrow.get_all_points()
            inside = ((points[:, 0] > node.get_left()[0] - 0.08)
                      & (points[:, 0] < node.get_right()[0] + 0.08)
                      & (points[:, 1] > node.get_bottom()[1] - 0.08)
                      & (points[:, 1] < node.get_top()[1] + 0.08))
            assert not inside.any()
