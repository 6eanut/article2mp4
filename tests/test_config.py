import pytest

from video_agent.config import CANVAS, TEMPLATE_TYPES, Settings, load_settings


def test_from_env_reads_three_keys():
    s = Settings.from_env({
        "LLM_BASE_URL": "https://api.deepseek.com/v1",
        "LLM_API_KEY": "sk-abc",
        "LLM_MODEL": "deepseek-chat",
    })
    assert s.base_url == "https://api.deepseek.com/v1"
    assert s.api_key == "sk-abc"
    assert s.model == "deepseek-chat"

def test_from_env_missing_key_raises():
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        Settings.from_env({"LLM_BASE_URL": "x", "LLM_MODEL": "y"})

def test_load_settings_reads_dotenv(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("LLM_BASE_URL=u\nLLM_API_KEY=k\nLLM_MODEL=m\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = load_settings()
    assert (s.base_url, s.api_key, s.model) == ("u", "k", "m")

def test_canvas_and_types():
    assert CANVAS["916"] == (1080, 1920)
    assert CANVAS["169"] == (1920, 1080)
    assert len(TEMPLATE_TYPES) == 12
    assert "bullets" in TEMPLATE_TYPES
