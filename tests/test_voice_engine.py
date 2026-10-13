import os
import pytest
from video_agent import voice_engine

def test_synthesize_defaults_and_signature():
    import inspect
    sig = inspect.signature(voice_engine.synthesize)
    assert list(sig.parameters) == ["text", "out_path", "voice", "speed"]
    assert sig.parameters["speed"].default == 1.0

def test_cache_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path / "m"))
    assert voice_engine.cache_dir() == str(tmp_path / "m")

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