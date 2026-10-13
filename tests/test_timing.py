import pytest

from video_agent.timing import (
    GAP,
    align_durations,
    estimate_duration,
    fit_complete_indices,
    fit_total,
)


def test_default_gap_keeps_short_form_cuts_tight():
    assert 0.08 <= GAP <= 0.20
    assert align_durations([2.0, 3.0]) == pytest.approx([2.0 + GAP, 3.0 + GAP])


def test_fit_total_counts_inter_shot_pauses():
    assert fit_total([2.0, 2.0, 2.0], limit=4.2, gap=0.15) == 1
    assert fit_total([2.0, 2.0, 2.0], limit=4.3, gap=0.15) == 2


def test_fit_complete_indices_preserves_ending():
    assert fit_complete_indices([2.0, 2.0, 2.0, 2.0], 6.4, gap=0.12) == [0, 1, 3]
    assert fit_complete_indices([2.0, 2.0], 3.0, gap=0.12) == [0, 1]

def test_align_adds_gap():
    assert align_durations([5.2, 1.6, 4.0], gap=0.4) == pytest.approx([5.6, 2.0, 4.4])

def test_estimate_uses_char_count():
    assert estimate_duration("你好世界", chars_per_sec=2.0) == pytest.approx(2.0)

def test_estimate_min_floor():
    assert estimate_duration("", chars_per_sec=5.0) >= 0.5

def test_fit_total_keeps_whole_shots_under_limit():
    from video_agent.timing import fit_total
    assert fit_total([2.0, 2.0, 2.0], 5.0) == 2   # 3rd would exceed
    assert fit_total([2.0, 2.0], None) == 2
    assert fit_total([10.0, 2.0], 5.0) == 1        # at least one
