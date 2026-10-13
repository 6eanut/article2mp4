from __future__ import annotations

from manim import Animation, Wait


def entrance_hold(anim, duration: float, min_entrance: float = 0.4) -> list[Animation]:
    """Squeeze the entrance animation into [min_entrance, duration], then pad
    the remainder with a Wait so the total equals ``duration``."""
    anims: list[Animation] = []
    if anim is not None:
        entrance = min(min_entrance, duration)
        anim.run_time = entrance
        anims.append(anim)
        rest = duration - entrance
    else:
        rest = duration
    if rest > 1e-6:
        anims.append(Wait(rest))
    return anims


from . import (  # noqa: E402  (must come after entrance_hold is defined)
    bullets,
    closing,
    compare,
    cycle,
    grid,
    metric,
    quote,
    section,
    steps,
    summary,
    title,
    tree,
)

TEMPLATES = {
    "title": title, "bullets": bullets, "closing": closing,
    "section": section, "quote": quote, "compare": compare, "summary": summary,
    "steps": steps, "cycle": cycle, "tree": tree, "grid": grid, "metric": metric,
}


def render_scene(type: str, props: dict, duration: float, subtitle=None) -> list[Animation]:
    return TEMPLATES[type].render(props, duration, subtitle)
