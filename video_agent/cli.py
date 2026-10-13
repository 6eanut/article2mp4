from __future__ import annotations

import argparse
import json
import math
import os
import shutil

from . import progress as prog
from .compose import assert_av_sync, concat_voiceover, mux, trim_audio
from .config import load_settings
from .llm import LLMClient
from .render import render_video
from .scene_gen import generate_scene_spec
from .script_gen import generate_narration
from .timing import GAP, align_durations, fit_complete_indices
from .tts import probe_duration, render_voiceover


def _write_narration(narration, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(json.loads(narration.model_dump_json()), file,
                  ensure_ascii=False, indent=2)


def _default_deps():
    def _client():
        return LLMClient(load_settings())

    def _render(spec, durations, aspect, out_dir, subtitle, subtitles=None, progress=None):
        return render_video(spec, durations, aspect, out_dir,
                            subtitle=subtitle, subtitles=subtitles, progress=progress)

    def _voiceover(narration, out_dir, voice):
        return render_voiceover(narration, out_dir, voice)

    def _compose(**k):
        ids = k.get("audio_ids") or [s.id for s in k["narration"].segments]
        vo = concat_voiceover(k["audio_dir"], ids,
                              os.path.join(k["out_dir"], "voice.wav"), gap=GAP)
        if k.get("trim_to"):
            vo = trim_audio(vo, k["trim_to"],
                            os.path.join(k["out_dir"], "voice_trimmed.wav"))
        out = os.path.join(k["out_dir"], f"{k['name']}_{k['aspect']}.mp4")
        mux(k["video"], vo, k.get("bgm"), out)
        assert_av_sync(probe_duration(out), probe_duration(vo), tol=0.3)
        return out

    return dict(client=_client, render=_render, voiceover=_voiceover,
                compose=_compose, script_gen=generate_narration, scene_gen=generate_scene_spec)


def run_pipeline(article_path, aspect, max_seconds, voice, subtitle,
                 voiceover_only, out_dir=None, deps=None, progress_enabled=True):
    if max_seconds is not None and (not math.isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError("--max-seconds must be a positive finite number")
    deps = deps or _default_deps()
    prog.ENABLED = progress_enabled
    TOTAL = 6
    name = os.path.splitext(os.path.basename(article_path))[0]
    out_dir = out_dir or os.path.join("output", name)
    os.makedirs(out_dir, exist_ok=True)

    with open(article_path, encoding="utf-8") as f:
        article = f.read()
    client = deps["client"]()
    prog.stage(1, TOTAL, "Narration")
    narration = deps["script_gen"](article, client, target_seconds=max_seconds)
    prog.detail(f"{len(narration.segments)} segments")
    narration_path = os.path.join(out_dir, "narration.json")
    _write_narration(narration, narration_path)
    audio_dir = os.path.join(out_dir, "audio")
    prog.stage(2, TOTAL, "Voiceover")
    durations = deps["voiceover"](narration, audio_dir, voice)
    if len(durations) != len(narration.segments):
        raise ValueError("voiceover duration count does not match narration segments")
    prog.detail(f"{len(durations)} audio files")
    audio_ids = [segment.id for segment in narration.segments]
    trim_to = None
    if max_seconds:
        selected = fit_complete_indices(durations, max_seconds, gap=GAP)
        if len(selected) < len(durations):
            selected_audio_ids = [audio_ids[index] for index in selected]
            narration = narration.model_copy(update={"segments": [
                narration.segments[index].model_copy(update={"id": new_id})
                for new_id, index in enumerate(selected)
            ]})
            durations = [durations[index] for index in selected]
            selected_audio_dir = os.path.join(out_dir, "audio_selected")
            os.makedirs(selected_audio_dir, exist_ok=True)
            for new_id, old_id in enumerate(selected_audio_ids):
                shutil.copyfile(os.path.join(audio_dir, f"{old_id:03d}.wav"),
                                os.path.join(selected_audio_dir, f"{new_id:03d}.wav"))
            audio_dir = selected_audio_dir
            audio_ids = list(range(len(selected)))
        trim_to = sum(durations) + GAP * len(durations)
        if trim_to > max_seconds + 0.05:
            prog.detail(f"soft cap exceeded: opening and conclusion need {trim_to:.1f}s")

    _write_narration(narration, narration_path)

    if voiceover_only:
        return {"narration": narration_path,
                "audio_dir": audio_dir}

    subtitles = [s.text for s in narration.segments] if subtitle else None

    prog.stage(3, TOTAL, "Scene spec")
    spec = deps["scene_gen"](narration, client)
    prog.detail(f"{len(spec.scenes)} scenes")
    with open(os.path.join(out_dir, "scene_spec.json"), "w", encoding="utf-8") as f:
        json.dump(json.loads(spec.model_dump_json()), f, ensure_ascii=False, indent=2)

    prog.stage(4, TOTAL, "Align")
    shot = align_durations(durations)
    bgm = os.path.join("assets", "bgm", "track.mp3")
    aspects = ["916", "169"] if aspect == "both" else [aspect]
    result = {}
    for asp in aspects:
        prog.stage(5, TOTAL, f"Render ({asp})")
        video = deps["render"](json.loads(spec.model_dump_json()), shot, asp,
                               out_dir, subtitle, subtitles,
                               progress=lambda done, n: prog.detail(f"scene {done + 1}/{n}"))
        prog.stage(6, TOTAL, f"Compose ({asp})")
        result[asp] = deps["compose"](
            video=video, audio_dir=audio_dir, narration=narration, out_dir=out_dir,
            name=name, aspect=asp, bgm=bgm, trim_to=trim_to, audio_ids=audio_ids,
        )
        prog.detail(os.path.basename(result[asp]))
    return {"video": result[aspect] if aspect in result else next(iter(result.values())),
            "all": result}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="video_agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("article")
    m.add_argument("--aspect", default="both", choices=["916", "169", "both"])
    m.add_argument("--max-seconds", type=float, default=None)
    m.add_argument("--voice", default="zf_001")
    m.add_argument("--subtitle", action=argparse.BooleanOptionalAction, default=True,
                   help="burn the narration in as subtitles (default: on)")
    m.add_argument("--voiceover-only", action="store_true")
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "make":
        run_pipeline(a.article, a.aspect, a.max_seconds, a.voice,
                     a.subtitle, a.voiceover_only)
        return 0
    return 1
