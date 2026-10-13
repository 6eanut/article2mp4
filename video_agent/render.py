from __future__ import annotations

import logging
import os
import re

from manim import DOWN, FadeIn, RoundedRectangle, Scene, VGroup, VMobject, Wait, config

from .config import CANVAS, DESIGN_FRAME_WIDTH, FPS
from .style import FG, FONT, apply_manim_config
from .templates import entrance_hold, render_scene
from .templates._fit import wrapped_text


def frame_dimensions(aspect: str) -> tuple[float, float]:
    """Logical frame (width, height): the width is fixed to the design width and
    the height is derived from the canvas ratio, so both the 9:16 and 16:9
    versions keep the same pixels-per-unit scale and the frame matches the canvas
    ratio (no letterboxing)."""
    w, h = CANVAS[aspect]
    return DESIGN_FRAME_WIDTH, DESIGN_FRAME_WIDTH * h / w


def _degrade_shot(scene, duration, subtitle=None):
    props = scene.get("props", {})
    text = props.get("text") or props.get("heading") or props.get("title") or "…"
    t = wrapped_text(str(text), max_width=12.0, font=FONT, font_size=36, color=FG)
    return entrance_hold(FadeIn(t), duration)


def build_scene_sequence(scenes, durations, subtitle_map):
    if len(scenes) != len(durations):
        raise ValueError(
            f"scene count ({len(scenes)}) != duration count ({len(durations)}) — "
            f"violates the 1:1 shot/narration contract"
        )
    seq = []
    for sc, dur in zip(scenes, durations):
        sub = subtitle_map.get(sc["id"]) if subtitle_map else None
        try:
            anims = render_scene(sc["type"], sc["props"], dur, sub)
        except Exception as e:  # render error -> degrade and continue: text-only shot
            logging.warning(
                "scene %s failed to render, degrading to a text-only shot: %s",
                sc.get("id"), e,
            )
            anims = _degrade_shot(sc, dur, sub)
        seq.append((sc["type"], anims))
    return seq


def _caption(text):
    font_size = 42 if config.frame_height > config.frame_width else 36
    t = wrapped_text(str(text), max_width=11.8, font=FONT,
                     font_size=font_size, color=FG)
    box = RoundedRectangle(
        corner_radius=0.14, width=t.width + 0.7, height=t.height + 0.4,
        fill_color="#0B1220", fill_opacity=0.94, stroke_opacity=0,
    )
    t.move_to(box)
    return VGroup(box, t).to_edge(DOWN, buff=max(0.6, config.frame_height * 0.1)).set_z_index(10)


def _caption_chunks(text: str) -> list[str]:
    """Split narration into cards with at most two measured lines each."""
    font_size = 42 if config.frame_height > config.frame_width else 36
    lines = wrapped_text(str(text), max_width=11.8, font=FONT,
                         font_size=font_size, color=FG).original_text.split("\n")
    return ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]


def _caption_weight(text: str) -> float:
    """Estimate spoken length from CJK characters and Latin words."""
    tokens = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[^\W_]", text)
    weight = 0.0
    for token in tokens:
        if token.isascii() and token.replace("'", "").isalpha():
            weight += max(1.0, len(token) / 4)
        elif token.isdigit():
            weight += max(1.0, len(token) / 3)
        else:
            weight += 1.0
    return max(1.0, weight)


def _play_with_captions(scene, anims, captions):
    """Change cards during holds without changing the shot's total runtime."""
    if len(captions) < 2:
        for anim in anims:
            scene.play(anim)
        return
    total = sum(anim.run_time for anim in anims)
    weights = [_caption_weight(card[1].original_text) for card in captions]
    total_weight = sum(weights)
    minimum = min(0.3, total / (2 * len(captions)))
    variable_time = total - minimum * len(captions)
    durations = [minimum + variable_time * weight / total_weight for weight in weights]
    boundaries = []
    for duration in durations[:-1]:
        boundaries.append((boundaries[-1] if boundaries else 0.0) + duration)
    elapsed = 0.0
    card_index = 0

    def advance_card():
        nonlocal card_index
        scene.remove(captions[card_index])
        card_index += 1
        scene.add(captions[card_index])

    for anim in anims:
        if isinstance(anim, Wait):
            remaining = anim.run_time
            while (card_index < len(boundaries)
                   and boundaries[card_index] <= elapsed + remaining + 1e-9):
                segment = max(0.0, boundaries[card_index] - elapsed)
                if segment > 1e-9:
                    scene.play(Wait(segment))
                    elapsed += segment
                    remaining -= segment
                advance_card()
            if remaining > 1e-9:
                scene.play(Wait(remaining))
                elapsed += remaining
        else:
            scene.play(anim)
            elapsed += anim.run_time
            while card_index < len(boundaries) and boundaries[card_index] <= elapsed + 1e-9:
                advance_card()


def _place_content(anims, caption=None):
    """Fit each shot in the region above the subtitle card."""
    members = []
    for anim in anims:
        member = getattr(anim, "mobject", None)
        if isinstance(member, VMobject) and not any(member is item for item in members):
            members.append(member)
    if not members:
        return
    group = VGroup(*members)
    top = config.frame_height / 2 - 0.4
    if caption is not None:
        bottom = caption.get_top()[1] + 0.35
    elif config.frame_height > config.frame_width:
        bottom = -config.frame_height / 2 + config.frame_height * 0.15
    else:
        bottom = -config.frame_height / 2 + 0.4
    available_height = max(0.1, top - bottom)
    available_width = config.frame_width - 1.2
    if config.frame_height > config.frame_width and group.width > 0 and group.height > 0:
        # Sparse 9:16 scenes should use the phone screen, not sit as a narrow
        # landscape-sized strip in its middle.
        group.scale(min(3.0, available_width / group.width,
                        available_height * 0.62 / group.height))
    if group.width > available_width:
        group.scale_to_fit_width(available_width)
    if group.height > available_height:
        group.scale_to_fit_height(available_height)
    group.move_to([0, (top + bottom) / 2, 0])


def build_subtitle_map(spec, subtitles):
    if not subtitles:
        return {}
    return {sc["id"]: subtitles[i]
            for i, sc in enumerate(spec["scenes"]) if i < len(subtitles)}


class ExplainSpec(Scene):
    SCENES: list = []
    DURATIONS: list = []
    SUBTITLE_MAP: dict = {}
    PROGRESS = None       # callable(done, total) or None
    _DONE: int = 0

    def construct(self):
        for (_, anims), sc in zip(
            build_scene_sequence(self.SCENES, self.DURATIONS, None), self.SCENES
        ):
            if self.PROGRESS is not None:
                # Call via the class so a plain-function/partial callback is not
                # bound as an instance method (which would inject `self` and add
                # an argument, breaking the `(done, total)` contract).
                type(self).PROGRESS(self._DONE, len(self.SCENES))
            self._DONE += 1
            text = self.SUBTITLE_MAP.get(sc["id"])
            captions = []
            if text:
                captions = [_caption(chunk) for chunk in _caption_chunks(text)]
                self.add(captions[0])
            tallest_caption = max(captions, key=lambda card: card.get_top()[1], default=None)
            _place_content(anims, tallest_caption)
            _play_with_captions(self, anims, captions)
            self.clear()


def render_video(spec, durations, aspect, out_dir, subtitle=False, subtitles=None,
                 progress=None):
    apply_manim_config()
    # Mute Manim's startup banner, per-animation INFO lines, and tqdm bar so the
    # pipeline's own progress output is the primary, readable signal.
    config.verbosity = "ERROR"
    config.progress_bar = "none"
    w, h = CANVAS[aspect]
    config.pixel_width = w
    config.pixel_height = h
    # The logical frame must match the target canvas ratio; otherwise Manim fits
    # the default 16:9 frame by width into the 9:16 canvas, squeezing the content
    # into a middle strip with side letterboxing and pushing the to_edge(DOWN)
    # subtitles off-screen.
    config.frame_width, config.frame_height = frame_dimensions(aspect)
    config.frame_rate = FPS
    config.media_dir = os.path.join(out_dir, "media")
    sub_map = {}
    if subtitle:
        if subtitles:
            sub_map = build_subtitle_map(spec, subtitles)
        else:
            for sc in spec["scenes"]:
                sub_map[sc["id"]] = sc["props"].get("text") or sc["props"].get("heading", "")
    ExplainSpec.SCENES = spec["scenes"]
    ExplainSpec.DURATIONS = durations
    ExplainSpec.SUBTITLE_MAP = sub_map
    ExplainSpec.PROGRESS = progress
    ExplainSpec._DONE = 0
    scene = ExplainSpec()
    scene.render()
    return str(scene.renderer.file_writer.movie_file_path)
