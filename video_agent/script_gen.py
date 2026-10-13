from __future__ import annotations

import os
import re

from pydantic import ValidationError

from .llm import LLMClient, LLMError
from .schema import Narration
from .timing import GAP

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_-]*")
_MAX_ESTIMATED_SECONDS = 78.0


def _estimated_seconds(narration: Narration) -> float:
    """Conservative script length estimate before the slower TTS pass."""
    total = 0.0
    for segment in narration.segments:
        cjk = len(_CJK.findall(segment.text))
        words = len(_WORD.findall(segment.text))
        speech = cjk / 3.6 + words / 2.6
        total += max(0.5, speech) + GAP
    return total


def load_prompt(name: str) -> str:
    with open(os.path.join(_PROMPT_DIR, f"{name}.md"), encoding="utf-8") as f:
        return f.read()


def generate_narration(article_md: str, client: LLMClient,
                       target_seconds: float | None = None) -> Narration:
    messages = [
        {"role": "system", "content": load_prompt("script")},
        {"role": "user", "content": article_md},
    ]
    if target_seconds:
        messages.append({"role": "user", "content": (
            f"Make a complete video under {target_seconds:g} seconds, including "
            "the conclusion. Keep the strongest facts and use fewer short segments."
        )})
    try:
        raw = client.chat_json(messages, retries=2)
    except LLMError as e:
        raise LLMError(f"narration generation failed: {e}")
    try:
        narration = Narration(**raw)
    except ValidationError as e:
        raise LLMError(f"narration format is invalid: {str(e).splitlines()[0][:200]}")

    budget = (
        min(_MAX_ESTIMATED_SECONDS, target_seconds * 0.9)
        if target_seconds else _MAX_ESTIMATED_SECONDS
    )
    if _estimated_seconds(narration) <= budget and len(narration.segments) <= 16:
        return narration

    revision = messages + [
        {"role": "assistant", "content": narration.model_dump_json()},
        {"role": "user", "content": (
            f"This draft will run too long. Rewrite it shorter, aiming for at most "
            f"{min(65.0, budget * 0.9):g} seconds and a complete story. Remove filler and repeated "
            "points while retaining the article's core facts, figures, hook, and useful "
            "ending. Use sequential IDs from 0. Return JSON only."
        )},
    ]
    try:
        shorter = Narration(**client.chat_json(revision, retries=1))
    except (LLMError, ValidationError):
        return narration
    if _estimated_seconds(shorter) < _estimated_seconds(narration):
        return shorter
    return narration
