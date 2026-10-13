from video_agent.scene_gen import generate_scene_spec, fallback_spec, _salvage
from video_agent.schema import Narration, SceneSpec
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

def test_generate_wrong_shape_then_fallback():
    # 合法 JSON 但结构错误（缺 scenes）：应走 retry→fallback，而不是抛 ValidationError
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: '{"foo":"bar"}'))
    assert spec.scenes[0].type == "title"
    assert [s.narration_id for s in spec.scenes] == [0, 1, 2]

def test_salvage_keeps_good_and_degrades_bad():
    bad = SceneSpec(title="T", aspects=["916", "169"], scenes=[
        {"id": 0, "narration_id": 0, "type": "quote", "props": {"text": "q"}},
        {"id": 1, "narration_id": 1, "type": "nonexistent", "props": {}},
        {"id": 2, "narration_id": 2, "type": "closing", "props": {"text": "完"}},
    ])
    out = _salvage(bad, NARR)
    assert out.scenes[0]["type"] == "quote"         # 好镜头保留
    assert out.scenes[2]["type"] == "closing"       # 好镜头保留
    assert out.scenes[1]["type"] == "bullets"       # 坏镜头降级
    assert [s["narration_id"] for s in out.scenes] == [0, 1, 2]
