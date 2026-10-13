import os

import pytest

from video_agent.cli import run_pipeline
from video_agent.schema import Narration, SceneSpec
from video_agent.timing import GAP

NARR = Narration(title="T", segments=[{"id": 0, "text": "one"}, {"id": 1, "text": "two"}])

def _spec():
    return SceneSpec(title="T", aspects=["916", "169"], scenes=[
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}},
        {"id": 1, "narration_id": 1, "type": "closing", "props": {"text": "done"}},
    ])

def test_run_pipeline_writes_intermediates(tmp_path):
    art = tmp_path / "a.md"
    art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    deps = dict(
        script_gen=lambda md, client, target_seconds=None: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub, subs=None, progress=None: f"{o}/silent_{asp}.mp4",
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=lambda **k: f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4",
        client=lambda: object(),
    )
    res = run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                       subtitle=False, voiceover_only=False, out_dir=str(out), deps=deps)
    assert os.path.exists(str(out / "narration.json"))
    assert os.path.exists(str(out / "scene_spec.json"))
    assert "a_916.mp4" in res["video"]

def test_voiceover_only_skips_render(tmp_path):
    art = tmp_path / "a.md"
    art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    called = {"render": 0}
    deps = dict(
        script_gen=lambda md, client, target_seconds=None: NARR,
        scene_gen=None,
        render=lambda *a: called.__setitem__("render", 1),
        voiceover=lambda n, o, v: [2.4, 2.4],
        compose=lambda **k: "x", client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                 subtitle=False, voiceover_only=True, out_dir=str(out), deps=deps)
    assert called["render"] == 0
    assert os.path.exists(str(out / "narration.json"))

def test_run_pipeline_passes_subtitles(tmp_path):
    art = tmp_path / "a.md"
    art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    seen = {}
    def render(sp, dur, asp, o, sub, subs=None, progress=None):
        seen["subs"] = subs
        return f"{o}/silent_{asp}.mp4"
    deps = dict(
        script_gen=lambda md, client, target_seconds=None: NARR,
        scene_gen=lambda n, client: _spec(),
        render=render,
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=lambda **k: f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4",
        client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                 subtitle=True, voiceover_only=False, out_dir=str(out), deps=deps)
    assert seen["subs"] == ["one", "two"]

def test_max_seconds_preserves_opening_and_ending(tmp_path, capsys):
    art = tmp_path / "a.md"
    art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    seen = {}
    def compose(**k):
        seen["trim_to"] = k.get("trim_to")
        seen["narration"] = k["narration"]
        return f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4"
    deps = dict(
        script_gen=lambda md, client, target_seconds=None: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub, subs=None, progress=None: f"{o}/silent_{asp}.mp4",
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=compose, client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=3.0, voice="v",
                 subtitle=False, voiceover_only=False, out_dir=str(out), deps=deps)
    assert len(seen["narration"].segments) == 2
    assert seen["trim_to"] == 2 * (2.4 + GAP)
    assert "soft cap exceeded" in capsys.readouterr().out

def test_run_pipeline_reports_monotonic_progress(tmp_path, capsys):
    import re
    art = tmp_path / "a.md"
    art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    deps = dict(
        script_gen=lambda md, client, target_seconds=None: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub, subs=None, progress=None: f"{o}/silent_{asp}.mp4",
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=lambda **k: f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4",
        client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                 subtitle=True, voiceover_only=False, out_dir=str(out), deps=deps)
    out_text = capsys.readouterr().out
    nums = [int(m.group(1)) for m in re.finditer(r"^\[(\d+)/6\]", out_text, re.M)]
    assert nums == [1, 2, 3, 4, 5, 6]


def test_default_subtitle_option_is_on():
    from video_agent.cli import build_parser
    assert build_parser().parse_args(["make", "a.md"]).subtitle is True
    assert build_parser().parse_args(["make", "a.md", "--no-subtitle"]).subtitle is False


def test_max_seconds_counts_pauses_and_saves_the_played_narration(tmp_path):
    art = tmp_path / "a.md"
    art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    seen = {}
    long_narr = Narration(title="T", segments=[
        {"id": i, "text": f"line {i}"} for i in range(4)
    ])

    def scene_gen(n, client):
        return SceneSpec(title="T", aspects=["916"], scenes=[
            {"id": i, "narration_id": i,
             "type": "title" if i == 0 else "closing" if i == len(n.segments) - 1 else "quote",
             "props": {"title": "T"} if i == 0 else {"text": s.text}}
            for i, s in enumerate(n.segments)
        ])

    def voiceover(n, audio_dir, voice):
        os.makedirs(audio_dir, exist_ok=True)
        for segment in n.segments:
            with open(os.path.join(audio_dir, f"{segment.id:03d}.wav"), "wb") as file:
                file.write(bytes([segment.id]))
        return [2.0] * 4

    def compose(**kwargs):
        seen["audio_ids"] = kwargs["audio_ids"]
        seen["audio_dir"] = kwargs["audio_dir"]
        return f"{kwargs['out_dir']}/result.mp4"

    deps = dict(
        script_gen=lambda md, client, target_seconds=None: long_narr,
        scene_gen=scene_gen,
        render=lambda sp, dur, asp, o, sub, subs=None, progress=None: seen.setdefault("dur", dur),
        voiceover=voiceover,
        compose=compose,
        client=lambda: object(),
    )
    run_pipeline(str(art), "916", 6.4, "v", False, False, out_dir=str(out), deps=deps)
    import json
    saved = json.loads((out / "narration.json").read_text(encoding="utf-8"))
    assert [s["text"] for s in saved["segments"]] == ["line 0", "line 1", "line 3"]
    assert [s["id"] for s in saved["segments"]] == [0, 1, 2]
    assert seen["audio_ids"] == [0, 1, 2]
    assert [open(os.path.join(seen["audio_dir"], f"{i:03d}.wav"), "rb").read()
            for i in range(3)] == [b"\x00", b"\x01", b"\x03"]
    assert seen["dur"] == [2.0 + GAP] * 3


def test_voiceover_only_cap_returns_audio_matching_saved_ids(tmp_path):
    art = tmp_path / "article.md"
    art.write_text("# short", encoding="utf-8")
    narration = Narration(title="T", segments=[
        {"id": i, "text": f"part {i}"} for i in range(4)
    ])

    def voiceover(n, audio_dir, voice):
        os.makedirs(audio_dir)
        for segment in n.segments:
            with open(os.path.join(audio_dir, f"{segment.id:03d}.wav"), "wb") as file:
                file.write(bytes([segment.id]))
        return [2.0] * 4

    deps = dict(client=lambda: object(),
                script_gen=lambda md, client, target_seconds=None: narration,
                voiceover=voiceover)
    result = run_pipeline(str(art), "916", 6.4, "v", False, True,
                          out_dir=str(tmp_path / "out"), deps=deps)
    assert [open(os.path.join(result["audio_dir"], f"{i:03d}.wav"), "rb").read()
            for i in range(3)] == [b"\x00", b"\x01", b"\x03"]


def test_failed_voiceover_keeps_generated_narration_for_diagnosis(tmp_path):
    art = tmp_path / "article.md"
    art.write_text("# article", encoding="utf-8")
    out = tmp_path / "out"

    def fail_voiceover(narration, audio_dir, voice):
        raise RuntimeError("Final couldn't be detected")

    deps = dict(client=lambda: object(),
                script_gen=lambda article, client, target_seconds=None: NARR,
                voiceover=fail_voiceover)
    with pytest.raises(RuntimeError, match="Final couldn't be detected"):
        run_pipeline(str(art), "916", None, "v", True, False,
                     out_dir=str(out), deps=deps)
    assert (out / "narration.json").exists()
    assert '"text": "one"' in (out / "narration.json").read_text(encoding="utf-8")
