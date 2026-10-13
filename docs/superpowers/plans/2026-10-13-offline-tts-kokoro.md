# article2mp4 — Replace edge-tts with offline Kokoro-82M (Chinese) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken edge-tts voiceover backend (Microsoft's Edge Read Aloud WS API changed on 2026-10-10; see rany2/edge-tts#490) with a fully offline Kokoro-82M Chinese TTS, so stage ③ synthesizes real narration on CPU with no network at inference time.

**Architecture:** Add a thin engine seam in `video_agent/tts.py`. A new module `video_agent/voice_engine.py` lazily downloads the Kokoro Chinese model + voices (via a GitHub proxy) into a cache dir and drives the ONNX session **directly** (the `kokoro-onnx` wrapper's `create()` passes a wrong `speed` dtype for this export). Chinese text → IPA phonemes via `misaki.zh.ZHG2P`, phonemes → token ids via the model's tokenizer, ids+style+speed → waveform. `render_voiceover` keeps its exact signature and just swaps the default `synth` from `synth_segment` (edge-tts) to the new engine. The CLI passes `speed` through to the engine.

**Tech Stack:** Python 3.14, `kokoro-onnx` 0.4.7, `misaki[zh]` 0.7.4, `onnxruntime` 1.31, `soundfile`, `numpy`; model files `kokoro-v1.1-zh.int8.onnx` (114 MB) + `voices-v1.1-zh.bin` (54 MB).

## Global Constraints

- Only user config: `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`. TTS must require **no** extra config.
- The tool must work **offline after first run** (models cached; inference makes no network calls).
- `render_voiceover(narration, out_dir, voice, synth=synth_segment, probe=probe_duration, retries=2) -> list[float]` signature is a public seam — keep it working; tests inject `synth`/`probe`.
- Voice ids are Kokoro ids (`zf_*` female, `zm_*` male; 103 available). Default `zf_001`; speech rate `speed` (0.5–2.0). The `--voice` CLI flag stays but its default changes to `zf_001`; `speed` is not user-facing (exercised by tests only).
- Model download must go through a GitHub proxy: direct `github.com/.../releases/download` is unreachable here; `https://gh-proxy.com/<url>`, `https://ghfast.top/<url>`, `https://ghproxy.net/<url>` all work. Try them in order.
- Runtime Python: `.env-mamba/env/bin/python`. Test command: `.env-mamba/env/bin/python -m pytest -q` (currently 65 passed).
- Do NOT commit the ~168 MB model files; cache them under `~/.cache/kokoro-zh/` (override with env `KOKORO_MODEL_DIR`).

---

### Task 1: Lock the voice-engine seam with a test (TDD)

**Files:**
- Create: `video_agent/voice_engine.py`
- Test: `tests/test_voice_engine.py`

**Interfaces:**
- Produces: `synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str` — writes 24 kHz mono WAV to `out_path`, returns it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_voice_engine.py
from video_agent import voice_engine

def test_synthesize_defaults_and_signature():
    import inspect
    sig = inspect.signature(voice_engine.synthesize)
    assert list(sig.parameters) == ["text", "out_path", "voice", "speed"]
    assert sig.parameters["speed"].default == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_agent.voice_engine'`.

- [ ] **Step 3: Create the module with a stub**

```python
# video_agent/voice_engine.py
from __future__ import annotations


def synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str:
    raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add video_agent/voice_engine.py tests/test_voice_engine.py
git commit -m "test: lock voice_engine.synthesize seam"
```

---

### Task 2: Model cache path + filename constants

**Files:**
- Modify: `video_agent/voice_engine.py`
- Test: `tests/test_voice_engine.py`

**Interfaces:**
- Produces: `MODEL_FILES: dict[str, str]` (filename → GitHub release URL), `cache_dir() -> str` (honors `KOKORO_MODEL_DIR`, else `~/.cache/kokoro-zh`), `model_path(name) -> str`.

- [ ] **Step 1: Write the failing test**

```python
def test_cache_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path / "m"))
    assert voice_engine.cache_dir() == str(tmp_path / "m")

def test_model_files_cover_both_generators():
    assert set(voice_engine.MODEL_FILES) == {"kokoro-v1.1-zh.int8.onnx", "voices-v1.1-zh.bin"}
    for url in voice_engine.MODEL_FILES.values():
        assert url.startswith("https://")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: FAIL (`AttributeError: module ... has no attribute 'cache_dir'`).

- [ ] **Step 3: Implement**

```python
import os

_RELEASE = ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
            "model-files-v1.1/")
MODEL_FILES = {
    "kokoro-v1.1-zh.int8.onnx": _RELEASE + "kokoro-v1.1-zh.int8.onnx",
    "voices-v1.1-zh.bin": _RELEASE + "voices-v1.1-zh.bin",
}


def cache_dir() -> str:
    return os.environ.get("KOKORO_MODEL_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "kokoro-zh")


def model_path(name: str) -> str:
    return os.path.join(cache_dir(), name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: kokoro zh model cache paths"
```

---

### Task 3: Downloader with GitHub-proxy fallback

**Files:**
- Modify: `video_agent/voice_engine.py`
- Test: `tests/test_voice_engine.py`

**Interfaces:**
- Produces: `PROXIES: list[str]`, `ensure_models(progress=None) -> None` (downloads any missing file, trying each proxy in order; raises `RuntimeError` if all proxies fail).

- [ ] **Step 1: Write the failing test** (fake opener; no network)

```python
def test_ensure_models_uses_proxy_and_skips_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
    got = []
    def fake_urlretrieve(url, dst):
        got.append(url); open(dst, "wb").write(b"x" * 10)
    monkeypatch.setattr(voice_engine.urllib.request, "urlretrieve", fake_urlretrieve)
    voice_engine.ensure_models()
    assert len(got) == 2
    assert all(u.startswith(voice_engine.PROXIES[0]) for u in got)
    got.clear()
    voice_engine.ensure_models()          # files exist → no downloads
    assert got == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: FAIL (`no attribute 'ensure_models'`).

- [ ] **Step 3: Implement**

```python
import urllib.request

PROXIES = ["https://gh-proxy.com/", "https://ghfast.top/", "https://ghproxy.net/"]


def _download(name: str) -> str:
    dst = model_path(name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    os.makedirs(cache_dir(), exist_ok=True)
    last = None
    for pre in PROXIES:
        try:
            urllib.request.urlretrieve(pre + MODEL_FILES[name], dst)
            if os.path.getsize(dst) > 0:
                return dst
        except Exception as e:  # 试下一个代理
            last = e
    raise RuntimeError(f"下载模型 {name} 失败（所有镜像不可用）: {last}")


def ensure_models(progress=None) -> None:
    for name in MODEL_FILES:
        if progress:
            progress(name)
        _download(name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: kokoro zh model download with proxy fallback"
```

---

### Task 4: Lazy engine (load once) + real synthesis

**Files:**
- Modify: `video_agent/voice_engine.py`
- Test: `tests/test_voice_engine.py`

**Interfaces:**
- Consumes: `ensure_models`, `model_path`.
- Produces: `_load()` (returns `(Kokoro, g2p)`) and `_engine()` (cached); `synthesize` now real.

- [ ] **Step 1: Write the failing test** (engine injectable; no model needed in CI)

```python
def test_synthesize_uses_injected_engine(monkeypatch, tmp_path):
    import numpy as np
    class FakeSess:
        def run(self, _, inp):
            return [np.zeros(2400, np.float32)]  # 0.1s @ 24k
    class FakeTok:
        def tokenize(self, ph): return [1, 2, 3]
    class FakeK:
        sess = FakeSess(); tokenizer = FakeTok()
        def get_voice_style(self, v): return np.zeros((99, 256), np.float32)
    class FakeG2P:
        def __call__(self, t): return "ph"
    monkeypatch.setattr(voice_engine, "_load", lambda: (FakeK(), FakeG2P()))
    out = str(tmp_path / "a.wav")
    voice_engine.synthesize("你好", out, "zf_001")
    import soundfile as sf
    data, sr = sf.read(out)
    assert sr == 24000 and len(data) == 2400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py::test_synthesize_uses_injected_engine -q`
Expected: FAIL (`NotImplementedError`).

- [ ] **Step 3: Implement**

```python
import numpy as np

_ENGINE = None
SAMPLE_RATE = 24000


def _load():
    from kokoro_onnx import Kokoro
    from misaki import zh as mzh
    ensure_models()
    return (Kokoro(model_path("kokoro-v1.1-zh.int8.onnx"),
                   model_path("voices-v1.1-zh.bin")), mzh.ZHG2P())


def _engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _load()
    return _ENGINE


def synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str:
    import soundfile as sf
    kokoro, g2p = _engine()
    ids = kokoro.tokenizer.tokenize(g2p(text))
    style = kokoro.get_voice_style(voice)[len(ids)]
    inputs = {
        "input_ids": np.array([[0, *ids, 0]], dtype=np.int64),
        "style": np.array(style, dtype=np.float32),
        "speed": np.array([speed], dtype=np.float32),
    }
    audio = np.asarray(kokoro.sess.run(None, inputs)[0], dtype=np.float32).reshape(-1)
    sf.write(out_path, audio, SAMPLE_RATE, subtype="PCM_16")
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: offline Kokoro zh synthesis (direct ONNX, lazy load)"
```

---

### Task 5: Real end-to-end synthesis smoke (opt-in integration)

**Files:**
- Test: `tests/test_voice_engine.py` (add an opt-in test)

- [ ] **Step 1: Add an opt-in integration test**

```python
import os, pytest

@pytest.mark.skipif(not os.environ.get("KOKORO_SMOKE"),
                    reason="set KOKORO_SMOKE=1 to download models and run real synthesis")
def test_real_zh_synthesis(tmp_path):
    import soundfile as sf
    out = str(tmp_path / "t.wav")
    voice_engine.synthesize("大家好，这是一段本地离线语音合成的测试。", out, "zf_001")
    data, sr = sf.read(out)
    assert sr == 24000 and len(data) / sr > 1.0
```

- [ ] **Step 2: Run it for real (downloads ~168 MB once through gh-proxy)**

Run: `KOKORO_SMOKE=1 .env-mamba/env/bin/python -m pytest tests/test_voice_engine.py::test_real_zh_synthesis -q`
Expected: PASS; `ls ~/.cache/kokoro-zh` shows both files.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "test: opt-in real Kokoro zh synthesis smoke"
```

---

### Task 6: Swap the pipeline's synth backend + thread speed

**Files:**
- Modify: `video_agent/tts.py` (`synth_segment` → engine; `render_voiceover` gains `speed`)
- Modify: `video_agent/cli.py` (`_default_deps().voiceover`; `--voice` default)
- Test: `tests/test_tts.py`

**Interfaces:**
- Consumes: `voice_engine.synthesize`.
- Produces: `synth_segment(text, out_path, voice, speed=1.0)`; `render_voiceover(narration, out_dir, voice, synth=synth_segment, probe=probe_duration, retries=2, speed=1.0)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tts.py (add)
def test_render_voiceover_passes_speed(tmp_path):
    seen = {}
    def fake_synth(text, path, voice, speed=1.0):
        seen["speed"] = speed; open(path, "wb").write(b"\x00")
    durs = render_voiceover(NARR, str(tmp_path), "zf_001",
                            synth=fake_synth, probe=lambda p: 1.0, speed=1.3)
    assert seen["speed"] == 1.3 and durs == [1.0, 1.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_tts.py::test_render_voiceover_passes_speed -q`
Expected: FAIL (`unexpected keyword argument 'speed'`).

- [ ] **Step 3: Implement**

In `video_agent/tts.py`, replace `synth_segment`'s body and add `speed`:

```python
def synth_segment(text: str, out_path: str, voice: str, speed: float = 1.0) -> None:
    from .voice_engine import synthesize
    synthesize(text, out_path, voice, speed=speed)
```

Extend `render_voiceover`:

```python
def render_voiceover(narration: Narration, out_dir: str, voice: str,
                     synth=synth_segment, probe=probe_duration, retries: int = 2,
                     speed: float = 1.0) -> list[float]:
    os.makedirs(out_dir, exist_ok=True)
    durations = []
    for seg in narration.segments:
        path = os.path.join(out_dir, f"{seg.id:03d}.mp3")
        last = None
        ok = False
        for _ in range(retries + 1):
            try:
                synth(seg.text, path, voice, speed=speed)
                durations.append(probe(path))
                ok = True
                break
            except Exception as e:  # 声音失败 = 致命
                last = e
        if not ok:
            raise RuntimeError(f"第 {seg.id} 段配音失败: {last}")
    return durations
```

Update the existing fakes in `tests/test_tts.py` (`fake_synth`, `boom`) to accept `speed=1.0`.

In `video_agent/cli.py`: `_default_deps()._voiceover` stays `render_voiceover(narration, out_dir, voice)`; update `main()` `m.add_argument("--voice", default="zf_001")`.

- [ ] **Step 4: Run the full suite**

Run: `.env-mamba/env/bin/python -m pytest -q`
Expected: PASS (all, including updated fakes).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: route voiceover through offline engine; thread speed"
```

---

### Task 7: Dependencies + docs

**Files:**
- Modify: `requirements.txt` (drop `edge-tts`, add four packages)
- Modify: `README.md` (voice default, offline note, first-run download)

- [ ] **Step 1: Update requirements**

```
manim==0.22.0
kokoro-onnx==0.4.7
misaki[zh]==0.7.4
onnxruntime==1.31.0
soundfile
numpy
openai
pydantic>=2
pytest
```

- [ ] **Step 2: Update README**

Change the `--voice` example to `zf_001`; add: 首次运行会自动下载约 168MB 的中文语音模型（经 GitHub 镜像）缓存到 `~/.cache/kokoro-zh/`，之后完全离线。

- [ ] **Step 3: Verify a clean install resolves**

Run: `.env-mamba/env/bin/python -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt 2>&1 | tail -3`
Expected: `Successfully installed` or `already satisfied`.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "docs: offline TTS deps and first-run download note"
```

---

### Task 8: Full end-to-end smoke with real TTS

- [ ] **Step 1: Run the real pipeline** (needs a valid `.env`; downloads models once)

Run: `KOKORO_SMOKE=1 .env-mamba/env/bin/python -m video_agent make articles/sample.md --subtitle`
Expected: `output/sample/sample_916.mp4` + `sample_169.mp4` produced; AV-sync assert passes; audio is real Chinese narration, not silence.

- [ ] **Step 2: Verify audio non-silent and matches picture**

Run: `.env-mamba/env/bin/python -c "from video_agent.tts import probe_duration; print(probe_duration('output/sample/voice.mp3'))"`
Expected: positive duration ≈ total video length (assert_av_sync enforces ≤0.3s).

- [ ] **Step 3: Commit any test additions**

```bash
git add -A && git commit -m "test: end-to-end offline TTS smoke"
```

---

## Self-Review

**Spec coverage (user request: 换成本地离线 TTS):** engine chosen ✓ (Task 1–5), auto-download ✓ (Task 3), no new user config ✓, offline after first run ✓ (Task 4), pipeline integration ✓ (Task 6), deps/docs ✓ (Task 7), real 出片 ✓ (Task 8).

**Placeholder scan:** no TBD/TODO; every code step shows code.

**Type consistency:** `synthesize(text, out_path, voice, speed=1.0)` identical across Tasks 1/4/6; `render_voiceover(..., speed=1.0)` consistent; `model_path`/`cache_dir`/`ensure_models` names consistent.

**Known risks:** (a) `kokoro-onnx` wrapper dtype bug — bypassed by driving `sess.run` directly (verified manually on this box). (b) Model host blocked — proxy fallback (verified `gh-proxy.com`). (c) Existing `tests/test_tts.py` fakes take 3 args — Task 6 Step 3 updates them. (d) Output is WAV audio written to a `.mp3` path; ffmpeg concat/mux detects by content, but note in report if concat misbehaves.
