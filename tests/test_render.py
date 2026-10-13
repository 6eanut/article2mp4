from video_agent.render import build_scene_sequence

SCENES = [
    {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}},
    {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "q"}},
]

def test_build_sequence_length_matches():
    seq = build_scene_sequence(SCENES, [2.0, 3.0], None)
    assert len(seq) == 2
    assert seq[0][0] == "title" and seq[1][0] == "quote"

def test_build_sequence_durations_sum():
    seq = build_scene_sequence(SCENES, [2.0, 3.0], None)
    total = sum(a.run_time for _, anims in seq for a in anims)
    assert abs(total - 5.0) < 1e-6