from __future__ import annotations

import os
import re
import urllib.request

import numpy as np

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


PROXIES = ["https://gh-proxy.com/", "https://ghfast.top/", "https://ghproxy.net/"]


def _download(name: str) -> str:
    dst = model_path(name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    os.makedirs(cache_dir(), exist_ok=True)
    last = None
    for pre in PROXIES:
        tmp = dst + ".part"
        try:
            resp = urllib.request.urlopen(pre + MODEL_FILES[name])
            blob = resp.read()
            length = resp.headers.get("Content-Length")
            if length:
                if len(blob) != int(length):
                    raise OSError("download truncated (byte count mismatch)")
            elif len(blob) == 0:
                raise OSError("download is empty")
            with open(tmp, "wb") as f:
                f.write(blob)
            os.replace(tmp, dst)
            return dst
        except Exception as e:  # try the next proxy
            last = e
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    raise RuntimeError(f"failed to download model {name} (all mirrors unavailable): {last}")


def ensure_models(progress=None) -> None:
    for name in MODEL_FILES:
        if progress:
            progress(name)
        _download(name)


_ENGINE = None
SAMPLE_RATE = 24000
_MODEL_VERSION_HYPHEN = re.compile(r"([A-Za-z]{2,}[A-Za-z0-9.]*)-(?=\d)")

# Tokens per sentence separator (approx. consumed by g2p/tokenizer) and
# tokenizer hard limit. Keep unpacking generously below the 510-row limit.
_MAX_TOKENS = 500
# Samples of silence (0.05 s @ 24 kHz) inserted between concatenated chunks.
_CHUNK_GAP_SAMPLES = int(0.05 * SAMPLE_RATE)

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


def _hard_split(text: str, count_tokens, max_tokens: int) -> list[str]:
    """Character-level split of a sentence too long to fit in one piece."""
    if count_tokens(text) <= max_tokens:
        return [text]
    pieces: list[str] = []
    buf = ""
    for ch in text:
        if buf and count_tokens(buf + ch) > max_tokens:
            pieces.append(buf)
            buf = ""
        buf += ch
    if buf:
        pieces.append(buf)
    return pieces


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


def _phonemize(g2p, text: str) -> str:
    """Align Misaki's initial-script check with its number conversion.

    ZHG2P checks the *original* first character, then converts Arabic numbers
    to Hanzi internally. A leading number therefore makes it parse following
    punctuation as pinyin. Applying the same conversion first preserves the
    spoken number while keeping its script detection in sync.
    """
    from cn2an import transform
    # In names such as GLM-5.2 and Qwen3.5-9B, '-' separates versions; cn2an
    # would otherwise pronounce it as a negative sign ("负").
    spoken = _MODEL_VERSION_HYPHEN.sub(r"\1 ", text)
    return g2p(transform(spoken, "an2cn"))


def _synthesize_chunk(kokoro, g2p, text: str, voice: str, speed: float) -> np.ndarray:
    """Run the model on a single (in-limit) text chunk and return float32 audio."""
    ids = kokoro.tokenizer.tokenize(_phonemize(g2p, text))
    style = kokoro.get_voice_style(voice)[len(ids)]
    inputs = {
        "input_ids": np.array([[0, *ids, 0]], dtype=np.int64),
        "style": np.array(style, dtype=np.float32),
        "speed": np.array([speed], dtype=np.float32),
    }
    return np.asarray(kokoro.sess.run(None, inputs)[0], dtype=np.float32).reshape(-1)


def synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str:
    import soundfile as sf
    if not out_path.lower().endswith(".wav"):
        raise ValueError("synthesized PCM audio requires a .wav output path")
    kokoro, g2p = _engine()
    def count_tokens(chunk_text):
        return len(kokoro.tokenizer.tokenize(_phonemize(g2p, chunk_text)))
    chunks = _chunk(text, count_tokens)
    if len(chunks) == 1:
        audio = _synthesize_chunk(kokoro, g2p, chunks[0], voice, speed)
    else:
        parts = [_synthesize_chunk(kokoro, g2p, c, voice, speed) for c in chunks]
        gap = np.zeros(_CHUNK_GAP_SAMPLES, dtype=np.float32)
        merged = [parts[0]]
        for part in parts[1:]:
            merged.append(gap)
            merged.append(part)
        audio = np.concatenate(merged)
    # Keep model output lossless until the final video encode.
    sf.write(out_path, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return out_path
