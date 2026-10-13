from __future__ import annotations
import logging
import os
from manim import Scene, Text, FadeIn, DOWN, config

from .config import CANVAS, FPS, DESIGN_FRAME_WIDTH
from .style import apply_manim_config, FONT, FG
from .templates import render_scene, entrance_hold


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
    t = Text(str(text), font=FONT, font_size=36, color=FG)
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
            logging.warning("scene %s failed to render, degrading to a text-only shot: %s", sc.get("id"), e)
            anims = _degrade_shot(sc, dur, sub)
        seq.append((sc["type"], anims))
    return seq


def _caption(text):
    t = Text(str(text), font=FONT, font_size=28, color=FG)
    if t.width > 12.0:
        t.scale_to_fit_width(12.0)
    return t.to_edge(DOWN, buff=0.6).set_z_index(10)


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
                self.PROGRESS(self._DONE, len(self.SCENES))
            self._DONE += 1
            text = self.SUBTITLE_MAP.get(sc["id"])
            if text:
                self.add(_caption(text))
            for a in anims:
                self.play(a)
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