"""Human-readable progress lines for the pipeline.

Emits one numbered line per stage ("[2/6] Voiceover … 12 segments") plus optional
indented detail lines, so the run is legible without Manim's log spew. Output can
be silenced by setting ``ENABLED = False``.
"""
from __future__ import annotations

ENABLED: bool = True


def stage(n: int, total: int, label: str, detail: str = "") -> None:
    """Print a stage header like ``[2/6] Voiceover … 12 segments``."""
    if not ENABLED:
        return
    line = f"[{n}/{total}] {label}"
    if detail:
        line += f" … {detail}"
    print(line, flush=True)


def detail(msg: str) -> None:
    """Print an indented detail line under the current stage."""
    if not ENABLED:
        return
    print(f"  · {msg}", flush=True)