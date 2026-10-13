from __future__ import annotations
import os
from pydantic import ValidationError
from .llm import LLMClient, LLMError
from .schema import Narration

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(name: str) -> str:
    with open(os.path.join(_PROMPT_DIR, f"{name}.md"), encoding="utf-8") as f:
        return f.read()


def generate_narration(article_md: str, client: LLMClient) -> Narration:
    messages = [
        {"role": "system", "content": load_prompt("script")},
        {"role": "user", "content": article_md},
    ]
    try:
        raw = client.chat_json(messages, retries=2)
    except LLMError as e:
        raise LLMError(f"口播稿生成失败: {e}")
    try:
        return Narration(**raw)
    except ValidationError as e:
        raise LLMError(f"口播稿格式不合法: {str(e).splitlines()[0][:200]}")