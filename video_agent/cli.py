from __future__ import annotations
import argparse
import json
import os

from .config import load_settings
from .llm import LLMClient
from .script_gen import generate_narration
from .scene_gen import generate_scene_spec
from .timing import align_durations, GAP, fit_total
from .tts import render_voiceover, probe_duration
from .render import render_video
from .compose import concat_voiceover, mux, assert_av_sync, trim_audio


def _default_deps():
    def _client():
        return LLMClient(load_settings())

    def _render(spec, durations, aspect, out_dir, subtitle, subtitles=None):
        return render_video(spec, durations, aspect, out_dir,
                            subtitle=subtitle, subtitles=subtitles)

    def _voiceover(narration, out_dir, voice):
        return render_voiceover(narration, out_dir, voice)

    def _compose(**k):
        ids = [s.id for s in k["narration"].segments]
        vo = concat_voiceover(k["audio_dir"], ids,
                              os.path.join(k["out_dir"], "voice.mp3"), gap=GAP)
        if k.get("trim_to"):
            vo = trim_audio(vo, k["trim_to"])
        out = os.path.join(k["out_dir"], f"{k['name']}_{k['aspect']}.mp4")
        mux(k["video"], vo, k.get("bgm"), out)
        assert_av_sync(probe_duration(out), probe_duration(vo), tol=0.3)
        return out

    return dict(client=_client, render=_render, voiceover=_voiceover,
                compose=_compose, script_gen=generate_narration, scene_gen=generate_scene_spec)


def run_pipeline(article_path, aspect, max_seconds, voice, subtitle,
                 voiceover_only, out_dir=None, deps=None):
    deps = deps or _default_deps()
    name = os.path.splitext(os.path.basename(article_path))[0]
    out_dir = out_dir or os.path.join("output", name)
    os.makedirs(out_dir, exist_ok=True)

    with open(article_path, encoding="utf-8") as f:
        article = f.read()
    client = deps["client"]()
    narration = deps["script_gen"](article, client)
    with open(os.path.join(out_dir, "narration.json"), "w", encoding="utf-8") as f:
        json.dump(json.loads(narration.model_dump_json()), f, ensure_ascii=False, indent=2)

    audio_dir = os.path.join(out_dir, "audio")
    durations = deps["voiceover"](narration, audio_dir, voice)
    trim_to = None
    if max_seconds:
        k = fit_total(durations, max_seconds)
        if k < len(durations):
            narration = narration.model_copy(update={"segments": narration.segments[:k]})
            durations = durations[:k]
        trim_to = sum(durations) + GAP * len(durations)

    if voiceover_only:
        return {"narration": os.path.join(out_dir, "narration.json")}

    subtitles = [s.text for s in narration.segments] if subtitle else None

    spec = deps["scene_gen"](narration, client)
    with open(os.path.join(out_dir, "scene_spec.json"), "w", encoding="utf-8") as f:
        json.dump(json.loads(spec.model_dump_json()), f, ensure_ascii=False, indent=2)

    shot = align_durations(durations)
    bgm = os.path.join("assets", "bgm", "track.mp3")
    aspects = ["916", "169"] if aspect == "both" else [aspect]
    result = {}
    for asp in aspects:
        video = deps["render"](json.loads(spec.model_dump_json()), shot, asp,
                               out_dir, subtitle, subtitles)
        result[asp] = deps["compose"](
            video=video, audio_dir=audio_dir, narration=narration, out_dir=out_dir,
            name=name, aspect=asp, bgm=bgm, trim_to=trim_to,
        )
    return {"video": result[aspect] if aspect in result else next(iter(result.values())),
            "all": result}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="video_agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("article")
    m.add_argument("--aspect", default="both", choices=["916", "169", "both"])
    m.add_argument("--max-seconds", type=float, default=None)
    m.add_argument("--voice", default="zf_001")
    m.add_argument("--subtitle", action="store_true")
    m.add_argument("--voiceover-only", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "make":
        res = run_pipeline(a.article, a.aspect, a.max_seconds, a.voice,
                           a.subtitle, a.voiceover_only)
        print("完成:", res)
        return 0
    return 1