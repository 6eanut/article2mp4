from __future__ import annotations
import json
from typing import Callable
from .config import Settings


class LLMError(Exception):
    pass


def strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
        if t.strip().startswith("json"):
            t = t.strip()[4:]
    return t.strip()


class LLMClient:
    def __init__(self, settings: Settings, transport: Callable[[list[dict]], str] | None = None):
        self.settings = settings
        self._transport = transport or self._openai_transport

    def _openai_transport(self, messages: list[dict]) -> str:
        from openai import OpenAI
        client = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key)
        resp = client.chat.completions.create(model=self.settings.model, messages=messages)
        return resp.choices[0].message.content

    def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        return self._transport(messages)

    def chat_json(self, messages: list[dict], retries: int = 2) -> dict:
        last_err = None
        for _ in range(retries + 1):
            raw = self._transport(messages)
            try:
                return json.loads(strip_fence(raw))
            except json.JSONDecodeError as e:
                last_err = e
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"输出不是合法 JSON（{e}）。只输出 JSON，不要解释。"},
                ]
        raise LLMError(f"无法获得合法 JSON: {last_err}")