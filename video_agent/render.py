from __future__ import annotations
import os
from manim import Scene, config

from .config import CANVAS, FPS
from .style import apply_manim_config
from .templates import render_scene


def build_scene_sequence(scenes, durations, subtitle_map):
    if len(scenes) != len(durations):
        raise ValueError(
            f"场景数({len(scenes)})与时长数({len(durations)})不一致——"
            f"违反镜头/旁白 1:1 契约"
        )
    seq = []
    for sc, dur in zip(scenes, durations):
        sub = subtitle_map.get(sc["id"]) if subtitle_map else None
        anims = render_scene(sc["type"], sc["props"], dur, sub)
        seq.append((sc["type"], anims))
    return seq


class ExplainSpec(Scene):
    SCENES: list = []
    DURATIONS: list = []
    SUBTITLE_MAP: dict = {}

    def construct(self):
        for _, anims in build_scene_sequence(self.SCENES, self.DURATIONS, self.SUBTITLE_MAP):
            for a in anims:
                self.play(a)


def render_video(spec, durations, aspect, out_dir, subtitle=False):
    apply_manim_config()
    w, h = CANVAS[aspect]
    config.pixel_width = w
    config.pixel_height = h
    config.frame_rate = FPS
    config.media_dir = os.path.join(out_dir, "media")
    sub_map = {}
    if subtitle:
        for sc in spec["scenes"]:
            sub_map[sc["id"]] = sc["props"].get("text") or sc["props"].get("heading", "")
    ExplainSpec.SCENES = spec["scenes"]
    ExplainSpec.DURATIONS = durations
    ExplainSpec.SUBTITLE_MAP = sub_map
    scene = ExplainSpec()
    scene.render()
    return str(scene.renderer.file_writer.movie_file_path)