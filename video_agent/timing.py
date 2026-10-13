from __future__ import annotations
import re

GAP = 0.4

_CJK = re.compile(r"[\u4e00-\u9fff]")


def align_durations(audio_durations, gap: float = GAP):
    return [d + gap for d in audio_durations]


def fit_total(audio_durations, limit):
    """Soft cap: keep whole shots from the front until adding one more would
    exceed ``limit``, and return how many were kept. If even the first shot
    exceeds ``limit``, keep at least one (never squeeze or cut the narration
    mid-sentence)."""
    if not limit or limit <= 0:
        return len(audio_durations)
    total = 0.0
    n = 0
    for d in audio_durations:
        if n >= 1 and total + d > limit:
            break
        total += d
        n += 1
    return n


def estimate_duration(text: str, chars_per_sec: float = 5.0) -> float:
    n = len(_CJK.findall(text)) or len(text)
    return max(0.5, n / chars_per_sec)