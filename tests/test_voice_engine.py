import os
import pytest
from video_agent import voice_engine

@pytest.mark.skipif(not os.environ.get("KOKORO_SMOKE"),
                    reason="set KOKORO_SMOKE=1 to download models and run real synthesis")
def test_real_zh_synthesis(tmp_path):
    import soundfile as sf
    # Match the pipeline: writes to a ".mp3" path (WAV content under the hood).
    out = str(tmp_path / "t.mp3")
    voice_engine.synthesize("大家好，这是一段本地离线语音合成的测试。", out, "zf_001")
    data, sr = sf.read(out)
    assert sr == 24000 and len(data) / sr > 1.0

def test_synthesize_uses_injected_engine(monkeypatch, tmp_path):
    import numpy as np
    class FakeSess:
        def run(self, _, inp):
            return [np.zeros(2400, np.float32)]  # 0.1s @ 24k
    class FakeTok:
        def tokenize(self, ph): return [1, 2, 3]
    class FakeK:
        sess = FakeSess(); tokenizer = FakeTok()
        def get_voice_style(self, v): return np.zeros((99, 256), np.float32)
    class FakeG2P:
        def __call__(self, t): return "ph"
    monkeypatch.setattr(voice_engine, "_ENGINE", None)
    monkeypatch.setattr(voice_engine, "_load", lambda: (FakeK(), FakeG2P()))
    out = str(tmp_path / "a.wav")
    voice_engine.synthesize("你好", out, "zf_001")
    import soundfile as sf
    data, sr = sf.read(out)
    assert sr == 24000 and len(data) == 2400

def test_synthesize_writes_readable_audio_to_mp3_path(monkeypatch, tmp_path):
    """Regression: the pipeline writes to f"{seg.id:03d}.mp3" paths (edge-tts era).
    soundfile must write WAV content there, not infer the MP3 container from the
    extension (which has no PCM_16 subtype)."""
    import numpy as np
    import soundfile as sf
    class FakeSess:
        def run(self, _, inp):
            return [np.sin(np.linspace(0, 500, 4800)).astype(np.float32)]
    class FakeTok:
        def tokenize(self, ph): return [1, 2, 3]
    class FakeK:
        sess = FakeSess(); tokenizer = FakeTok()
        def get_voice_style(self, v): return np.zeros((99, 256), np.float32)
    class FakeG2P:
        def __call__(self, t): return "ph"
    monkeypatch.setattr(voice_engine, "_ENGINE", None)
    monkeypatch.setattr(voice_engine, "_load", lambda: (FakeK(), FakeG2P()))
    out = str(tmp_path / "000.mp3")
    voice_engine.synthesize("你好", out, "zf_001")
    data, sr = sf.read(out)
    assert sr == 24000 and len(data) == 4800
    assert open(out, "rb").read(4) == b"RIFF"  # WAV content despite .mp3 name

def test_synthesize_long_text_concatenates_chunks(monkeypatch, tmp_path):
    import numpy as np
    import soundfile as sf
    monkeypatch.setattr(voice_engine, "_ENGINE", None)  # clear prior cached engine
    chunk_len = 2400  # each chunk produces this many samples (0.1s @ 24k)
    class FakeSess:
        n = 0
        def run(self, _, inp):
            FakeSess.n += 1
            return [np.ones(chunk_len, np.float32)]
    class FakeTok:
        # tokenizer counts by length so max_tokens (500) counts characters.
        def tokenize(self, ph): return list(range(len(ph)))
    class FakeK:
        sess = FakeSess(); tokenizer = FakeTok()
        def get_voice_style(self, v): return np.zeros((500, 256), np.float32)
    class FakeG2P:
        def __call__(self, t): return t
    monkeypatch.setattr(voice_engine, "_load", lambda: (FakeK(), FakeG2P()))

    # Many short sentences → definitely splits into multiple chunks.
    long_text = "句子。" * 300  # one sentence fits a chunk; many pack into several
    out = str(tmp_path / "long.wav")
    voice_engine.synthesize(long_text, out, "zf_001")
    data, sr = sf.read(out)
    assert sr == 24000
    num_chunks = FakeSess.n
    assert num_chunks > 1
    gap = voice_engine._CHUNK_GAP_SAMPLES
    expected = chunk_len * num_chunks + gap * (num_chunks - 1)
    assert len(data) == expected
    import inspect
    sig = inspect.signature(voice_engine.synthesize)
    assert list(sig.parameters) == ["text", "out_path", "voice", "speed"]
    assert sig.parameters["speed"].default == 1.0

def test_cache_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path / "m"))
    assert voice_engine.cache_dir() == str(tmp_path / "m")

def test_chunk_short_text_single_chunk():
    text = "你好呀。"
    assert voice_engine._chunk(text, len) == [text]

def test_chunk_long_text_multiple_chunks_preserves_text():
    # count_tokens = len → max_tokens counts characters.
    max_tokens = 8
    sentences = ["第一句", "第二句", "第三句第四句！", "第五句。"]  # len 22 total
    text = "".join(sentences)
    assert len(text) > max_tokens
    chunks = voice_engine._chunk(text, len, max_tokens)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= max_tokens
    assert "".join(chunks) == text  # punctuation preserved, nothing dropped

def test_chunk_overlong_sentence_hard_split_without_punctuation():
    max_tokens = 10
    text = "这是一个非常长没有标点符号的句子需要被硬分割成多个小片段"
    assert len(text) > max_tokens
    chunks = voice_engine._chunk(text, len, max_tokens)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= max_tokens
    assert "".join(chunks) == text

def test_model_files_cover_both_generators():
    assert set(voice_engine.MODEL_FILES) == {"kokoro-v1.1-zh.int8.onnx", "voices-v1.1-zh.bin"}
    for url in voice_engine.MODEL_FILES.values():
        assert url.startswith("https://")

def test_ensure_models_uses_proxy_and_skips_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
    got = []
    def fake_urlretrieve(url, dst):
        got.append(url); open(dst, "wb").write(b"x" * 10)
    monkeypatch.setattr(voice_engine.urllib.request, "urlretrieve", fake_urlretrieve)
    voice_engine.ensure_models()
    assert len(got) == 2
    assert all(u.startswith(voice_engine.PROXIES[0]) for u in got)
    got.clear()
    voice_engine.ensure_models()          # files exist → no downloads
    assert got == []

def test_partial_download_leaves_no_final_file(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
    attempts = []
    def partial_then_raise(url, dst):
        attempts.append(url)
        open(dst, "wb").write(b"partial")
        raise OSError("connection dropped")
    monkeypatch.setattr(voice_engine.urllib.request, "urlretrieve", partial_then_raise)
    with pytest.raises(RuntimeError):
        voice_engine._download("kokoro-v1.1-zh.int8.onnx")
    # final model path must be untouched (no partial cached as valid model)
    assert not os.path.exists(voice_engine.model_path("kokoro-v1.1-zh.int8.onnx"))
    # attempted every proxy, and any leftover temp cleaned up
    assert attempts == [p + voice_engine.MODEL_FILES["kokoro-v1.1-zh.int8.onnx"]
                        for p in voice_engine.PROXIES]
    assert not os.path.exists(voice_engine.model_path("kokoro-v1.1-zh.int8.onnx") + ".part")