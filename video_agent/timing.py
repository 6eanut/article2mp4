from __future__ import annotations
import re

_CJK = re.compile(r"[\u4e00-\u9fff]")


def align_durations(audio_durations, gap: float = 0.4):
    return [d + gap for d in audio_durations]


def estimate_duration(text: str, chars_per_sec: float = 5.0) -> float:
    n = len(_CJK.findall(text)) or len(text)
    return max(0.5, n / chars_per_sec)