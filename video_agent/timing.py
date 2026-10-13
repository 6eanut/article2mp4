from __future__ import annotations

import re

# A brief beat between complete thoughts; the narration remains the master clock.
GAP = 0.12

_CJK = re.compile(r"[\u4e00-\u9fff]")


def align_durations(audio_durations, gap: float = GAP):
    return [d + gap for d in audio_durations]


def fit_total(audio_durations, limit, gap: float = GAP):
    """Soft cap: keep whole shots from the front until adding one more would
    exceed ``limit``, and return how many were kept. If even the first shot
    exceeds ``limit``, keep at least one (never squeeze or cut the narration
    mid-sentence)."""
    if not limit or limit <= 0:
        return len(audio_durations)
    total = 0.0
    n = 0
    for d in audio_durations:
        shot_duration = d + gap
        if n >= 1 and total + shot_duration > limit:
            break
        total += shot_duration
        n += 1
    return n


def fit_complete_indices(audio_durations, limit, gap: float = GAP) -> list[int]:
    """Keep the opening, as much of the body as fits, and the conclusion.

    The cap stays soft when even the opening and conclusion exceed it; cutting
    either would leave an incomplete story.
    """
    count = len(audio_durations)
    if not limit or limit <= 0 or count <= 2:
        return list(range(count))
    selected = [0]
    total = audio_durations[0] + audio_durations[-1] + 2 * gap
    for index in range(1, count - 1):
        shot = audio_durations[index] + gap
        if total + shot > limit:
            break
        selected.append(index)
        total += shot
    return [*selected, count - 1]


def estimate_duration(text: str, chars_per_sec: float = 5.0) -> float:
    n = len(_CJK.findall(text)) or len(text)
    return max(0.5, n / chars_per_sec)
