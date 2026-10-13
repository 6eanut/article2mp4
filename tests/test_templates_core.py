import pytest

from video_agent.templates import TEMPLATES, entrance_hold, render_scene


def test_entrance_hold_fills_duration():
    anims = entrance_hold(None, duration=3.0, min_entrance=0.8)
    total = sum(a.run_time for a in anims)
    assert abs(total - 3.0) < 1e-6


def test_default_entrance_is_brief():
    from manim import FadeIn, Text
    anims = entrance_hold(FadeIn(Text("快速进入")), duration=2.0)
    assert 0.3 <= anims[0].run_time <= 0.45


def test_core_three_registered():
    for t in ("title", "bullets", "closing"):
        assert t in TEMPLATES


def test_render_title_returns_anims():
    anims = render_scene("title", {"title": "Title", "subtitle": "Subtitle"}, duration=2.5)
    assert len(anims) >= 1
    assert abs(sum(a.run_time for a in anims) - 2.5) < 1e-6


def test_render_bullets_returns_anims():
    anims = render_scene("bullets", {"heading": "Points", "items": ["a", "b", "c"]}, duration=4.0)
    assert abs(sum(a.run_time for a in anims) - 4.0) < 1e-6


def test_render_unknown_type_raises():
    with pytest.raises(KeyError):
        render_scene("nope", {}, duration=1.0)
