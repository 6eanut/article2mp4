from __future__ import annotations
import os
import subprocess
from .schema import Narration


def ffmpeg_path() -> str:
    """优先用环境里的 ffmpeg（.env-mamba/env/bin），否则回退 PATH。"""
    cand = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".env-mamba", "env", "bin", "ffmpeg",
    )
    return cand if os.path.exists(cand) else "ffmpeg"


def synth_segment(text: str, out_path: str, voice: str, speed: float = 1.0) -> None:
    from .voice_engine import synthesize
    synthesize(text, out_path, voice, speed=speed)


def probe_duration(path: str) -> float:
    ffprobe = ffmpeg_path().replace("ffmpeg", "ffprobe")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def render_voiceover(narration: Narration, out_dir: str, voice: str,
                     synth=synth_segment, probe=probe_duration, retries: int = 2,
                     speed: float = 1.0) -> list[float]:
    os.makedirs(out_dir, exist_ok=True)
    durations = []
    for seg in narration.segments:
        path = os.path.join(out_dir, f"{seg.id:03d}.mp3")
        last = None
        ok = False
        for _ in range(retries + 1):
            try:
                synth(seg.text, path, voice, speed=speed)
                durations.append(probe(path))
                ok = True
                break
            except Exception as e:  # 声音失败 = 致命
                last = e
        if not ok:
            raise RuntimeError(f"第 {seg.id} 段配音失败: {last}")
    return durations