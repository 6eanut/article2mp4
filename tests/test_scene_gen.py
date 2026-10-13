from video_agent.config import Settings
from video_agent.llm import LLMClient
from video_agent.scene_gen import _salvage, fallback_spec, generate_scene_spec
from video_agent.schema import Narration, SceneSpec

S = Settings("u", "k", "m")
NARR = Narration(title="T", segments=[{"id": 0, "text": "one"},
                                      {"id": 1, "text": "two"},
                                      {"id": 2, "text": "three"}])

def test_fallback_has_three_types_and_1to1():
    spec = fallback_spec(NARR)
    assert spec.scenes[0].type == "title"
    assert spec.scenes[-1].type == "closing"
    assert [s.narration_id for s in spec.scenes] == [0, 1, 2]

def test_generate_ok():
    good = ('{"title":"T","aspects":["916","169"],"scenes":['
            '{"id":0,"narration_id":0,"type":"title","props":{"title":"T"}},'
            '{"id":1,"narration_id":1,"type":"quote","props":{"text":"q"}},'
            '{"id":2,"narration_id":2,"type":"closing","props":{"text":"done"}}]}')
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: good))
    assert len(spec.scenes) == 3

def test_generate_bad_then_fallback():
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: "nonsense"))
    assert spec.scenes[0].type == "title"  # fallback

def test_generate_wrong_shape_then_fallback():
    # Valid JSON but wrong shape (missing scenes): retry, then fall back.
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: '{"foo":"bar"}'))
    assert spec.scenes[0].type == "title"
    assert [s.narration_id for s in spec.scenes] == [0, 1, 2]

def test_salvage_keeps_good_and_degrades_bad():
    bad = SceneSpec(title="T", aspects=["916", "169"], scenes=[
        {"id": 0, "narration_id": 0, "type": "quote", "props": {"text": "q"}},
        {"id": 1, "narration_id": 1, "type": "nonexistent", "props": {}},
        {"id": 2, "narration_id": 2, "type": "closing", "props": {"text": "done"}},
    ])
    out = _salvage(bad, NARR)
    assert out.scenes[0]["type"] == "quote"         # good shot kept
    assert out.scenes[2]["type"] == "closing"       # good shot kept
    assert out.scenes[1]["type"] == "bullets"       # bad shot degraded
    assert [s["narration_id"] for s in out.scenes] == [0, 1, 2]
