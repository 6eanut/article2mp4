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