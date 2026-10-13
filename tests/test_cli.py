import os
from video_agent.cli import run_pipeline
from video_agent.schema import Narration, SceneSpec

NARR = Narration(title="T", segments=[{"id": 0, "text": "一"}, {"id": 1, "text": "二"}])

def _spec():
    return SceneSpec(title="T", aspects=["916", "169"], scenes=[
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}},
        {"id": 1, "narration_id": 1, "type": "closing", "props": {"text": "完"}},
    ])

def test_run_pipeline_writes_intermediates(tmp_path):
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    deps = dict(
        script_gen=lambda md, client: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub, subs=None: f"{o}/silent_{asp}.mp4",
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
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    called = {"render": 0}
    deps = dict(
        script_gen=lambda md, client: NARR,
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
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    seen = {}
    def render(sp, dur, asp, o, sub, subs=None):
        seen["subs"] = subs
        return f"{o}/silent_{asp}.mp4"
    deps = dict(
        script_gen=lambda md, client: NARR,
        scene_gen=lambda n, client: _spec(),
        render=render,
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=lambda **k: f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4",
        client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                 subtitle=True, voiceover_only=False, out_dir=str(out), deps=deps)
    assert seen["subs"] == ["一", "二"]

def test_max_seconds_trims_shots_and_audio(tmp_path):
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    seen = {}
    def compose(**k):
        seen["trim_to"] = k.get("trim_to")
        seen["narration"] = k["narration"]
        return f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4"
    deps = dict(
        script_gen=lambda md, client: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub, subs=None: f"{o}/silent_{asp}.mp4",
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=compose, client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=3.0, voice="v",
                 subtitle=False, voiceover_only=False, out_dir=str(out), deps=deps)
    assert len(seen["narration"].segments) == 1   # only shot 0 fits under 3.0
    assert seen["trim_to"] == 2.4 + 0.4           # 2.8