import pytest

from video_agent.config import Settings
from video_agent.llm import LLMClient, LLMError
from video_agent.script_gen import generate_narration, load_prompt

S = Settings("u", "k", "m")
GOOD = '{"title":"T","segments":[{"id":0,"text":"one"},{"id":1,"text":"two"}]}'

def test_load_prompt_nonempty():
    assert len(load_prompt("script")) > 20


def test_script_prompt_requests_short_form_structure():
    prompt = load_prompt("script").lower()
    assert "hook" in prompt
    assert "filler" in prompt
    assert "seconds" in prompt
    assert "short" in prompt

def test_generate_narration_parses():
    c = LLMClient(S, transport=lambda m: GOOD)
    n = generate_narration("# article body", c)
    assert n.title == "T" and len(n.segments) == 2

def test_generate_narration_retries_then_raises():
    c = LLMClient(S, transport=lambda m: "junk")
    with pytest.raises(LLMError):
        generate_narration("# x", c)


def test_overlong_narration_gets_one_condensing_pass():
    long = {"title": "T", "segments": [
        {"id": i, "text": "这是一句需要压缩的完整中文描述" * 3} for i in range(10)
    ]}
    short = {"title": "T", "segments": [
        {"id": i, "text": "每个镜头只讲一个要点。"} for i in range(8)
    ]}

    class Client:
        calls = []

        def chat_json(self, messages, retries):
            self.calls.append(messages)
            return long if len(self.calls) == 1 else short

    client = Client()
    result = generate_narration("# 长文章", client)
    assert len(client.calls) == 2
    assert len(result.segments) == 8
    assert "shorter" in client.calls[1][-1]["content"].lower()


def test_failed_condensing_pass_keeps_valid_first_script():
    long = {"title": "T", "segments": [
        {"id": i, "text": "这一句足够长需要保留关键信息" * 3} for i in range(10)
    ]}

    class Client:
        calls = 0

        def chat_json(self, messages, retries):
            self.calls += 1
            return long if self.calls == 1 else {"invalid": "response"}

    client = Client()
    result = generate_narration("# 长文章", client)
    assert len(result.segments) == 10
    assert client.calls == 2


def test_mixed_language_runtime_counts_chinese_and_english():
    from video_agent.schema import Narration
    from video_agent.script_gen import _estimated_seconds
    mixed = Narration(title="T", segments=[{"id": 0, "text": "中文 " + "long phrase " * 100}])
    assert _estimated_seconds(mixed) > 50


def test_explicit_duration_target_reaches_script_prompt():
    class Client:
        messages = None

        def chat_json(self, messages, retries):
            self.messages = messages
            return {"title": "T", "segments": [{"id": 0, "text": "简短但完整。"}]}

    client = Client()
    generate_narration("# article", client, target_seconds=30)
    assert "30 seconds" in str(client.messages)
