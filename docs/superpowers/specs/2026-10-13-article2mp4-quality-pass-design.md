# article2mp4 Quality Pass — Design

**Date:** 2026-10-13
**Status:** approved (pending plan)
**Scope:** four independent fixes to an already-working tool. No change to the
product contract (one Markdown in, one or two MP4 out; config is only
`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`; narration is the master clock).

## Problem statement

The tool is verified end-to-end, but four output-quality defects remain. Each was
root-caused by direct inspection/measurement, not guessed:

| # | Symptom (user) | Root cause (verified) |
|---|---|---|
| ① | Vertical video truncates or overlaps text | No template calls `scale_to_fit_width()`. The logical frame width is fixed at `DESIGN_FRAME_WIDTH = 14.222…`; single-line `Text` wider than that is clipped. `render.py:53` scales only the subtitle. |
| ② | Narration breathes in the middle of a sentence; sounds stiff | `voice_engine.py:74` `_SENTENCE_SEP = "。！？；、\n"` treats the enumeration comma `、` and semicolon `；` as **sentence ends**, so `苹果、香蕉、西瓜` is hard-split. Each split also restarts prosody after a 0.05 s gap (`voice_engine.py:175-181`). |
| ③ | Speech is unclear / muffled | Measured overall loudness ≈ **−26 LUFS** vs the streaming target of **−14 LUFS** — a ~12 dB shortfall. Quantisation was ruled out experimentally: int8 (114 MB) and fp16 (163 MB) outputs are essentially identical. ffmpeg `loudnorm` is available. |
| ④ | No subtitles appear | Captions **do** render — a one-shot `--subtitle` render shows a text band at y≈1846 in a 1080×1920 frame. The real cause is that subtitles are **off by default** (`--subtitle` required). |
| ⑤ | Runtime logs are ugly | `cli.py` emits a single `print("Done:", res)`; all other output is third-party Manim `tqdm` / `INFO` / banner noise. No per-stage progress. |

**Decision (user):** the visual fix is **deterministic layout validation**, not
multimodal adversarial review. Rationale: text overflow is a pure *geometry*
problem that a geometric assertion captures with 100% coverage, at zero model cost
and no network dependency; a vision-model revision loop would be expensive,
non-convergent, and would violate the tool's offline/deterministic character.

## Change 1 — Deterministic layout adaptation (visual truncation/overlap)

**Principle:** every template must guarantee its widest element fits the safe
frame width, for any input length, in both aspects.

- Add `video_agent/templates/_fit.py`:
  - `FRAME_SAFE_WIDTH` derived from `render.frame_dimensions` with a small margin
    (`DESIGN_FRAME_WIDTH − margin`).
  - `fit_width(mobj, max_width=FRAME_SAFE_WIDTH)` → `mobj.scale_to_fit_width(max_width)`
    only when `mobj.width > max_width`; returns `mobj` (chainable, idempotent).
  - `fit_group(group, max_width=…)` → scale the whole `VGroup` uniformly by the
    worst offender, so relative font sizes inside a group are preserved (headings
    and body shrink together rather than one collapsing).
- Apply in all **12 templates** to every element that can touch the frame edge:
  template headings, bullet lines, quote text, metric value/label, tree/cycle/grid
  node labels, compare column text, closing handle. Long CJK strings are the
  stress case; Latin runs of the same logical length are shorter but must also fit.
- `render.py::_caption` reuses `fit_width` for consistency (behaviour unchanged).

**Explicitly out of scope:** auto line-wrapping. Scaling to fit is simpler and
sufficient; wrapping would push elements past the block budget and complicate the
`entrance_hold` timing model.

## Change 2 — Punctuation-tiered segmentation + loudness normalisation (speech)

**2a. Tiered sentence boundaries** (`voice_engine.py`):

- **Hard boundary** (end of sentence; may add a short pause): `。！？!?…` and newline.
- **Soft boundary** (clause; split only when the token budget forces it, and
  **with no large inter-chunk rest**): `；;`. The enumeration comma `、` and the
  halfwidth comma `,` are **never** split points.
- `_split_sentences` keeps all punctuation attached and classifies each split as
  hard or soft. When packing chunks, prefer breaking at a hard boundary; fall back
  to a soft boundary only when packing at hard boundaries would exceed
  `_MAX_TOKENS`. Never split at `、`.
- Result: a sentence's clauses stay in one synthesis call whenever they fit, so
  prosody is not restarted mid-sentence.

**2b. Loudness normalisation** (compose stage, not synthesis):

- In `compose.py`, apply ffmpeg `loudnorm` (`I=-14, TP=-1.5, LRA=11`) to the
  concatenated voiceover before muxing. One-pass, additive, reversible; no
  re-synthesis and no change to on-disk per-segment WAVs.

Rationale for keeping 2b at compose: it is a single, central, tunable step and
does not perturb the deterministic per-segment audio contract.

## Change 3 — Subtitles on by default (captions)

- Flip the CLI default: subtitles **on**; add `--no-subtitle` to disable.
  (`--subtitle` retained as a no-op alias for back-compat with prior invocations
  and docs.)
- Readability: raise caption font size, keep it clear of the bottom edge, and
  route long lines through `fit_width`. Captions already render today; this change
  makes them visible by default and legible.
- Update `docs/DESIGN.md` (currently says "off by default") and the README CLI
  reference to reflect the new default.

## Change 4 — Human-readable stage progress (logs)

- Add `video_agent/progress.py`: a tiny `stage(n, total, label)` / `detail(msg)`
  printer that emits lines like `[1/6] Narration … 12 segments`,
  `[5/6] Render (916) … animation 3/34`, `[6/6] Compose … <name>_916.mp4`.
- `run_pipeline` drives it per stage; `_default_deps` threads a per-shot render
  callback so the render stage reports `i/N` instead of Manim's tqdm.
- Suppress Manim `tqdm` / `INFO` / startup banner (via `config` logging level),
  so the human-facing progress is the primary output.
- Keep the final `result` dict returned from `main()` (e.g. `--json` verbosity
  unaffected). Graceful degradation: if suppression API differs across Manim
  versions, fall back to leaving Manim output as-is — progress lines still print.

## Files touched

- **New:** `video_agent/templates/_fit.py`, `video_agent/progress.py`,
  `tests/test_layout.py`, `tests/test_progress.py` (thin),
  `docs/superpowers/specs/2026-10-13-article2mp4-quality-pass-design.md` (this).
- **Modified:** all 12 `video_agent/templates/*.py`; `video_agent/render.py`
  (caption fit + shot callback); `video_agent/voice_engine.py` (tiered split);
  `video_agent/compose.py` (loudnorm); `video_agent/cli.py` (subtitle default,
  progress wiring); `docs/DESIGN.md`, `README.md` (subtitle default).

## Testing (beyond the existing suite)

- `tests/test_layout.py` — for each of the 12 types, render into a 9:16 frame
  with an oversized CJK sample and assert every top-level element's
  `width <= FRAME_SAFE_WIDTH`. Fast (render one animation each), offline,
  deterministic. This is the geometric anti-truncation gate.
- `tests/test_voice_engine.py` — add: `、` does **not** create a chunk boundary;
  a long enumeration that fits stays in one chunk; clauses split only at a soft
  boundary when the budget forces it.
- `tests/test_compose.py` — assert the voiceover path passes through `loudnorm`
  (filter present in the ffmpeg command / measurable integrated loudness increase).
- Existing suite must stay green (currently **78 passed, 1 skipped**).

## Risks / notes

- **Template scaling changes layout, not semantics** — but existing per-template
  unit renders may assert exact pixel sizes; they will need the same `fit_width`
  tolerance. Verified case-by-case.
- **Loudness normalisation can reveal clipping** in already-hot segments; `TP=-1.5`
  guards the true peak, and the A/V-sync assertion is unaffected (duration is
  preserved by `loudnorm`).
- **Turning subtitles on by default** changes the default visual output; called
  out here so it is a conscious, documented decision (user has repeatedly asked
  for subtitles).
- **No merge feature** is added — the user explicitly wants two separate MP4s.

## Out of scope (YAGNI)

- Multimodal (vision-model) frame review and auto-revision.
- A narration rate parameter.
- Auto line-wrapping of template text.
- Merging the two aspect outputs into one file.
