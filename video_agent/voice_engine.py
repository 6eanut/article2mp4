from __future__ import annotations

import os

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


def synthesize(text: str, out_path: str, voice: str, speed: float = 1.0) -> str:
    raise NotImplementedError