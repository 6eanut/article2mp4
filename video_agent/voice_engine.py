from __future__ import annotations

import os
import urllib.request

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
        try:
            urllib.request.urlretrieve(pre + MODEL_FILES[name], dst)
            if os.path.getsize(dst) > 0:
                return dst
        except Exception as e:  # 试下一个代理
            last = e
    raise RuntimeError(f"下载模型 {name} 失败（所有镜像不可用）: {last}")


def ensure_models(progress=None) -> None:
    for name in MODEL_FILES:
        if progress:
            progress(name)
        _download(name)


def synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str:
    raise NotImplementedError