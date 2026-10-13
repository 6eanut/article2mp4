import pytest
from video_agent.llm import LLMClient, strip_fence, LLMError
from video_agent.config import Settings

S = Settings("u", "k", "m")

def test_strip_fence_plain():
    assert strip_fence('{"a":1}') == '{"a":1}'

def test_strip_fence_json_block():
    assert strip_fence('```json\n{"a":1}\n```') == '{"a":1}'
    assert strip_fence('```\n{"a":1}\n```') == '{"a":1}'

def test_chat_json_parses():
    c = LLMClient(S, transport=lambda msgs: '{"ok": true}')
    assert c.chat_json([{"role": "user", "content": "hi"}]) == {"ok": True}

def test_chat_json_retries_then_raises():
    calls = {"n": 0}
    def bad(msgs):
        calls["n"] += 1
        return "not json"
    c = LLMClient(S, transport=bad)
    with pytest.raises(LLMError):
        c.chat_json([{"role": "user", "content": "hi"}], retries=1)
    assert calls["n"] == 2  # 首次 + 1 次重试

def test_chat_json_rejects_non_object():
    c = LLMClient(S, transport=lambda m: "42")
    with pytest.raises(LLMError):
        c.chat_json([{"role": "user", "content": "hi"}], retries=1)