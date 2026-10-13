from __future__ import annotations
import re

GAP = 0.4

_CJK = re.compile(r"[\u4e00-\u9fff]")


def align_durations(audio_durations, gap: float = GAP):
    return [d + gap for d in audio_durations]


def fit_total(audio_durations, limit):
    """软上限：从头保留完整镜头，直到再加一段就超过 limit；返回保留的段数。
    若连第一段都超过 limit，至少保留一段（不硬压、不截断旁白）。"""
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