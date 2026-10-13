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