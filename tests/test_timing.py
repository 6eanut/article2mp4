import pytest
from video_agent.timing import align_durations, estimate_duration

def test_align_adds_gap():
    assert align_durations([5.2, 1.6, 4.0], gap=0.4) == pytest.approx([5.6, 2.0, 4.4])

def test_estimate_uses_char_count():
    assert estimate_duration("你好世界", chars_per_sec=2.0) == pytest.approx(2.0)

def test_estimate_min_floor():
    assert estimate_duration("", chars_per_sec=5.0) >= 0.5