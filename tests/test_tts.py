import pytest
from video_agent.tts import render_voiceover
from video_agent.schema import Narration
from video_agent import tts

NARR = Narration(title="T", segments=[{"id": 0, "text": "one"},
                                      {"id": 1, "text": "two"}])

def test_render_voiceover_passes_speed(tmp_path):
    seen = {}
    def fake_synth(text, path, voice, speed=1.0):
        seen["speed"] = speed; open(path, "wb").write(b"\x00")
    durs = render_voiceover(NARR, str(tmp_path), "zf_001",
                            synth=fake_synth, probe=lambda p: 1.0, speed=1.3)
    assert seen["speed"] == 1.3 and durs == [1.0, 1.0]

def test_render_voiceover_returns_durations(tmp_path):
    def fake_synth(text, path, voice, speed=1.0):
        open(path, "wb").write(b"\x00")
    calls = iter([5.0, 1.5])
    def fake_probe(path):
        return next(calls)
    durs = render_voiceover(NARR, str(tmp_path), "zh-CN-XiaoxiaoNeural",
                            synth=fake_synth, probe=fake_probe)
    assert durs == [5.0, 1.5]

def test_render_voiceover_retries_then_raises(tmp_path):
    def boom(text, path, voice, speed=1.0):
        raise RuntimeError("tts down")
    with pytest.raises(RuntimeError):
        render_voiceover(NARR, str(tmp_path), "v", synth=boom, probe=lambda p: 1.0, retries=1)

def test_ffmpeg_path_points_into_env():
    assert "ffmpeg" in tts.ffmpeg_path()