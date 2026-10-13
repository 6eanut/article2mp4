from __future__ import annotations
from manim import Animation, Wait


def entrance_hold(anim, duration: float, min_entrance: float = 0.8) -> list[Animation]:
    """把入场动画压进 [min_entrance, duration]，末尾补 Wait 填满 duration。"""
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


from . import title, bullets, closing  # noqa: E402  (须在 entrance_hold 之后)

TEMPLATES = {
    "title": title, "bullets": bullets, "closing": closing,
}


def render_scene(type: str, props: dict, duration: float, subtitle=None) -> list[Animation]:
    return TEMPLATES[type].render(props, duration, subtitle)