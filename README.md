# article2mp4

[![CI](https://github.com/6eanut/article2mp4/actions/workflows/ci.yml/badge.svg)](https://github.com/6eanut/article2mp4/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

Turn a **Markdown article** into a narrated explainer video — rendered with
[Manim](https://www.manim.community/) animations and voiced by a fully **offline**
text-to-speech engine. One command produces both a vertical **9:16** and a
horizontal **16:9** MP4.

```
Markdown article  ──▶  LLM narration  ──▶  LLM scene spec  ──▶  offline voiceover
                  ──▶  duration alignment  ──▶  Manim render  ──▶  ffmpeg mux  ──▶  MP4
```

## Features

- **One input, one command.** Give it a Markdown file; get back ready-to-share videos.
- **Offline voiceover.** Chinese narration is synthesized locally with
  [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (`kokoro-onnx`) — no
  network calls at inference time after the one-time model download.
- **Twelve scene templates.** Title, section, bullets, steps, cycle, tree, compare,
  grid, metric, quote, summary, and closing layouts, chosen automatically from the
  narration.
- **Narration-driven timing.** Each shot's duration comes from its own audio; the
  animation adapts to the voice, not the other way around.
- **Dual aspect ratios.** 9:16 (1080×1920) and 16:9 (1920×1080) in a single run.
- **Optional subtitles and background music.**
- **Minimal configuration.** The only settings are your LLM's URL, API key, and model.

## Requirements

- Python **3.11+**
- `ffmpeg` on your `PATH`
- Manim's system libraries (Cairo, Pango). On Debian/Ubuntu:

  ```bash
  sudo apt-get install -y ffmpeg libcairo2-dev libpango1.0-dev pkg-config
  ```

## Install

```bash
# 1. Clone and create an environment
git clone https://github.com/6eanut/article2mp4.git
cd article2mp4
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the only three settings
cp .env.example .env
# edit .env: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
```

The project is also installable as a package (providing the `article2mp4` console
script) via `pip install .`.

## Quick start

```bash
python -m video_agent make examples/demo.md
```

Outputs land in `output/demo/`:

- `demo_916.mp4` — vertical
- `demo_169.mp4` — horizontal

The first run downloads about **168 MB** of Chinese speech models (fetched through
a GitHub mirror and cached in `~/.cache/kokoro-zh/`). After that, synthesis is fully
offline.

## CLI reference

```
python -m video_agent make <article.md> [options]
```

| Option | Description | Default |
| --- | --- | --- |
| `--aspect {916,169,both}` | Which aspect ratio(s) to render | `both` |
| `--max-seconds N` | Soft cap: keep whole shots from the front until `N` seconds | no limit |
| `--voice ID` | Kokoro voice id (e.g. `zf_001`) | `zf_001` |
| `--subtitle` | Burn the narration in as subtitles | off |
| `--voiceover-only` | Generate narration audio only, skip rendering | off |

## How it works

1. **Narration** — an LLM rewrites the article into a short spoken script, split into
   sentence-level segments.
2. **Scene spec** — an LLM assigns each segment one of twelve scene types with typed
   props; the result is validated and retried on malformed output.
3. **Voiceover** — each segment is synthesized to a 24 kHz WAV file by the offline
   Kokoro engine.
4. **Alignment** — shot durations are derived from the audio durations (narration is
   the master clock).
5. **Render** — a Manim scene renders each shot; a failing shot degrades to a plain
   text card instead of aborting the video.
6. **Compose** — ffmpeg concatenates the shots, lays the narration (and optional BGM)
   underneath, and muxes to MP4, asserting audio/video sync.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the module map and
[`docs/DESIGN.md`](docs/DESIGN.md) for the reasoning behind these choices.

## Voice and language

The bundled speech engine is **Chinese-only** (Kokoro `v1.1-zh`; 103 voices — the
default is the female voice `zf_001`). Narration is synthesized in the language of
the source article, so a Chinese article produces Chinese narration. English text
would be transcribed phonetically rather than spoken naturally; using a different
language is not currently supported.

## Project layout

```
video_agent/          pipeline package
  cli.py              command-line entry point and orchestration
  script_gen.py       article → narration (LLM)
  scene_gen.py        narration → scene spec (LLM)
  schema.py           data contracts and validation
  voice_engine.py     offline Kokoro TTS
  timing.py           duration alignment
  render.py           Manim rendering
  compose.py          ffmpeg concat / mux
  templates/          twelve Manim scene templates
  prompts/            LLM prompt files
tests/                pytest suite (runs offline)
examples/demo.md      sample article
```

## Development

```bash
pytest -q          # run the test suite (offline)
ruff check .       # lint
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow.

## Limitations

- Narration is **Chinese-only** (see above).
- The LLM endpoint must be OpenAI-compatible.
- Rendering is CPU-bound; longer articles take longer to render.

## License

Released under the [MIT License](LICENSE).
