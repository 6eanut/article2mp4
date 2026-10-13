from __future__ import annotations
import os
import subprocess
from .tts import ffmpeg_path


def build_concat_file(ids, audio_dir) -> str:
    return "\n".join(f"file '{os.path.join(audio_dir, f'{i:03d}.mp3')}'" for i in ids) + "\n"


def build_concat_filter(n: int, gap: float) -> str:
    """每个输入后补 gap 秒静音，再顺序拼接（制作‘呼吸停顿’）。"""
    pad = "".join(f"[{k}:a]apad=pad_dur={gap}[a{k}];" for k in range(n))
    join = "".join(f"[a{k}]" for k in range(n))
    return f"{pad}{join}concat=n={n}:v=0:a=1[out]"


def concat_voiceover(audio_dir, ids, out_path, gap: float = 0.0) -> str:
    ff = ffmpeg_path()
    inputs = []
    for i in ids:
        inputs += ["-i", os.path.join(audio_dir, f"{i:03d}.mp3")]
    if gap and gap > 0:
        filt = build_concat_filter(len(ids), gap)
        subprocess.run([ff, "-y", *inputs, "-filter_complex", filt,
                        "-map", "[out]", out_path], check=True, capture_output=True)
    else:
        lst = out_path + ".txt"
        try:
            with open(lst, "w", encoding="utf-8") as f:
                f.write(build_concat_file(ids, audio_dir))
            subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                            "-c", "copy", out_path], check=True, capture_output=True)
        finally:
            if os.path.exists(lst):
                os.remove(lst)
    return out_path


def mux(video_path, audio_path, bgm_path, out_path) -> str:
    ff = ffmpeg_path()
    if bgm_path and os.path.exists(bgm_path):
        subprocess.run([
            ff, "-y", "-i", video_path, "-i", audio_path, "-i", bgm_path,
            "-filter_complex",
            "[2:a]volume=0.12,aloop=loop=-1:size=2e9[b];[1:a][b]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-shortest", out_path,
        ], check=True, capture_output=True)
    else:
        subprocess.run([ff, "-y", "-i", video_path, "-i", audio_path,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-shortest", out_path], check=True, capture_output=True)
    return out_path


def assert_av_sync(video_dur: float, audio_dur: float, tol: float = 0.3) -> None:
    assert abs(video_dur - audio_dur) <= tol, \
        f"音画时长偏差过大: video={video_dur:.2f}s audio={audio_dur:.2f}s tol={tol}"