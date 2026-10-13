from __future__ import annotations
import logging
import os
from manim import Scene, Text, FadeIn, DOWN, config

from .config import CANVAS, FPS
from .style import apply_manim_config, FONT, FG
from .templates import render_scene, entrance_hold

# 逻辑画框宽度取 16:9 的标准宽 14.222（=1920/135），使 9:16 与 16:9 两版
# 的像素/单位比例一致、模板字号通用；高度按画布比例推出。
DESIGN_FRAME_WIDTH = 14.222222222222221


def frame_dimensions(aspect: str) -> tuple[float, float]:
    """逻辑画框 (width, height)：宽度固定为设计宽，高度按画布宽高比推出，
    保证 9:16 与 16:9 两版的像素/单位比例一致，且画框与画布同比（不出现黑边）。"""
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
            f"场景数({len(scenes)})与时长数({len(durations)})不一致——"
            f"违反镜头/旁白 1:1 契约"
        )
    seq = []
    for sc, dur in zip(scenes, durations):
        sub = subtitle_map.get(sc["id"]) if subtitle_map else None
        try:
            anims = render_scene(sc["type"], sc["props"], dur, sub)
        except Exception as e:  # 画面出错降级继续：该镜退化为纯文字镜
            logging.warning("场景 %s 渲染失败，降级为纯文字镜: %s", sc.get("id"), e)
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

    def construct(self):
        for (_, anims), sc in zip(
            build_scene_sequence(self.SCENES, self.DURATIONS, None), self.SCENES
        ):
            text = self.SUBTITLE_MAP.get(sc["id"])
            if text:
                self.add(_caption(text))
            for a in anims:
                self.play(a)
            self.clear()


def render_video(spec, durations, aspect, out_dir, subtitle=False, subtitles=None):
    apply_manim_config()
    w, h = CANVAS[aspect]
    config.pixel_width = w
    config.pixel_height = h
    # 逻辑画框必须与目标画布同比，否则 Manim 会按宽度把 16:9 默认画框塞进
    # 9:16 画布，内容被压在中间一条、左右黑边，to_edge(DOWN) 的字幕也落到画外。
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
    scene = ExplainSpec()
    scene.render()
    return str(scene.renderer.file_writer.movie_file_path)