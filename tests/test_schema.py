import pytest
from video_agent.schema import Narration, validate_scene_spec, ContractError

NARR = Narration(title="T", segments=[
    {"id": 0, "text": "第一句"}, {"id": 1, "text": "第二句"},
])

def _spec(scenes):
    return {"title": "T", "aspects": ["916", "169"], "scenes": scenes}

def test_valid_spec_passes():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T", "subtitle": "s"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "金句"}},
    ])
    spec = validate_scene_spec(raw, NARR)
    assert len(spec.scenes) == 2
    assert spec.scenes[1].type == "quote"

def test_unknown_type_rejected():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "pie_chart", "props": {}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="pie_chart"):
        validate_scene_spec(raw, NARR)

def test_count_mismatch_rejected():
    raw = _spec([{"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}}])
    with pytest.raises(ContractError, match="数量"):
        validate_scene_spec(raw, NARR)

def test_narration_id_mismatch_rejected():
    raw = _spec([
        {"id": 0, "narration_id": 1, "type": "title", "props": {"title": "T"}},
        {"id": 1, "narration_id": 0, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="narration_id"):
        validate_scene_spec(raw, NARR)

def test_missing_required_prop_rejected():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "title", "props": {"subtitle": "缺title"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="title"):
        validate_scene_spec(raw, NARR)