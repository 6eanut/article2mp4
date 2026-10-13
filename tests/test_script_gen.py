import pytest
from video_agent.script_gen import generate_narration, load_prompt
from video_agent.llm import LLMClient, LLMError
from video_agent.config import Settings

S = Settings("u", "k", "m")
GOOD = '{"title":"T","segments":[{"id":0,"text":"one"},{"id":1,"text":"two"}]}'

def test_load_prompt_nonempty():
    assert len(load_prompt("script")) > 20

def test_generate_narration_parses():
    c = LLMClient(S, transport=lambda m: GOOD)
    n = generate_narration("# article body", c)
    assert n.title == "T" and len(n.segments) == 2

def test_generate_narration_retries_then_raises():
    c = LLMClient(S, transport=lambda m: "junk")
    with pytest.raises(LLMError):
        generate_narration("# x", c)