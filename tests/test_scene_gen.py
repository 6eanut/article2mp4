from video_agent.scene_gen import generate_scene_spec, fallback_spec
from video_agent.schema import Narration
from video_agent.llm import LLMClient
from video_agent.config import Settings

S = Settings("u", "k", "m")
NARR = Narration(title="T", segments=[{"id": 0, "text": "一"},
                                      {"id": 1, "text": "二"},
                                      {"id": 2, "text": "三"}])

def test_fallback_has_three_types_and_1to1():
    spec = fallback_spec(NARR)
    assert spec.scenes[0].type == "title"
    assert spec.scenes[-1].type == "closing"
    assert [s.narration_id for s in spec.scenes] == [0, 1, 2]

def test_generate_ok():
    good = ('{"title":"T","aspects":["916","169"],"scenes":['
            '{"id":0,"narration_id":0,"type":"title","props":{"title":"T"}},'
            '{"id":1,"narration_id":1,"type":"quote","props":{"text":"q"}},'
            '{"id":2,"narration_id":2,"type":"closing","props":{"text":"完"}}]}')
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: good))
    assert len(spec.scenes) == 3

def test_generate_bad_then_fallback():
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: "nonsense"))
    assert spec.scenes[0].type == "title"  # 兜底