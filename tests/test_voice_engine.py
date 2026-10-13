import os

import pytest

from video_agent import voice_engine


class _FakeResp:
    """Minimal file-like stand-in for `urllib.request.urlopen`'s response."""

    def __init__(self, data, content_length=None):
        self._data = data
        self.headers = ({"Content-Length": str(content_length)}
                        if content_length is not None else {})

    def read(self, *args, **kwargs):
        return self._data

@pytest.mark.skipif(not os.environ.get("KOKORO_SMOKE"),
                    reason="set KOKORO_SMOKE=1 to download models and run real synthesis")
def test_real_zh_synthesis(tmp_path):
    import soundfile as sf
    out = str(tmp_path / "t.wav")
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
        sess = FakeSess()
        tokenizer = FakeTok()
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

def test_synthesize_writes_readable_pcm_wav(monkeypatch, tmp_path):
    import numpy as np
    import soundfile as sf
    class FakeSess:
        def run(self, _, inp):
            return [np.sin(np.linspace(0, 500, 4800)).astype(np.float32)]
    class FakeTok:
        def tokenize(self, ph): return [1, 2, 3]
    class FakeK:
        sess = FakeSess()
        tokenizer = FakeTok()
        def get_voice_style(self, v): return np.zeros((99, 256), np.float32)
    class FakeG2P:
        def __call__(self, t): return "ph"
    monkeypatch.setattr(voice_engine, "_ENGINE", None)
    monkeypatch.setattr(voice_engine, "_load", lambda: (FakeK(), FakeG2P()))
    out = str(tmp_path / "000.wav")
    voice_engine.synthesize("你好", out, "zf_001")
    data, sr = sf.read(out)
    assert sr == 24000 and len(data) == 4800
    assert open(out, "rb").read(4) == b"RIFF"

def test_synthesize_rejects_misleading_mp3_extension(tmp_path):
    with pytest.raises(ValueError, match=".wav"):
        voice_engine.synthesize("你好", str(tmp_path / "000.mp3"), "zf_001")


@pytest.mark.parametrize("text", [
    "15台电视盒子，跑起大模型。",
    "26B模型居然能跑在电视盒子上。",
    "0.39 token/s：AI蠕虫能自己复制。",
    " 15台电视盒子，跑起大模型。",
    "“15台电视盒子，跑起大模型。”",
    "GLM-5.2在5次测试中传遍8个节点。",
])
def test_synthesize_chinese_narration_starting_with_number(monkeypatch, tmp_path, text):
    """Misaki converts initial digits to Hanzi before segmenting, so the input
    must be normalized before its initial-script detection runs."""
    import numpy as np
    from misaki.zh import ZHG2P

    class FakeSess:
        def run(self, _, inp):
            return [np.zeros(2400, np.float32)]

    class FakeTok:
        def tokenize(self, phonemes):
            assert phonemes
            return [1, 2, 3]

    class FakeK:
        sess = FakeSess()
        tokenizer = FakeTok()

        def get_voice_style(self, voice):
            return np.zeros((99, 256), np.float32)

    monkeypatch.setattr(voice_engine, "_ENGINE", (FakeK(), ZHG2P()))
    out = tmp_path / "numbered.wav"
    assert voice_engine.synthesize(text, str(out), "zf_001") == str(out)
    assert out.stat().st_size > 44


def test_phonemize_preserves_version_numbers_without_negative_reading():
    assert voice_engine._phonemize(lambda text: text,
                                    "GLM-5.2和Qwen3.5-9B模型") == (
        "GLM 五点二和Qwen三点五 九B模型")


def test_phonemize_preserves_single_letter_negative_numbers():
    assert voice_engine._phonemize(lambda text: text, "x-5") == "x负五"


def test_phonemize_leaves_non_numeric_text_unchanged():
    assert voice_engine._phonemize(lambda text: text,
                                    "AI能自己找设备。") == "AI能自己找设备。"

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
        sess = FakeSess()
        tokenizer = FakeTok()
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
    def fake_urlopen(url):
        got.append(url)
        return _FakeResp(b"x" * 10, content_length=10)
    monkeypatch.setattr(voice_engine.urllib.request, "urlopen", fake_urlopen)
    voice_engine.ensure_models()
    assert len(got) == 2
    assert all(u.startswith(voice_engine.PROXIES[0]) for u in got)
    got.clear()
    voice_engine.ensure_models()          # files exist → no downloads
    assert got == []

def test_partial_download_leaves_no_final_file(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
    attempts = []
    def drop_urlopen(url):
        attempts.append(url)
        raise OSError("connection dropped")
    monkeypatch.setattr(voice_engine.urllib.request, "urlopen", drop_urlopen)
    with pytest.raises(RuntimeError):
        voice_engine._download("kokoro-v1.1-zh.int8.onnx")
    # final model path must be untouched (no partial cached as valid model)
    assert not os.path.exists(voice_engine.model_path("kokoro-v1.1-zh.int8.onnx"))
    # attempted every proxy, and any leftover temp cleaned up
    assert attempts == [p + voice_engine.MODEL_FILES["kokoro-v1.1-zh.int8.onnx"]
                        for p in voice_engine.PROXIES]
    assert not os.path.exists(voice_engine.model_path("kokoro-v1.1-zh.int8.onnx") + ".part")

def test_truncated_download_falls_through_to_next_proxy(monkeypatch, tmp_path):
    """A proxy returning fewer bytes than Content-Length must be rejected and the
    file tried on the next proxy, never cached under the real dst."""
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
    dst = voice_engine.model_path("kokoro-v1.1-zh.int8.onnx")
    calls = []

    def fake_urlopen(url):
        calls.append(url)
        if url.startswith(voice_engine.PROXIES[0]):
            return _FakeResp(b"truncated", content_length=100)  # 9 != 100
        return _FakeResp(b"x" * 100, content_length=100)

    monkeypatch.setattr(voice_engine.urllib.request, "urlopen", fake_urlopen)
    got = voice_engine._download("kokoro-v1.1-zh.int8.onnx")
    assert got == dst
    assert os.path.getsize(dst) == 100        # full file finally cached
    assert os.path.exists(dst)                 # via a non-first proxy
    assert calls[0].startswith(voice_engine.PROXIES[0])
    assert calls[1].startswith(voice_engine.PROXIES[1])
    assert not os.path.exists(dst + ".part")   # temp always cleaned up

def test_all_proxies_truncate_raises_and_leaves_no_final(monkeypatch, tmp_path):
    """When every proxy truncates (size != Content-Length), _download raises and
    leaves no final file and no leftover temp."""
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
    dst = voice_engine.model_path("kokoro-v1.1-zh.int8.onnx")
    calls = []

    def truncate_urlopen(url):
        calls.append(url)
        return _FakeResp(b"partial", content_length=100)

    monkeypatch.setattr(voice_engine.urllib.request, "urlopen", truncate_urlopen)
    with pytest.raises(RuntimeError):
        voice_engine._download("kokoro-v1.1-zh.int8.onnx")
    assert len(calls) == len(voice_engine.PROXIES)  # every proxy attempted
    assert not os.path.exists(dst)                  # no partial cached as valid
    assert not os.path.exists(dst + ".part")

def test_enumeration_comma_never_splits_chunk():
    """`、` is an enumeration comma: it must not create a chunk boundary even
    when the text is long, so a listed phrase is spoken as one clause group."""
    # count_tokens = len → max_tokens counts characters (5 chars per item).
    text = "苹果、香蕉、西瓜、菠萝。"          # 12 chars
    chunks = voice_engine._chunk(text, len, max_tokens=11)  # must split somewhere
    assert len(chunks) > 1
    # The only legal break is at the hard end `。`; `、` must not start a chunk.
    for c in chunks:
        assert not c.startswith("、")
    assert "".join(chunks) == text


def test_split_sentences_only_hard_ends_single_turn():
    """A sentence with soft punctuation stays in ONE turn until a real end."""
    turns = voice_engine._split_sentences("先做甲；再做乙、丙和丁。然后结束。")
    assert turns == ["先做甲；再做乙、丙和丁。", "然后结束。"]


def test_chunk_splits_at_boundary_never_mid_list():
    text = "甲甲甲；乙乙乙。丙丙丙。"
    chunks = voice_engine._chunk(text, len, max_tokens=8)
    assert "".join(chunks) == text
    assert all(len(c) <= 8 for c in chunks)


def test_chunk_respects_sentence_end_before_list_comma():
    """Hard sentence ends are the packing boundary: a list joined by `、` must not
    let a chunk run past a `。` end when each sentence fits the budget. This fails
    on the old behaviour, which split at `、` and packed across the sentence end."""
    text = "甲、乙、丙。丁、戊、己。"   # two 6-char sentences, 12 chars total
    chunks = voice_engine._chunk(text, len, max_tokens=8)
    assert chunks == ["甲、乙、丙。", "丁、戊、己。"]
