from __future__ import annotations
from pydantic import ValidationError
from .llm import LLMClient, LLMError
from .schema import Narration, SceneSpec, validate_scene_spec, ContractError
from .config import TEMPLATE_TYPES
from .schema import PROPS_REQUIRED
from .script_gen import load_prompt


def _scene_ok(sc) -> bool:
    if sc.type not in TEMPLATE_TYPES:
        return False
    return all(f in sc.props for f in PROPS_REQUIRED[sc.type])


def _salvage(bad: SceneSpec, narration: Narration) -> SceneSpec:
    """Per-shot validation: keep good shots from the LLM output and degrade
    only the bad ones (instead of discarding the whole storyboard)."""
    scenes = []
    n = len(narration.segments)
    for i, sc in enumerate(bad.scenes):
        if i < n and _scene_ok(sc):
            scenes.append({"id": i, "narration_id": i, "type": sc.type, "props": sc.props})
            continue
        seg = narration.segments[i]
        if i == 0:
            scenes.append({"id": i, "narration_id": i, "type": "title",
                           "props": {"title": narration.title}})
        elif i == n - 1:
            scenes.append({"id": i, "narration_id": i, "type": "closing",
                           "props": {"text": seg.text}})
        else:
            scenes.append({"id": i, "narration_id": i, "type": "bullets",
                           "props": {"heading": seg.text[:20], "items": [seg.text]}})
    return bad.model_copy(update={"scenes": scenes})


def fallback_spec(narration: Narration) -> SceneSpec:
    scenes = []
    n = len(narration.segments)
    for i, seg in enumerate(narration.segments):
        if i == 0:
            t, props = "title", {"title": narration.title}
        elif i == n - 1:
            t, props = "closing", {"text": seg.text}
        else:
            t, props = "bullets", {"heading": seg.text[:20], "items": [seg.text]}
        scenes.append({"id": i, "narration_id": i, "type": t, "props": props})
    return SceneSpec(title=narration.title, aspects=["916", "169"], scenes=scenes)


def generate_scene_spec(narration: Narration, client: LLMClient) -> SceneSpec:
    messages = [
        {"role": "system", "content": load_prompt("scene")},
        {"role": "user", "content": narration.model_dump_json()},
    ]
    try:
        raw = client.chat_json(messages, retries=2)
        return validate_scene_spec(raw, narration)
    except (LLMError, ContractError, ValidationError) as e:
        messages = messages + [{"role": "user",
                                "content": f"Your previous output was invalid: {str(e).splitlines()[0][:200]}. Please fix it and output JSON only."}]
        try:
            raw = client.chat_json(messages, retries=1)
            try:
                return validate_scene_spec(raw, narration)
            except ContractError:
                if len(raw.get("scenes", [])) == len(narration.segments):
                    try:
                        spec = SceneSpec(**raw)
                    except ValidationError:
                        return fallback_spec(narration)
                    return _salvage(spec, narration)
                return fallback_spec(narration)
        except (LLMError, ContractError, ValidationError):
            return fallback_spec(narration)
