import os

import pytest

from video_agent.compose import assert_av_sync, build_concat_file


def test_build_concat_file_lists_in_order(tmp_path):
    (tmp_path / "000.wav").write_bytes(b"x")
    (tmp_path / "001.wav").write_bytes(b"x")
    text = build_concat_file([0, 1], str(tmp_path))
    assert text.index("000.wav") < text.index("001.wav")
    assert text.count("file ") == 2

def test_build_concat_file_escapes_apostrophes(tmp_path):
    audio_dir = tmp_path / "teacher's"
    audio_dir.mkdir()
    line = build_concat_file([0], str(audio_dir)).strip()
    assert "teacher'\\''s/000.wav'" in line

def test_assert_av_sync_ok():
    assert_av_sync(10.0, 10.2, tol=0.3)  # does not raise

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

def test_trim_audio_in_place_uses_temp_file(monkeypatch, tmp_path):
    import video_agent.compose as c
    src = tmp_path / "voice.wav"
    src.write_bytes(b"original")
    seen = {}
    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        (tmp_path / os.path.basename(argv[-1])).write_bytes(b"trimmed")
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", fake_run)
    assert c.trim_audio(str(src), 1.0) == str(src)
    assert seen["argv"][-1] != str(src)
    assert src.read_bytes() == b"trimmed"

def test_concat_voiceover_applies_loudnorm(monkeypatch, tmp_path):
    import video_agent.compose as c
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    (tmp_path / "000.mp3").write_bytes(b"x")
    c.concat_voiceover(str(tmp_path), [0], "out.mp3", gap=0.4)
    joined = " ".join(seen["argv"])
    assert "loudnorm" in joined and "I=-14" in joined

def test_concat_voiceover_can_skip_loudnorm(monkeypatch, tmp_path):
    import video_agent.compose as c
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    (tmp_path / "000.mp3").write_bytes(b"x")
    c.concat_voiceover(str(tmp_path), [0], "out.mp3", gap=0.4, loudnorm=False)
    assert "loudnorm" not in " ".join(seen["argv"])

def test_concat_voiceover_cleans_speech_and_writes_pcm_wav(monkeypatch, tmp_path):
    import video_agent.compose as c
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    c.concat_voiceover(str(tmp_path), [0, 1], "voice.wav", gap=0.2)
    args = seen["argv"]
    assert args.count("-i") == 2
    assert str(tmp_path / "000.wav") in args
    assert "highpass" in args[args.index("-filter_complex") + 1]
    assert "acompressor" in args[args.index("-filter_complex") + 1]
    assert args[args.index("-c:a") + 1] == "pcm_s16le"
    assert args[args.index("-ar") + 1] == "24000"

def test_mux_ducks_music_while_voice_is_present_and_encodes_aac(monkeypatch, tmp_path):
    import video_agent.compose as c
    bgm = tmp_path / "track.mp3"
    bgm.write_bytes(b"x")
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    c.mux("video.mp4", "voice.wav", str(bgm), "output.mp4")
    args = seen["argv"]
    graph = args[args.index("-filter_complex") + 1]
    assert "sidechaincompress" in graph
    assert "alimiter" in graph
    assert "amix=inputs=2:duration=first:normalize=0" in graph
    assert args[args.index("-c:a") + 1] == "aac"
    assert args[args.index("-b:a") + 1] == "192k"

def test_mux_without_music_encodes_aac(monkeypatch):
    import video_agent.compose as c
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    c.mux("video.mp4", "voice.wav", None, "output.mp4")
    assert seen["argv"][seen["argv"].index("-c:a") + 1] == "aac"
