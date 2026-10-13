import pytest

from video_agent.schema import ContractError, Narration, validate_scene_spec

NARR = Narration(title="T", segments=[
    {"id": 0, "text": "first sentence"}, {"id": 1, "text": "second sentence"},
])

def _spec(scenes):
    return {"title": "T", "aspects": ["916", "169"], "scenes": scenes}

def test_valid_spec_passes():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T", "subtitle": "s"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "a memorable line"}},
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
    with pytest.raises(ContractError, match="does not match narration segment count"):
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
        {"id": 0, "narration_id": 0, "type": "title", "props": {"subtitle": "missing title"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="title"):
        validate_scene_spec(raw, NARR)

def test_props_table_covers_all_template_types():
    from video_agent.config import TEMPLATE_TYPES
    from video_agent.schema import PROPS_REQUIRED
    assert set(PROPS_REQUIRED) == set(TEMPLATE_TYPES)
