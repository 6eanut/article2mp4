import pytest

from video_agent.templates import render_scene

CASES = [
    ("section", {"index": 2, "heading": "Act Two"}, 2.5),
    ("quote", {"text": "Content first, template second.", "source": "Design principle"}, 3.0),
    ("compare", {"heading": "A vs B", "left": {"title": "Choice", "items": ["x"]},
                 "right": {"title": "Blend", "items": ["y"]}}, 4.0),
    ("summary", {"heading": "Recap", "items": ["one", "two", "three"]}, 3.5),
]

@pytest.mark.parametrize("t,props,dur", CASES)
def test_text_templates_fill_duration(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    assert abs(sum(a.run_time for a in anims) - dur) < 1e-6
