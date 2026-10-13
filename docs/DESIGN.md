# Design rationale

[ARCHITECTURE.md](ARCHITECTURE.md) describes *what* the system is. This document
explains *why* it is built this way — the decisions that are not obvious from
reading the code, and the alternatives that were considered and rejected.

## Product shape (the hard contract)

The tool's form is fixed and deliberately narrow:

- **Input:** one Markdown file.
- **Output:** one (or two) MP4 files.
- **The only configuration is** `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.
- **One command runs end to end**, with no interactive step in the middle.
- A standalone repository: clone it and it works; the user's articles and outputs
  never enter version control.

The content form follows from early requirements: produce both a **9:16 vertical**
clip (short-video platforms) and a **16:9 horizontal** one (longer-form platforms);
narration, visuals, and music are all generated or bundled by the tool; the style
is data/animation explainer, not live-action.

**Quality principle (explicitly authorised):** wherever an implementation
detail conflicts with output quality, quality wins. Cost and speed yield to the
quality of the finished video.

## Why Manim

Manim (Python) is the single rendering engine.

- It has the highest practical quality ceiling for math/diagram/text animation.
- It renders **frame-by-frame on CPU, deterministically** — the same code and
  input reproduce the same video 100% of the time, which is exactly the property
  batch production needs.
- Chinese renders correctly through an explicit font (`Noto Sans SC`).

Remotion (React/TS) was kept as a possible future direction but is out of scope
for this version; it would be reconsidered if marketing/UI-style visuals became
the primary need.

> Two known sharp edges: Manim 0.22 does **not** export `CheckMark`, so the tick
> is drawn by hand; and CJK **must** be given an explicit font, or Chinese renders
> as tofu boxes.

## Narration as the master clock

**Decision:** generate the narration audio first, read each segment's real
duration, and drive shot durations and cut points from it. The voice is the only
master clock; the picture follows.

The rejected alternative was to fix shot durations and then stretch or crop the
narration to fit. That was turned down because being even half a beat out of
sync is glaringly obvious in an explainer video — the mismatch reads as broken.

The most direct consequence: when the viewer sees "the picture held for a
moment", it is because *that sentence took five seconds to say*, not because the
animation was hard-coded to pause for three. The timing is honest by
construction.

**Core formula:** `shot_i duration = audio_i duration + gap`, where `gap` is a
breathing pause between shots (default 0.4 s).

### How a template "eats" a number of seconds

Each template declares two phases:

```
        d = 5.6s
   ├──────────────────────────┤
   ├─ entrance ─┤├──── hold ────┤
     entrance         hold
     animation        (frozen)
     (has a
      minimum)
```

- Allocation rule: `hold = d − entrance`. A long `d` holds longer; a short `d`
  compresses the entrance to its minimum.
- Extreme fallback: if `d` is shorter than the minimum entrance, the entrance is
  sped up (compressed `run_time`); if that still is not enough, the shot is
  nudged slightly longer — **better to hold the picture half a second too long
  than to let the animation break.**

### Subtitles

Subtitles are a **toggleable overlay, on by default**, disabled with
`--no-subtitle`. The content is the narration sentence for that shot, shown in
sync with it. It is a **cross-cutting template capability** shared by all twelve
types, not a feature of one type. Motivation: short vertical videos are widely
watched on mute, so on-screen text is close to standard — so it ships on.

### Speech rate

**No rate parameter.** The engine speaks at its natural rate; there is no
`--rate` flag. (Explicit user decision: the rate does not need tuning.)

## Offline voiceover

The original design used `edge-tts`, a network service. The shipped engine is
**fully offline**: Kokoro-82M (`kokoro-onnx`, the `zh` release) with `misaki[zh]`
for grapheme-to-phoneme conversion and `onnxruntime` for inference.

Reasons for going offline:

- **No network dependency at inference time.** Once the models are downloaded,
  synthesis works without connectivity, and a run cannot fail because an external
  service is slow or unavailable.
- **No third-party exit.** A hosted TTS API can change or disappear; a bundled
  model cannot.
- **Deterministic-ish and free to run.**

The models (`kokoro-v1.1-zh.int8.onnx`, ~114 MB, and `voices-v1.1-zh.bin`, ~54 MB,
about **168 MB total**) download on first use through a GitHub mirror and are
cached under `~/.cache/kokoro-zh/` (overridable with `KOKORO_MODEL_DIR`). They are
**not** committed to the repository.

**The output is Chinese-only.** The bundled engine is the Chinese `zh` release and
cannot pronounce English naturally — English text would be transcribed
phonetically. The narration language therefore follows the source article, and
for Chinese input the result is natural Chinese speech. Supporting another
language would mean swapping the model.

Three integration details worth recording:

1. The `zh` ONNX export expects a **float32** `speed` tensor, whereas the wrapper
   passes int32; the engine calls `sess.run` directly to control the dtype.
2. The tokenizer has a hard limit of about 510 phonemes, so long text is split on
   sentence boundaries (and hard-split by characters when a single sentence is too
   long), then concatenated with a short silence between chunks.
3. Model paths end in `.mp3` as a historical remnant of the `edge-tts` era, but the
   audio is written as **WAV**. This is intentional: libsndfile infers the
   container from the file extension, and MP3 has no `PCM_16` subtype, which would
   raise "Invalid combination of format, subtype and endian". ffmpeg detects audio
   by content, so WAV-in-`.mp3` concatenates and muxes fine.

## Failure philosophy

**Degrade on visuals, stop on sound/content.** A plain-looking shot is still
watchable; missing audio or garbled content is not. This is why the pipeline is
willing to lose visual polish to keep going, but treats a failed voiceover or an
unparseable script as fatal.

The degradation ladder for scene generation — *ideal template → `bullets` →
`title+bullets+closing`* — exists so the tool **always produces a video**, even
when the model returns something the contract cannot accept.

## Hand-editable intermediates

Every intermediate is written to disk as readable JSON. If the narration is not
to the user's liking, they can edit `narration.json` and re-run the later stages
without paying for another model call; if the scene spec is wrong, they change a
line and re-render. This turns one expensive model call into a file that can be
polished repeatedly.

## Testing bets

The suite concentrates on three things and nothing else: the golden smoke test
(does the whole chain produce correct artifacts), the JSON contract (the
system's linchpin), and per-template unit renders. LLM output quality is not
tested — it is subjective and depends on an external model — and ffmpeg
frame-comparison is skipped as too heavy.

## Explicitly out of scope (YAGNI)

- A second rendering engine (Remotion) alongside Manim.
- Automatic image/icon selection or stock-media integration.
- A narration rate parameter.
- Automated evaluation of LLM output quality.
- Many-to-one mapping of narration segments onto a single shot.
