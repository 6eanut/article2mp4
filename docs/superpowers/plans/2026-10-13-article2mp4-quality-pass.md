# article2mp4 Quality Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four output-quality defects in the working `article2mp4` tool — vertical-video text truncation/overlap, stiff mid-sentence narration, unclear (too-quiet) speech, and the absence of subtitles / readable logs — without changing the product contract.

**Architecture:** Four independent changes. (1) A deterministic layout helper (`templates/_fit.py`) that scales each template's widest element to the safe frame width, plus a fast unit-test gate. (2) Punctuation-tiered TTS segmentation (never split at `、`; prefer real sentence ends) in `voice_engine.py`, plus one-pass ffmpeg `loudnorm` in `compose.py`. (3) Subtitles flipped to on-by-default via a `--no-subtitle` flag. (4) A tiny `progress.py` stage printer wired into `run_pipeline`, with Manim's progress bar/verbosity suppressed.

**Tech Stack:** Python 3.11+, Manim 0.22, ffmpeg/ffprobe, pytest. Interpreter: `.env-mamba/env/bin/python`.

## Global Constraints

- Product contract unchanged: **one Markdown in, one or two MP4 out**; user config is only `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; narration is the master clock (`shot_duration = audio + GAP`, `GAP = 0.4`).
- **Do NOT add a merge/combine step** — the user explicitly wants two separate MP4s.
- **No narration rate parameter** (user: "旁白语速不用调").
- **No multimodal / vision-model frame review** — the visual fix is geometric only (user-selected option).
- All code, comments, docstrings, log strings, prompts, and docs are **English**. Only these functional Chinese values stay: `video_agent/timing.py` `_CJK = re.compile(r"[\u4e00-\u9fff]")`, `video_agent/voice_engine.py` `_SENTENCE_SEP` (Chinese punctuation), and Chinese test fixtures in `tests/test_voice_engine.py` / `tests/test_timing.py`.
- Do **not** commit the ~168 MB Kokoro model files or `.env`.
- Local commits only; **push is NOT authorized**.
- Run everything with `.env-mamba/env/bin/python`. Baseline suite: **78 passed, 1 skipped** (the skip is the opt-in `KOKORO_SMOKE` real-synthesis test).

---

### Task 1: Layout fit helper

**Files:**
- Create: `video_agent/templates/_fit.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: `video_agent.render.DESIGN_FRAME_WIDTH` (= `14.222222222222221`).
- Produces:
  - `FRAME_SAFE_WIDTH: float`
  - `fit_width(mobj, max_width: float = FRAME_SAFE_WIDTH)` → the same mobject, scaled down to `max_width` **only if** `mobj.width > max_width`; returns `mobj` (chainable).
  - `fit_group(group, max_width: float = FRAME_SAFE_WIDTH)` → `VGroup` scaled uniformly so `group.width <= max_width`; returns `group`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layout.py`:
```python
from manim import Text, VGroup, DOWN
from video_agent.templates._fit import fit_width, fit_group, FRAME_SAFE_WIDTH


def test_fit_width_shrinks_oversized_text():
    t = Text("x" * 100)
    assert t.width > FRAME_SAFE_WIDTH
    assert fit_width(t) is t                       # chainable, same object
    assert t.width <= FRAME_SAFE_WIDTH + 1e-6


def test_fit_width_leaves_small_text_untouched():
    t = Text("hi")
    before = t.width
    fit_width(t)
    assert abs(t.width - before) < 1e-9


def test_fit_group_shrinks_group_uniformly():
    g = VGroup(Text("x" * 100), Text("x" * 60)).arrange(DOWN)
    assert g.width > FRAME_SAFE_WIDTH
    fit_group(g)
    assert g.width <= FRAME_SAFE_WIDTH + 1e-6
    # uniform scaling preserves the size ratio between the two texts
    assert abs(g[1].width / g[0].width - 60 / 100) < 0.02


def test_frame_safe_width_is_below_design_width():
    from video_agent.render import DESIGN_FRAME_WIDTH
    assert 0 < FRAME_SAFE_WIDTH < DESIGN_FRAME_WIDTH
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_layout.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_agent.templates._fit'`.

- [ ] **Step 3: Write minimal implementation**

Create `video_agent/templates/_fit.py`:
```python
"""Keep template text inside the visible frame.

Manim clips any mobject wider than the logical frame, and CJK strings quickly
exceed it in the narrow 9:16 frame. Templates call these helpers so an
over-long heading/line shrinks to fit instead of being cut off.
"""
from __future__ import annotations

from ..render import DESIGN_FRAME_WIDTH

# A small horizontal margin so glyph edges never touch the frame border.
FRAME_SAFE_WIDTH: float = DESIGN_FRAME_WIDTH - 0.6


def fit_width(mobj, max_width: float = FRAME_SAFE_WIDTH):
    """Scale ``mobj`` down to ``max_width`` if it is wider; otherwise no-op.

    Returns the same mobject so calls can be chained."""
    if mobj.width > max_width:
        mobj.scale_to_fit_width(max_width)
    return mobj


def fit_group(group, max_width: float = FRAME_SAFE_WIDTH):
    """Scale a whole group down uniformly so its width fits ``max_width``,
    preserving the relative sizes of its members."""
    if group.width > max_width:
        group.scale_to_fit_width(max_width)
    return group
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.env-mamba/env/bin/python -m pytest tests/test_layout.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add video_agent/templates/_fit.py tests/test_layout.py
git commit -m "feat: add layout fit helpers for template text"
```

---

### Task 2: Apply fit to all twelve templates

**Files:**
- Modify: `video_agent/templates/title.py`, `bullets.py`, `section.py`, `quote.py`, `compare.py`, `summary.py`, `steps.py`, `cycle.py`, `tree.py`, `grid.py`, `metric.py`, `closing.py`
- Test: `tests/test_layout.py` (append)

**Interfaces:**
- Consumes: `fit_width` / `fit_group` from Task 1 (`from ._fit import fit_width, fit_group`).
- Produces: every template's top-level `body`/`parts` `VGroup` is width-safe; no signature change (`render(props, duration, subtitle=None) -> list[Animation]` is unchanged).

> **Edit rule for every template:** import the helper, then ensure the final
> group returned to `entrance_hold` is wrapped in `fit_group(...)`. Each step
> below shows the exact `old`/`new`; internal `body` construction is shown only
> where it changes.

- [ ] **Step 1: Write the failing test (append to `tests/test_layout.py`)**

```python
import pytest
from video_agent.templates import render_scene

FILLER = "超长标题超长标题超长标题超长标题超长标题超长标题"
LONG = "这是一条非常非常长的要点内容用来测试竖屏下会不会被截断掉"

CASES = [
    ("title", {"title": FILLER, "subtitle": FILLER}, 3.0),
    ("section", {"index": 7, "heading": FILLER}, 3.0),
    ("bullets", {"heading": FILLER, "items": [LONG, LONG]}, 4.0),
    ("steps", {"heading": FILLER, "steps": [LONG, LONG, LONG], "done_index": 1}, 4.0),
    ("cycle", {"heading": FILLER, "nodes": [LONG, LONG, LONG]}, 4.0),
    ("tree", {"heading": FILLER, "root": LONG, "children": [[LONG, LONG], [LONG]]}, 4.0),
    ("compare", {"heading": FILLER,
                 "left": {"title": FILLER, "items": [LONG]},
                 "right": {"title": FILLER, "items": [LONG]}}, 4.0),
    ("grid", {"heading": FILLER, "cells": [{"label": LONG, "mark": "tick"},
                                           {"label": LONG, "mark": "cross"}]}, 3.0),
    ("metric", {"heading": FILLER, "value": 1234567, "unit": "%", "label": LONG}, 4.0),
    ("quote", {"text": FILLER + FILLER, "source": FILLER}, 3.0),
    ("summary", {"heading": FILLER, "items": [LONG, LONG, LONG]}, 3.5),
    ("closing", {"text": FILLER, "handle": FILLER}, 3.0),
]


@pytest.mark.parametrize("t,props,dur", CASES)
def test_template_content_fits_frame(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    for a in anims:
        m = getattr(a, "mobject", None)
        if m is not None:
            assert m.width <= FRAME_SAFE_WIDTH + 1e-6, f"{t} overflows: {m.width}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_layout.py -q`
Expected: FAIL on multiple templates (e.g. `title overflows`, `quote overflows`).

- [ ] **Step 3a: Edit `video_agent/templates/title.py`**

Replace the import line:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group
```
Then replace the final `return` line:
```python
    return entrance_hold(FadeIn(parts, shift=UP * 0.4), duration)
```
with:
```python
    fit_group(parts)
    return entrance_hold(FadeIn(parts, shift=UP * 0.4), duration)
```

- [ ] **Step 3b: Edit `video_agent/templates/section.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group
```
Replace:
```python
    body = VGroup(idx, h).arrange(DOWN, buff=0.25)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.3), duration)
```
with:
```python
    body = VGroup(idx, h).arrange(DOWN, buff=0.25)
    fit_group(body)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.3), duration)
```

- [ ] **Step 3c: Edit `video_agent/templates/bullets.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_width
```
Replace:
```python
    items = VGroup(*[
        Text(f"· {it}", font=FONT, font_size=30, color=ACCENT[i % len(ACCENT)])
        for i, it in enumerate(props["items"])
    ]).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    body = VGroup(h, items).arrange(DOWN, buff=0.5)
```
with:
```python
    items = VGroup(*[
        fit_width(Text(f"· {it}", font=FONT, font_size=30, color=ACCENT[i % len(ACCENT)]))
        for i, it in enumerate(props["items"])
    ]).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    body = VGroup(fit_width(h), items).arrange(DOWN, buff=0.5)
```

- [ ] **Step 3d: Edit `video_agent/templates/quote.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group, fit_width
```
Replace:
```python
    q = Text(f"“{props['text']}”", font=FONT, font_size=46, weight="BOLD", color=FG)
    parts = VGroup(q)
    if props.get("source"):
        s = Text(f"— {props['source']}", font=FONT, font_size=26, color=MUTED)
        parts = VGroup(q, s).arrange(DOWN, buff=0.4)
```
with:
```python
    q = fit_width(Text(f"“{props['text']}”", font=FONT, font_size=46, weight="BOLD", color=FG))
    parts = VGroup(q)
    if props.get("source"):
        s = fit_width(Text(f"— {props['source']}", font=FONT, font_size=26, color=MUTED))
        parts = VGroup(q, s).arrange(DOWN, buff=0.4)
    fit_group(parts)
```

- [ ] **Step 3e: Edit `video_agent/templates/compare.py`**

Replace the import line:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group, fit_width, FRAME_SAFE_WIDTH
```
Replace `_col`'s body:
```python
def _col(side, color):
    t = Text(side["title"], font=FONT, font_size=34, weight="BOLD", color=color)
    items = VGroup(*[Text(f"· {i}", font=FONT, font_size=26, color=FG) for i in side["items"]]
                   ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
    return VGroup(t, items).arrange(DOWN, buff=0.3)
```
with:
```python
def _col(side, color):
    # Two columns sit side by side, so each column may use only about half the
    # safe width.
    col_max = FRAME_SAFE_WIDTH / 2 - 0.3
    t = fit_width(Text(side["title"], font=FONT, font_size=34, weight="BOLD", color=color),
                  col_max)
    items = VGroup(*[fit_width(Text(f"· {i}", font=FONT, font_size=26, color=FG), col_max)
                     for i in side["items"]]
                   ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
    return VGroup(t, items).arrange(DOWN, buff=0.3)
```
Replace the final `return`:
```python
    body = VGroup(h, cols).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```
with:
```python
    body = VGroup(fit_width(h), cols).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
```

- [ ] **Step 3f: Edit `video_agent/templates/summary.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group, fit_width
```
Replace the final `return`:
```python
    body = VGroup(h, chips).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```
with:
```python
    body = VGroup(fit_width(h), chips).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
```

- [ ] **Step 3g: Edit `video_agent/templates/steps.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group
```
Replace the final `return`:
```python
    body = VGroup(h, line, dots, labels, marks).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```
with:
```python
    body = VGroup(h, line, dots, labels, marks).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
```

- [ ] **Step 3h: Edit `video_agent/templates/cycle.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group
```
Replace the final `return`:
```python
    body = VGroup(h, ring).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```
with:
```python
    body = VGroup(h, ring).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
```

- [ ] **Step 3i: Edit `video_agent/templates/tree.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group
```
Replace the final `return`:
```python
    body = VGroup(h, graph).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```
with:
```python
    body = VGroup(h, graph).arrange(DOWN, buff=0.6)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
```

- [ ] **Step 3j: Edit `video_agent/templates/grid.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group
```
Replace the final `return`:
```python
    body = VGroup(h, boxes).arrange(DOWN, buff=0.7)
    return entrance_hold(FadeIn(body), duration)
```
with:
```python
    body = VGroup(h, boxes).arrange(DOWN, buff=0.7)
    fit_group(body)
    return entrance_hold(FadeIn(body), duration)
```

- [ ] **Step 3k: Edit `video_agent/templates/metric.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group, fit_width
```
Replace the final `return`:
```python
    body = VGroup(h, val, lbl).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)
```
with:
```python
    body = VGroup(fit_width(h), fit_width(val), fit_width(lbl)).arrange(DOWN, buff=0.4)
    fit_group(body)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)
```

- [ ] **Step 3l: Edit `video_agent/templates/closing.py`**

Replace:
```python
from . import entrance_hold
```
with:
```python
from . import entrance_hold
from ._fit import fit_group, fit_width
```
Replace:
```python
    parts = VGroup(t)
    if props.get("handle"):
        h = Text(props["handle"], font=FONT, font_size=24, color=MUTED)
        parts = VGroup(t, h).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(parts), duration)
```
with:
```python
    parts = VGroup(fit_width(t))
    if props.get("handle"):
        h = fit_width(Text(props["handle"], font=FONT, font_size=24, color=MUTED))
        parts = VGroup(t, h).arrange(DOWN, buff=0.4)
    fit_group(parts)
    return entrance_hold(FadeIn(parts), duration)
```

- [ ] **Step 4: Run the layout test, then the full template tests**

Run: `.env-mamba/env/bin/python -m pytest tests/test_layout.py -q`
Expected: PASS (16 passed).
Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_core.py tests/test_templates_shapes.py tests/test_templates_text.py -q`
Expected: PASS (existing duration/registration tests unaffected).

- [ ] **Step 5: Commit**

```bash
git add video_agent/templates/*.py tests/test_layout.py
git commit -m "feat: keep all twelve templates inside the frame width"
```

---

### Task 3: Tiered TTS segmentation (never split at `、`)

**Files:**
- Modify: `video_agent/voice_engine.py:73-121`
- Test: `tests/test_voice_engine.py` (append)

**Interfaces:**
- Consumes: existing `_MAX_TOKENS`, `_hard_split`.
- Produces: `_HARD_SEP`, `_SOFT_SEP`, `_SENTENCE_SEP` (= hard + soft, kept for
  callers), `_split_sentences(text) -> list[str]` (now splits only at hard ends),
  `_soft_split(text, count_tokens, max_tokens) -> list[str]`, and `_chunk(...)`
  that packs at hard ends first, falls back to soft ends when the budget forces
  it, and never splits at `、`.

- [ ] **Step 1: Write the failing test (append to `tests/test_voice_engine.py`)**

```python
def test_enumeration_comma_never_splits_chunk():
    """`、` is an enumeration comma: it must not create a chunk boundary even
    when the text is long, so a listed phrase is spoken as one clause group."""
    # count_tokens = len → max_tokens counts characters (5 chars per item).
    text = "苹果、香蕉、西瓜、菠萝。"          # 12 chars
    chunks = voice_engine._chunk(text, len, max_tokens=11)  # must split somewhere
    assert len(chunks) > 1
    # The only legal break is at the hard end `。`; `、` must not start a chunk.
    for c in chunks:
        assert not c.startswith("、")
    assert "".join(chunks) == text


def test_split_sentences_only_hard_ends_single_turn():
    """A sentence with soft punctuation stays in ONE turn until a real end."""
    turns = voice_engine._split_sentences("先做甲；再做乙、丙和丁。然后结束。")
    assert turns == ["先做甲；再做乙、丙和丁。", "然后结束。"]


def test_chunk_splits_at_boundary_never_mid_list():
    text = "甲甲甲；乙乙乙。丙丙丙。"
    chunks = voice_engine._chunk(text, len, max_tokens=8)
    assert "".join(chunks) == text
    assert all(len(c) <= 8 for c in chunks)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q -k "enumeration or split_sentences or mid_list"`
Expected: FAIL — `_split_sentences` currently splits at `；`/`、`.

- [ ] **Step 3: Replace the segmentation code**

In `video_agent/voice_engine.py`, replace lines 73-121 (the `_SENTENCE_SEP`
definition, `_chunk`, and `_split_sentences`) with:
```python
# Punctuation that denotes a sentence end (a full pause may follow). The
# enumeration comma `、` and the halfwidth comma are deliberately NOT here —
# splitting at them chops lists and restarts prosody mid-sentence.
_HARD_SEP = "。！？!?…\n"
# Clause punctuation: used only as a split point when the token budget forces it.
_SOFT_SEP = "；;"
# Kept for backwards compatibility with callers/tests that reference it.
_SENTENCE_SEP = _HARD_SEP + _SOFT_SEP


def _chunk(text: str, count_tokens, max_tokens: int = _MAX_TOKENS) -> list[str]:
    """Split ``text`` into pieces whose ``count_tokens`` never exceeds ``max_tokens``.

    Splits happen only at sentence ends (``_HARD_SEP``) and — when the budget
    forces it — at clause punctuation (``_SOFT_SEP``). The enumeration comma ``、``
    is never a split point. A single piece longer than the limit is hard-split by
    characters.
    """
    if not text:
        return [""]
    if count_tokens(text) <= max_tokens:
        return [text]

    units = _split_sentences(text)
    chunks: list[str] = []
    buf = ""
    for unit in units:
        if count_tokens(unit) <= max_tokens:
            if buf and count_tokens(buf + unit) > max_tokens:
                chunks.append(buf)
                buf = unit
            else:
                buf += unit
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            for piece in _soft_split(unit):
                if count_tokens(piece) <= max_tokens:
                    if buf and count_tokens(buf + piece) > max_tokens:
                        chunks.append(buf)
                        buf = piece
                    else:
                        buf += piece
                else:
                    if buf:
                        chunks.append(buf)
                        buf = ""
                    chunks.extend(_hard_split(piece, count_tokens, max_tokens))
    if buf:
        chunks.append(buf)
    return chunks


def _soft_split(text: str) -> list[str]:
    """Break a too-long sentence at clause punctuation (``_SOFT_SEP``), keeping
    the punctuation attached. Returns ``[text]`` unchanged when there is no break."""
    parts: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in _SOFT_SEP:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    return parts or [text]


def _split_sentences(text: str) -> list[str]:
    """Split on hard sentence ends only, keeping the punctuation attached."""
    parts: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in _HARD_SEP:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    return parts
```

- [ ] **Step 4: Run the voice-engine tests**

Run: `.env-mamba/env/bin/python -m pytest tests/test_voice_engine.py -q`
Expected: PASS (all existing chunking tests plus the three new ones; the existing
`test_chunk_long_text_multiple_chunks_preserves_text` still holds because `。`
is a hard end).

- [ ] **Step 5: Commit**

```bash
git add video_agent/voice_engine.py tests/test_voice_engine.py
git commit -m "fix: never split TTS chunks at the enumeration comma"
```

---

### Task 4: Loudness normalization in compose

**Files:**
- Modify: `video_agent/compose.py:19-38` (the `concat_voiceover` function)
- Test: `tests/test_compose.py` (append)

**Interfaces:**
- Consumes: `ffmpeg_path()`.
- Produces: `concat_voiceover(audio_dir, ids, out_path, gap=0.0, loudnorm=True)` —
  when `loudnorm` is true the output voiceover is normalized to
  `I=-14 LUFS, TP=-1.5 dBTP, LRA=11`. Additive keyword arg (default keeps existing
  callers working).

- [ ] **Step 1: Write the failing test (append to `tests/test_compose.py`)**

```python
def test_concat_voiceover_applies_loudnorm(monkeypatch, tmp_path):
    import video_agent.compose as c
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    (tmp_path / "000.mp3").write_bytes(b"x")
    c.concat_voiceover(str(tmp_path), [0], "out.mp3", gap=0.4)
    joined = " ".join(seen["argv"])
    assert "loudnorm" in joined and "I=-14" in joined


def test_concat_voiceover_can_skip_loudnorm(monkeypatch, tmp_path):
    import video_agent.compose as c
    seen = {}
    monkeypatch.setattr(c, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(c.subprocess, "run", lambda *a, **k: seen.update(argv=a[0]))
    (tmp_path / "000.mp3").write_bytes(b"x")
    c.concat_voiceover(str(tmp_path), [0], "out.mp3", gap=0.4, loudnorm=False)
    assert "loudnorm" not in " ".join(seen["argv"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_compose.py -q -k loudnorm`
Expected: FAIL with `TypeError: concat_voiceover() got an unexpected keyword argument 'loudnorm'`.

- [ ] **Step 3: Implement**

In `video_agent/compose.py`, add a module constant after the imports:
```python
# EBU R128 loudness target for the web/streaming reference level, applied to the
# concatenated voiceover: -14 LUFS integrated with a -1.5 dBTP ceiling.
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"
```
Replace the whole `concat_voiceover` function with:
```python
def concat_voiceover(audio_dir, ids, out_path, gap: float = 0.0,
                     loudnorm: bool = True) -> str:
    ff = ffmpeg_path()
    inputs = []
    for i in ids:
        inputs += ["-i", os.path.join(audio_dir, f"{i:03d}.mp3")]
    if gap and gap > 0:
        filt = build_concat_filter(len(ids), gap)
        if loudnorm:  # normalize loudness after concatenation
            filt = filt.replace("[out]", f"[pre];[pre]{LOUDNORM}[out]")
        subprocess.run([ff, "-y", *inputs, "-filter_complex", filt,
                        "-map", "[out]", out_path], check=True, capture_output=True)
    else:
        lst = out_path + ".txt"
        try:
            with open(lst, "w", encoding="utf-8") as f:
                f.write(build_concat_file(ids, audio_dir))
            af = ["-af", LOUDNORM] if loudnorm else ["-c", "copy"]
            subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                            *af, out_path], check=True, capture_output=True)
        finally:
            if os.path.exists(lst):
                os.remove(lst)
    return out_path
```

- [ ] **Step 4: Run the compose tests**

Run: `.env-mamba/env/bin/python -m pytest tests/test_compose.py -q`
Expected: PASS (existing gap/trim tests plus the two new ones). Note the existing
`test_build_concat_filter_inserts_gap` tests `build_concat_filter` directly and is
unaffected.

- [ ] **Step 5: Commit**

```bash
git add video_agent/compose.py tests/test_compose.py
git commit -m "feat: normalize voiceover loudness to -14 LUFS"
```

---

### Task 5: Progress logger

**Files:**
- Create: `video_agent/progress.py`
- Test: `tests/test_progress.py`

**Interfaces:**
- Produces: `stage(n: int, total: int, label: str, detail: str = "") -> None`
  (prints `[n/total] label` or `[n/total] label … detail`), `detail(msg: str) -> None`
  (prints `  · msg`), and a module flag `ENABLED: bool = True` that silences all output.

- [ ] **Step 1: Write the failing test**

Create `tests/test_progress.py`:
```python
from video_agent import progress


def test_stage_prints_numbered_line(capsys):
    progress.stage(2, 6, "Voiceover", "3 segments")
    assert capsys.readouterr().out.strip() == "[2/6] Voiceover … 3 segments"


def test_stage_without_detail_has_no_trailing_dots(capsys):
    progress.stage(1, 6, "Narration")
    assert capsys.readouterr().out.strip() == "[1/6] Narration"


def test_detail_is_indented(capsys):
    progress.detail("wrote narration.json")
    assert capsys.readouterr().out.strip() == "· wrote narration.json"


def test_disabled_prints_nothing(capsys):
    progress.ENABLED = False
    try:
        progress.stage(1, 6, "Narration")
        progress.detail("x")
    finally:
        progress.ENABLED = True
    assert capsys.readouterr().out == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_progress.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_agent.progress'`.

- [ ] **Step 3: Implement**

Create `video_agent/progress.py`:
```python
"""Human-readable progress lines for the pipeline.

Emits one numbered line per stage ("[2/6] Voiceover … 12 segments") plus optional
indented detail lines, so the run is legible without Manim's log spew. Output can
be silenced by setting ``ENABLED = False``.
"""
from __future__ import annotations

ENABLED: bool = True


def stage(n: int, total: int, label: str, detail: str = "") -> None:
    """Print a stage header like ``[2/6] Voiceover … 12 segments``."""
    if not ENABLED:
        return
    line = f"[{n}/{total}] {label}"
    if detail:
        line += f" … {detail}"
    print(line, flush=True)


def detail(msg: str) -> None:
    """Print an indented detail line under the current stage."""
    if not ENABLED:
        return
    print(f"  · {msg}", flush=True)
```

- [ ] **Step 4: Run the test**

Run: `.env-mamba/env/bin/python -m pytest tests/test_progress.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add video_agent/progress.py tests/test_progress.py
git commit -m "feat: add human-readable stage progress logger"
```

---

### Task 6: Wire progress + subtitle default into the CLI, suppress Manim noise

**Files:**
- Modify: `video_agent/cli.py`
- Modify: `video_agent/render.py:64-104`
- Test: `tests/test_cli.py` (append)

**Interfaces:**
- Consumes: `video_agent.progress.stage` / `detail`/`ENABLED` (Task 5).
- Produces:
  - `render_video(spec, durations, aspect, out_dir, subtitle=False, subtitles=None, progress=None)`
    — `progress` is `callable(done: int, total: int)` called once per scene before it plays.
  - `run_pipeline(..., deps=None, progress_enabled=True)` — additive kwarg.
  - `build_parser() -> argparse.ArgumentParser`; CLI `--subtitle/--no-subtitle` defaulting to **on**.

- [ ] **Step 1: Write the failing test (append to `tests/test_cli.py`)**

```python
def test_run_pipeline_reports_progress(tmp_path, capsys):
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    deps = dict(
        script_gen=lambda md, client: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub, subs=None, progress=None: f"{o}/silent_{asp}.mp4",
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=lambda **k: f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4",
        client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                 subtitle=True, voiceover_only=False, out_dir=str(out), deps=deps)
    out_text = capsys.readouterr().out
    assert "[1/6] Narration" in out_text
    assert "[6/6] Compose" in out_text


def test_default_subtitle_option_is_on():
    from video_agent.cli import build_parser
    assert build_parser().parse_args(["make", "a.md"]).subtitle is True
    assert build_parser().parse_args(["make", "a.md", "--no-subtitle"]).subtitle is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.env-mamba/env/bin/python -m pytest tests/test_cli.py -q -k "progress or default_subtitle"`
Expected: FAIL (`build_parser` undefined; no progress output).

- [ ] **Step 3a: Edit `video_agent/render.py`**

Change the `ExplainSpec` class body — add two class attributes and report progress:
```python
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
```
Change `render_video`'s signature and add suppression + callback wiring:
```python
def render_video(spec, durations, aspect, out_dir, subtitle=False, subtitles=None,
                 progress=None):
    apply_manim_config()
    # Mute Manim's startup banner, per-animation INFO lines, and tqdm bar so the
    # pipeline's own progress output is the primary, readable signal.
    config.verbosity = "ERROR"
    config.progress_bar = "none"
    w, h = CANVAS[aspect]
```
and near the end, before `scene = ExplainSpec()`:
```python
    ExplainSpec.PROGRESS = progress
    ExplainSpec._DONE = 0
```

- [ ] **Step 3b: Edit `video_agent/cli.py`**

Add the import:
```python
from . import progress as prog
```
Change `_default_deps`'s `_render` to forward the callback:
```python
    def _render(spec, durations, aspect, out_dir, subtitle, subtitles=None, progress=None):
        return render_video(spec, durations, aspect, out_dir,
                            subtitle=subtitle, subtitles=subtitles, progress=progress)
```
Replace `main()` with a `build_parser()` + `main()` pair:
```python
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
```
In `run_pipeline`, add `progress_enabled=True` to the signature and stage calls
(only the changed lines shown; keep the existing body otherwise):
```python
def run_pipeline(article_path, aspect, max_seconds, voice, subtitle,
                 voiceover_only, out_dir=None, deps=None, progress_enabled=True):
    deps = deps or _default_deps()
    prog.ENABLED = progress_enabled
    TOTAL = 6
    ...
    prog.stage(1, TOTAL, "Narration")
    narration = deps["script_gen"](article, client)
    prog.detail(f"{len(narration.segments)} segments")
    ...
    prog.stage(2, TOTAL, "Scene spec")
    spec = deps["scene_gen"](narration, client)
    prog.detail(f"{len(spec.scenes)} scenes")
    ...
    prog.stage(3, TOTAL, "Voiceover")
    durations = deps["voiceover"](narration, audio_dir, voice)
    prog.detail(f"{len(durations)} audio files")
    ...
    prog.stage(4, TOTAL, "Align")
    shot = align_durations(durations)
    ...
    for asp in aspects:
        prog.stage(5, TOTAL, f"Render ({asp})")
        video = deps["render"](json.loads(spec.model_dump_json()), shot, asp,
                               out_dir, subtitle, subtitles,
                               progress=lambda done, n: prog.detail(f"scene {done + 1}/{n}"))
        prog.stage(6, TOTAL, f"Compose ({asp})")
        result[asp] = deps["compose"](
            video=video, audio_dir=audio_dir, narration=narration, out_dir=out_dir,
            name=name, aspect=asp, bgm=bgm, trim_to=trim_to,
        )
        prog.detail(os.path.basename(result[asp]))
    return {"video": result[aspect] if aspect in result else next(iter(result.values())),
            "all": result}
```
Note: Scene spec's real work runs **after** Voiceover in the existing body,
because scene generation consumes the narration that `--max-seconds` may have
trimmed, and trimming needs the voiceover durations. Keep that execution order,
and number each stage by its **print position** (Narration=1, Voiceover=2,
Scene spec=3, Align=4, Render=5, Compose=6) so the counter is monotonic and
matches the reader's sense of "how far along are we".

- [ ] **Step 4: Run the CLI tests, then the whole suite**

Run: `.env-mamba/env/bin/python -m pytest tests/test_cli.py -q`
Expected: PASS (existing tests pass `subtitle=` explicitly, so the flag default
does not affect them; plus 2 new tests).
Run: `.env-mamba/env/bin/python -m pytest -q`
Expected: baseline + new tests all green (was 78 passed, 1 skipped).

- [ ] **Step 5: Commit**

```bash
git add video_agent/cli.py video_agent/render.py tests/test_cli.py
git commit -m "feat: on-by-default subtitles and readable stage progress"
```

---

### Task 7: Docs — subtitle default, tone, changelog

**Files:**
- Modify: `README.md:29`, `README.md:87`
- Modify: `docs/DESIGN.md:84-90`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `CHANGELOG.md`

**Interfaces:** documentation only; no code.

- [ ] **Step 1: Update `README.md`**

At line 29, change:
```markdown
- **Optional subtitles and background music.**
```
to:
```markdown
- **Subtitles on by default** (disable with `--no-subtitle`) **and background music.**
```
At line 87, change the option row:
```markdown
| `--subtitle` | Burn the narration in as subtitles | off |
```
to:
```markdown
| `--subtitle` / `--no-subtitle` | Burn the narration in as subtitles | on |
```

- [ ] **Step 2: Update `docs/DESIGN.md`**

Replace the "Subtitles" paragraph (lines 84-90) with:
```markdown
### Subtitles

Subtitles are a **toggleable overlay, on by default**, disabled with
`--no-subtitle`. The content is the narration sentence for that shot, shown in
sync with it. It is a **cross-cutting template capability** shared by all twelve
types, not a feature of one type. Motivation: short vertical videos are widely
watched on mute, so on-screen text is close to standard — so it ships on.
```

- [ ] **Step 3: Update `docs/ARCHITECTURE.md`**

In the `### render.py` paragraph, append: "Every template scales its widest
element to the safe frame width (`templates/_fit.py`) so long CJK text is never
clipped in the narrow 9:16 frame."
In the `### compose.py` paragraph, append: "`concat_voiceover()` applies ffmpeg
`loudnorm` (-14 LUFS) so the narration is loud and clear on playback."
In the module map, add under `video_agent/`:
```
  progress.py       human-readable per-stage progress lines
```

- [ ] **Step 4: Update `CHANGELOG.md`**

Under `## [Unreleased]`, add:
```markdown
### Changed

- Subtitles now default to **on** (`--no-subtitle` disables them).
- Template text scales to fit the frame, preventing clipped or overlapping text
  in the 9:16 output.

### Fixed

- Narration no longer breaks mid-sentence at enumeration commas (`、`).
- Voiceover loudness normalized to -14 LUFS for clearer playback.

### Added

- Human-readable per-stage progress output; Manim's progress bar is muted.
```

- [ ] **Step 5: Commit**

```bash
git add README.md docs/DESIGN.md docs/ARCHITECTURE.md CHANGELOG.md
git commit -m "docs: reflect subtitle default, layout fit, loudness, and progress"
```

---

### Task 8: End-to-end smoke verification

**Files:** none (verification only; uses `examples/demo.md`).

- [ ] **Step 1: Run the real pipeline with subtitles on (default)**

Run:
```bash
.env-mamba/env/bin/python -m video_agent make examples/demo.md
```
Expected: readable `[1/6] … [6/6]` progress lines; two files written —
`output/demo/demo_916.mp4` and `output/demo/demo_169.mp4`; no A/V-sync assertion
error.

- [ ] **Step 2: Confirm both outputs exist and probe their durations**

Run:
```bash
.env-mamba/env/bin/python - <<'PY'
from video_agent.tts import probe_duration
import os
for a in ("916", "169"):
    p = f"output/demo/demo_{a}.mp4"
    print(a, os.path.exists(p), round(probe_duration(p), 2))
PY
```
Expected: `916 True <dur>` and `169 True <dur>`, durations within ~0.3 s of each
other (same narration).

- [ ] **Step 3: Spot-check a mid frame for no clipping and a caption band**

Run:
```bash
mkdir -p /tmp/a2mp4_smoke
.env-mamba/env/bin/ffmpeg -y -loglevel error -ss 3 -i output/demo/demo_916.mp4 -frames:v 1 /tmp/a2mp4_smoke/f.png
```
Then read `/tmp/a2mp4_smoke/f.png` and confirm: template text is fully visible
(nothing cut at the frame edges) and a narration line sits near the bottom.

- [ ] **Step 4: Confirm the suite is green and key facts hold**

Run:
```bash
.env-mamba/env/bin/python -m pytest -q
git grep -c 'loudnorm' video_agent/compose.py
.env-mamba/env/bin/python -c "import tomllib;tomllib.load(open('pyproject.toml','rb'))" && echo pyproject-ok
```
Expected: suite green; `compose.py` shows the `loudnorm` constant; pyproject parses.

- [ ] **Step 5: Commit (only if the smoke test required a fix)**

```bash
git add -A
git commit -m "test: verify end-to-end quality-pass output" || echo "nothing to commit"
```

---

## Self-Review

**Spec coverage:**
- ① Layout truncation/overlap → Tasks 1–2 (fit helpers + all twelve templates + geometric gate). ✓
- ② Mid-sentence narration breaks → Task 3 (`、` never splits; hard-first packing). ✓
- ③ Unclear/quiet speech → Task 4 (`loudnorm` -14 LUFS). ✓
- ④ Subtitles → Task 6 (on-by-default + `--no-subtitle`) + Task 7 docs. ✓
- ⑤ Readable logs → Tasks 5–6 (`progress.py` + Manim muting + per-scene lines). ✓
- Docs + changelog → Task 7. ✓
- Deterministic verification → Task 8. ✓

**Placeholder scan:** no "TBD"/"handle errors"/"write tests for the above"; every
code step shows the code; every run step gives a command and expected result.

**Type consistency:** `fit_width(mobj, max_width=FRAME_SAFE_WIDTH)`,
`fit_group(group, max_width=FRAME_SAFE_WIDTH)`, `FRAME_SAFE_WIDTH`,
`concat_voiceover(..., loudnorm=True)`, `LOUDNORM`,
`progress.stage(n, total, label, detail)`, `progress.detail(msg)`,
`progress.ENABLED`, `render_video(..., progress=None)`, `build_parser()` are used
consistently across tasks.

**Known soft spot to watch during execution:** the per-scene `prog.detail("scene
i/N")` line prints once per scene (≈30+ lines per aspect). If that proves noisy in
the real run (Task 8 Step 1), collapse it to one line per aspect — cosmetic only,
no requirement depends on it.
