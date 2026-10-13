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

def test_build_sequence_length_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        build_scene_sequence(SCENES, [2.0], None)  # 2 scenes, 1 duration

def test_degrade_shot_on_render_error(monkeypatch, caplog):
    import video_agent.render as r
    def boom(*a, **k):
        raise RuntimeError("template boom")
    monkeypatch.setattr(r, "render_scene", boom)
    with caplog.at_level("WARNING"):
        seq = r.build_scene_sequence(SCENES, [2.0, 3.0], None)
    assert len(seq) == 2
    assert abs(sum(a.run_time for _, anims in seq for a in anims) - 5.0) < 1e-6
    # Degradation must not swallow errors silently: every degrade leaves a log line
    assert caplog.text.count("degrading to a text-only shot") == 2

def test_build_subtitle_map_from_narration_sentences():
    from video_agent.render import build_subtitle_map
    spec = {"scenes": [{"id": 0}, {"id": 1}]}
    assert build_subtitle_map(spec, ["alpha", "beta"]) == {0: "alpha", 1: "beta"}
    assert build_subtitle_map(spec, None) == {}

def test_frame_dimensions_match_canvas_aspect():
    # The logical frame must match the pixel canvas ratio, or the 9:16 version
    # gets squeezed into a 16:9 letterbox with subtitles falling off-screen
    from video_agent.render import frame_dimensions
    for aspect, (w, h) in (("916", (1080, 1920)), ("169", (1920, 1080))):
        fw, fh = frame_dimensions(aspect)
        assert abs(fw / fh - w / h) < 1e-9