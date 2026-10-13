from __future__ import annotations

import os
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
            urllib.request.urlretrieve(pre + MODEL_FILES[name], tmp)
            if os.path.getsize(tmp) > 0:
                os.replace(tmp, dst)
                return dst
        except Exception as e:  # 试下一个代理
            last = e
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    raise RuntimeError(f"下载模型 {name} 失败（所有镜像不可用）: {last}")


def ensure_models(progress=None) -> None:
    for name in MODEL_FILES:
        if progress:
            progress(name)
        _download(name)


_ENGINE = None
SAMPLE_RATE = 24000

# Tokens per sentence separator (approx. consumed by g2p/tokenizer) and
# tokenizer hard limit. Keep unpacking generously below the 510-row limit.
_MAX_TOKENS = 500
# Samples of silence (0.05 s @ 24 kHz) inserted between concatenated chunks.
_CHUNK_GAP_SAMPLES = int(0.05 * SAMPLE_RATE)

# Characters that denote a sentence boundary (punctuation kept attached).
_SENTENCE_SEP = "。！？；、\n"


def _chunk(text: str, count_tokens, max_tokens: int = _MAX_TOKENS) -> list[str]:
    """Split ``text`` into pieces whose ``count_tokens`` never exceeds ``max_tokens``.

    ``count_tokens(s)`` must return the token count of a string (callers wrap the
    g2p+tokenizer in a lambda). Sentences are greedily packed on Chinese
    sentence boundaries (keeping the trailing punctuation). A single sentence
    longer than the limit is hard-split by characters into fitting pieces.
    """
    if not text:
        return [""]
    if count_tokens(text) <= max_tokens:
        return [text]

    sentences = _split_sentences(text)
    chunks: list[str] = []
    buf = ""
    for sent in sentences:
        if count_tokens(sent) <= max_tokens:
            if buf and count_tokens(buf + sent) > max_tokens:
                chunks.append(buf)
                buf = sent
            else:
                buf += sent
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(_hard_split(sent, count_tokens, max_tokens))
    if buf:
        chunks.append(buf)
    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split on Chinese sentence punctuation, keeping the punctuation attached."""
    parts: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in _SENTENCE_SEP:
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


def _synthesize_chunk(kokoro, g2p, text: str, voice: str, speed: float) -> np.ndarray:
    """Run the model on a single (in-limit) text chunk and return float32 audio."""
    ids = kokoro.tokenizer.tokenize(g2p(text))
    style = kokoro.get_voice_style(voice)[len(ids)]
    inputs = {
        "input_ids": np.array([[0, *ids, 0]], dtype=np.int64),
        "style": np.array(style, dtype=np.float32),
        "speed": np.array([speed], dtype=np.float32),
    }
    return np.asarray(kokoro.sess.run(None, inputs)[0], dtype=np.float32).reshape(-1)


def synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str:
    import soundfile as sf
    kokoro, g2p = _engine()
    count_tokens = lambda s: len(kokoro.tokenizer.tokenize(g2p(s)))
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
    # Force WAV: pipeline paths end in ".mp3" (a remnant of the edge-tts era),
    # and libsndfile would otherwise infer the MP3 container from the extension,
    # which has no PCM_16 subtype. ffmpeg detects audio by content, so WAV-in-.mp3
    # concatenates and muxes fine.
    sf.write(out_path, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return out_path
