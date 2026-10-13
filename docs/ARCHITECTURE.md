# Architecture

This document describes how `article2mp4` is put together: the pipeline stages,
the modules that implement them, and the data contracts that connect them.

## Overview

The tool is a **scene compiler**. It reads one Markdown article and emits one or
two MP4 files, in six stages:

```
article.md
   │
   ▼
① Narration     LLM call #1      article → spoken script, split into N segments
   │                             produces narration.json   [{id, text}, ...]
   ▼
② Scene spec    LLM call #2      narration + template catalogue → scene JSON
   │                             produces scene_spec.json   [{id, narration_id, type, props}, ...]
   │                             (schema-validated, retried, with a fallback)
   ▼
③ Voiceover     offline TTS      one audio file per segment; ffprobe reads each real duration
   │                             produces audio/NNN.mp3 + durations
   ▼
④ Alignment     pure Python      write each duration back onto its shot
   │                             (no model calls — deterministic)
   ▼
⑤ Render        Manim            dispatch each shot's `type` to a template; each template
   │                             "eats" its target seconds and distributes entrance vs. hold
   │                             produces the silent 9:16 and 16:9 videos
   ▼
⑥ Compose       ffmpeg           silent video + concatenated narration + built-in BGM
                                 (+ optional subtitles) → output/<name>/<name>_916.mp4, _169.mp4
```

**The model appears only in stages ① and ②.** Everything from ③ onward is
deterministic computation: reproducible, offline, and free.

Two consequences are worth calling out:

- **Stage ① fixes the shot count.** The narration is split into N segments, and
  each segment becomes exactly one shot. "How many shots" is decided the moment
  the script is written — a direct result of making narration the master clock.
- **Stage ④ is where audio/video sync lands.** It translates the one ground truth
  ("how long this sentence took to say") into "how long this shot holds", without
  calling any model.

## Module map

```
video_agent/
  cli.py            command-line entry point and orchestration (run_pipeline)
  config.py         canvas sizes, FPS, template list, Settings from .env
  llm.py            OpenAI-compatible client; JSON extraction with retries
  script_gen.py     ① article → narration (loads prompts/script.md)
  scene_gen.py      ② narration → scene spec, validation + retry + salvage/fallback
  schema.py         the data contracts (Narration, SceneSpec) and validation rules
  timing.py         ④ duration alignment; CJK-aware duration estimation
  tts.py            ③ per-segment synthesis; ffprobe duration probe
  voice_engine.py   offline Kokoro-82M TTS engine (model download + caching)
  render.py         ⑤ dispatch type → template; build the Manim Scene
  compose.py        ⑥ ffmpeg concat, mux, A/V sync assertion, audio trim
  style.py          design tokens (font, colours, chip/tick primitives)
  templates/        twelve scene templates, one file per type + entrance_hold helper
  prompts/          script.md, scene.md — the LLM prompts (editable, not code)
tests/              offline pytest suite
examples/demo.md    sample article
assets/bgm/         built-in royalty-free loop (optional)
```

## Module responsibilities and interfaces

### `cli.py`
The only orchestration point. `run_pipeline()` wires the stages together and is
injected with a `deps` dict of callables, so tests can run it without an LLM,
TTS engine, or Renderer. `main()` parses the CLI and calls `run_pipeline()`.

### `config.py`
Holds `CANVAS` (`916` → 1080×1920, `169` → 1920×1080), `FPS`, and
`TEMPLATE_TYPES`. `Settings.from_env()` reads exactly three keys —
`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` — and fails loudly if any is missing.
This is the entire user-facing configuration surface.

### `llm.py`
A thin OpenAI-compatible wrapper. `chat()` returns raw text; `chat_json()`
strips code fences, parses JSON, requires an object (not array/scalar), and on
failure appends the error back to the conversation and retries.

### `script_gen.py` / `scene_gen.py`
Stage ① and ②. Each loads its prompt file and asks the model for one JSON
document. `scene_gen` is the guarded stage: it validates against `schema.py`,
retries once with the error message, then falls back gracefully (see below).

### `schema.py`
The contracts. `Narration` and `SceneSpec` are pydantic models;
`validate_scene_spec()` enforces the three rules (1:1 mapping, known `type`,
required `props`) and raises `ContractError`. `PROPS_REQUIRED` maps each type to
its required prop keys and is asserted to cover exactly `TEMPLATE_TYPES`.

### `voice_engine.py`
The offline TTS engine (see [DESIGN.md](DESIGN.md#offline-voiceover)). Handles
one-time model download with mirror fallback and integrity checks, sentence
chunking under the tokenizer limit, and writing 24 kHz PCM audio.

### `timing.py`
`align_durations()` adds the inter-shot `GAP`; `fit_total()` applies the soft
`--max-seconds` cap by keeping whole shots from the front; `estimate_duration()`
falls back to a character-count estimate when audio duration is unavailable.

### `render.py`
Sets up Manim's frame to match the target canvas ratio, then renders each shot
by dispatching `type` to `templates.render_scene`. A shot whose template raises
is **degraded** to a plain text card and rendering continues.

### `compose.py`
ffmpeg glue: `concat_voiceover()` joins per-segment audio (optionally inserting a
breathing `gap`), `mux()` lays narration + BGM under the silent video,
`assert_av_sync()` fails if audio and video durations drift beyond a tolerance,
and `trim_audio()` pads/trims to an exact length.

## Data contracts

The two JSON documents below are the **only interface between the model and the
templates** — the single most important contract in the system.

### `narration.json` (stage ①)

```json
{
  "title": "LLM Reasoning and Agents: From Test-Time Compute to Planning",
  "segments": [
    { "id": 0, "text": "If you let the model try a few times, its reasoning improves noticeably." },
    { "id": 1, "text": "This is what we call test-time compute." }
  ]
}
```

### `scene_spec.json` (stage ②)

```json
{
  "title": "LLM Reasoning and Agents",
  "aspects": ["916", "169"],
  "scenes": [
    { "id": 0, "type": "title", "narration_id": 0,
      "props": { "title": "LLM Reasoning and Agents", "subtitle": "From Test-Time Compute to Planning" } },
    { "id": 1, "type": "quote", "narration_id": 1,
      "props": { "text": "Test-time compute: try a few times, answer more accurately" } }
  ]
}
```

### The three rules

1. **`scenes` and `segments` are strictly 1:1** — `scenes[i].narration_id == i`,
   and the shot count equals the segment count. Sync is guaranteed by the data
   structure, so it *cannot* drift. (The opening shot occupies an id and owns a
   narration segment too; there are no free-floating shots.)
2. **`type` must be one of the twelve** — otherwise validation fails and triggers
   a retry.
3. **`props` shape is determined by `type`** — each type has a fixed prop schema;
   extra fields are ignored, missing required fields fail validation.

`narration_id` is stored explicitly (even though it always equals `id`): stage ④
uses it to look up the duration, and relaxing the 1:1 rule later would only
require loosening this constraint and nothing else.

## The twelve templates

The model cannot invent shot types; it may only choose from these twelve,
derived from a reference explainer style. Each template is **duration-
parameterised** — it accepts a number of seconds and internally distributes
entrance animation vs. hold time.

| # | type | Purpose | props |
|---|------|---------|-------|
| 1 | `title` | Opening title | `{title, subtitle}` |
| 2 | `section` | Section transition | `{index, heading}` |
| 3 | `bullets` | Bullets revealed one by one (**most common**) | `{heading, items[]}` |
| 4 | `steps` | Process/step bar, optional progress | `{heading, steps[], done_index}` |
| 5 | `cycle` | 3–4 node loop (repeat / closed loop) | `{heading, nodes[]}` |
| 6 | `tree` | Tree diagram, highlightable path | `{heading, root, children[][]}` |
| 7 | `compare` | Two-column comparison (A vs B) | `{heading, left:{title,items[]}, right:{title,items[]}}` |
| 8 | `grid` | Candidate grid, tick/cross marks | `{heading, cells:[{label, mark}]}` |
| 9 | `metric` | Big number + label | `{heading, value, unit, label}` |
| 10 | `quote` | Oversized pull-quote | `{text, source?}` |
| 11 | `summary` | Keyword recap | `{heading, items[]}` |
| 12 | `closing` | Ending + optional handle | `{text, handle?}` |

**The baseline trio** is `title` + `bullets` + `closing`: any article can be
turned into a complete video using just these three. Degradation falls back to
this trio, **guaranteeing the tool always produces a video**.

**Visual style:** pure text + colour blocks + geometric shapes — no stock
imagery or icon libraries. This avoids image sourcing, licensing, and dependency
problems, and the look is already clean enough. The design tokens (font,
colours, accent palette) live in `style.py`.

## Failure policy

**A visual problem degrades and continues; a sound/content problem stops with an
error.** Plain visuals are still watchable, but missing audio or garbled content
is not.

| Stage | Possible failure | Handling |
|-------|------------------|----------|
| ① Narration | LLM timeout / empty response | Retry twice; then fail |
| ② Scene spec | Invalid JSON / unknown `type` / missing props | Re-ask the model once with the error; then degrade the shot to `bullets`; then degrade the whole document to `title+bullets+closing` — **always produce a video** |
| ③ Voiceover | One segment fails to synthesize | Retry twice; then fail |
| ④ Alignment | Audio duration missing | Character-count estimate; continue |
| ⑤ Render | A single template raises | Degrade that shot to a text card; render the rest |
| ⑥ Compose | Audio/video out of sync | Assert total audio vs. total video; fail if drift > 0.3 s |

The degradation chain — *ideal template → `bullets` → `title+bullets+closing`* —
is the ladder toward "it always produces something".

Each run writes its intermediates to `output/<name>/`, so a failure points
directly at the stage that broke.

## Output layout

```
output/<article-name>/
  narration.json          stage ① output (readable, editable)
  scene_spec.json         stage ② output
  audio/000.mp3 …         stage ③ output (one file per segment)
  <name>_916.mp4          vertical
  <name>_169.mp4          horizontal
```

## Testing strategy

The suite bets on exactly three things:

1. **Golden smoke** — a small sample article runs the full chain and asserts the
   artifacts exist with correct durations and resolutions.
2. **JSON contract** — one valid `scene_spec.json` plus deliberately broken ones
   (wrong `type`, missing props) asserting "valid passes, broken is rejected".
   This is the system's linchpin, so it is locked down hard.
3. **Per-template unit render** — each template takes fake data plus a duration
   and renders a short segment without error, so a template can be verified
   alone in seconds.

**Deliberately not tested:** LLM output quality (subjective and model-dependent)
and frame-accurate ffmpeg comparison (too heavy).
