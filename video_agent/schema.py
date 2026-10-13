from __future__ import annotations
from pydantic import BaseModel
from .config import TEMPLATE_TYPES


class ContractError(Exception):
    """分镜 JSON 不符合契约。"""


class Segment(BaseModel):
    id: int
    text: str


class Narration(BaseModel):
    title: str
    segments: list[Segment]


class Scene(BaseModel):
    id: int
    narration_id: int
    type: str
    props: dict


class SceneSpec(BaseModel):
    title: str
    aspects: list[str]
    scenes: list[Scene]


PROPS_REQUIRED: dict[str, list[str]] = {
    "title":   ["title"],
    "section": ["index", "heading"],
    "bullets": ["heading", "items"],
    "steps":   ["heading", "steps"],
    "cycle":   ["heading", "nodes"],
    "tree":    ["heading", "root", "children"],
    "compare": ["heading", "left", "right"],
    "grid":    ["heading", "cells"],
    "metric":  ["heading", "value", "label"],
    "quote":   ["text"],
    "summary": ["heading", "items"],
    "closing": ["text"],
}


def validate_scene_spec(raw: dict, narration: Narration) -> SceneSpec:
    spec = SceneSpec(**raw)
    if len(spec.scenes) != len(narration.segments):
        raise ContractError(
            f"镜头数量({len(spec.scenes)})与旁白段数({len(narration.segments)})不一致"
        )
    for i, sc in enumerate(spec.scenes):
        if sc.type not in TEMPLATE_TYPES:
            raise ContractError(f"未知镜头类型: {sc.type}")
        if sc.narration_id != i:
            raise ContractError(f"scene[{i}].narration_id={sc.narration_id} 应为 {i}")
        missing = [f for f in PROPS_REQUIRED[sc.type] if f not in sc.props]
        if missing:
            raise ContractError(f"{sc.type} 缺少必填字段: {', '.join(missing)}")
    return spec