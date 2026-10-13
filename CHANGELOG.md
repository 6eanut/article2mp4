# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Subtitles now default to **on** (`--no-subtitle` disables them).
- Template text scales to fit the frame, preventing clipped or overlapping text
  in the 9:16 output.

### Fixed

- Narration no longer breaks mid-sentence at enumeration commas (`、`).
- Voiceover loudness normalized to -14 LUFS for clearer playback.

### Added

- Human-readable per-stage progress output; Manim's progress bar is muted.

## [0.1.0] - 2026-10-13

### Added

- End-to-end pipeline: Markdown article → LLM narration script → LLM scene
  spec → per-segment voiceover → duration alignment → Manim render → ffmpeg
  concat/mux, producing both 9:16 and 16:9 MP4s.
- Twelve Manim scene templates (title, section, bullets, steps, cycle, tree,
  compare, grid, metric, quote, summary, closing).
- Fully offline Chinese text-to-speech powered by Kokoro-82M (`kokoro-onnx`),
  with on-demand model download and a GitHub-mirror fallback.
- Optional subtitles and background music; `--max-seconds` soft limit;
  `--voiceover-only` mode.
- Configuration surface limited to `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.

### Notes

- The narration voice is **Chinese-only**; the repository itself is written in
  English.
