from __future__ import annotations
import os
from dataclasses import dataclass

CANVAS = {"916": (1080, 1920), "169": (1920, 1080)}
FPS = 30

TEMPLATE_TYPES = [
    "title", "section", "bullets", "steps", "cycle", "tree",
    "compare", "grid", "metric", "quote", "summary", "closing",
]


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls, env: dict) -> "Settings":
        missing = [k for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL") if not env.get(k)]
        if missing:
            raise ValueError(f"missing configuration: {', '.join(missing)} (set it in .env)")
        return cls(env["LLM_BASE_URL"], env["LLM_API_KEY"], env["LLM_MODEL"])


def load_settings() -> Settings:
    env: dict[str, str] = {}
    path = ".env"
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        env.setdefault(k, os.environ.get(k, ""))
    return Settings.from_env(env)