import pytest
from video_agent.templates import render_scene

CASES = [
    ("section", {"index": 2, "heading": "第二幕"}, 2.5),
    ("quote", {"text": "先有内容，再选模板。", "source": "设计原则"}, 3.0),
    ("compare", {"heading": "A vs B", "left": {"title": "选择", "items": ["x"]},
                 "right": {"title": "融合", "items": ["y"]}}, 4.0),
    ("summary", {"heading": "回顾", "items": ["一", "二", "三"]}, 3.5),
]

@pytest.mark.parametrize("t,props,dur", CASES)
def test_text_templates_fill_duration(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    assert abs(sum(a.run_time for a in anims) - dur) < 1e-6