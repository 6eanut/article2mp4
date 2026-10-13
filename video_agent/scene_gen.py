from __future__ import annotations
from pydantic import ValidationError
from .llm import LLMClient, LLMError
from .schema import Narration, SceneSpec, validate_scene_spec, ContractError
from .script_gen import load_prompt


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
                                "content": f"上次输出不合法：{str(e).splitlines()[0][:200]}。请修正后重新只输出 JSON。"}]
        try:
            raw = client.chat_json(messages, retries=1)
            return validate_scene_spec(raw, narration)
        except (LLMError, ContractError, ValidationError):
            return fallback_spec(narration)
