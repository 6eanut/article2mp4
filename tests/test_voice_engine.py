from video_agent import voice_engine

def test_synthesize_defaults_and_signature():
    import inspect
    sig = inspect.signature(voice_engine.synthesize)
    assert list(sig.parameters) == ["text", "out_path", "voice", "speed"]
    assert sig.parameters["speed"].default == 1.0