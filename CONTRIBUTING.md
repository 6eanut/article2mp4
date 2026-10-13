# Contributing to article2mp4

Thanks for your interest in improving article2mp4! This document explains how to
set up the project, run the tests, and submit changes.

## Development setup

The project targets **Python 3.11+** and needs `ffmpeg` plus the standard Manim
system libraries (Cairo, Pango) available on your system.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install runtime + dev dependencies
pip install -r requirements.txt
pip install pytest ruff

# 3. Configure the only user-facing settings
cp .env.example .env
# edit .env: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
```

The full pipeline also needs `ffmpeg` on your `PATH`. On Debian/Ubuntu:

```bash
sudo apt-get install -y ffmpeg libcairo2-dev libpango1.0-dev pkg-config
```

## Running the tests

```bash
pytest -q
```

The suite runs entirely offline; the one real-model TTS test is opt-in and
skipped by default. To run it (it downloads ~168 MB of models on first use):

```bash
KOKORO_SMOKE=1 pytest tests/test_voice_engine.py -q
```

## Linting

```bash
ruff check .
```

## Pull request process

1. Fork the repository and create a topic branch from `main`.
2. Keep changes focused; one logical change per pull request.
3. Add or update tests for any behavior change.
4. Make sure `pytest -q` and `ruff check .` are clean.
5. Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/)
   style (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
6. Open the pull request and fill in the template.

## Scope and conventions

- **The tool narrates Chinese.** The bundled speech engine (Kokoro `zh`) is
  Chinese-only, so narration text and the shipped example are Chinese. Everything
  else — code, comments, docstrings, error messages, documentation — is written in
  English.
- Some Chinese is **functional** and must not be translated: the Hanzi-count regex
  in `video_agent/timing.py`, the CJK sentence-delimiter set in
  `video_agent/voice_engine.py`, and the Chinese input fixtures in the TTS tests.
  See `docs/ARCHITECTURE.md` before touching those.
- Prefer small, well-tested functions and keep modules focused.

## Reporting bugs and requesting features

Use the GitHub issue templates. For security issues, see `SECURITY.md` instead
of opening a public issue.
