import pytest
from video_agent.compose import build_concat_file, assert_av_sync

def test_build_concat_file_lists_in_order(tmp_path):
    (tmp_path / "000.mp3").write_bytes(b"x")
    (tmp_path / "001.mp3").write_bytes(b"x")
    text = build_concat_file([0, 1], str(tmp_path))
    assert text.index("000.mp3") < text.index("001.mp3")
    assert text.count("file ") == 2

def test_assert_av_sync_ok():
    assert_av_sync(10.0, 10.2, tol=0.3)  # 不抛

def test_assert_av_sync_raises():
    with pytest.raises(AssertionError):
        assert_av_sync(10.0, 11.0, tol=0.3)

def test_build_concat_filter_inserts_gap():
    from video_agent.compose import build_concat_filter
    f = build_concat_filter(2, 0.4)
    assert f.count("apad=pad_dur=0.4") == 2
    assert f.endswith("concat=n=2:v=0:a=1[out]")

def test_trim_audio_builds_pad_command(tmp_path, monkeypatch):
    import video_agent.compose as c
    called = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run",
                        lambda *a, **k: called.update(argv=a[0]))
    c.trim_audio("in.mp3", 3.0, "out.mp3")
    assert "-t" in called["argv"] and "apad=whole_dur=3.000" in called["argv"]