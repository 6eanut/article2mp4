from __future__ import annotations

import os
import subprocess
import tempfile

from .tts import ffmpeg_path

# EBU R128 loudness target, applied after gentle speech EQ and compression.
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"
SPEECH_FILTER = (
    "highpass=f=80,"
    "equalizer=f=250:t=q:w=1:g=-2,"
    "equalizer=f=3000:t=q:w=1:g=2,"
    "acompressor=threshold=0.125:ratio=2:attack=15:release=100"
)


def build_concat_file(ids, audio_dir) -> str:
    paths = [os.path.join(audio_dir, f"{i:03d}.wav") for i in ids]
    return "\n".join("file '" + path.replace("'", "'\\''") + "'" for path in paths) + "\n"


def _audio_codec(out_path: str) -> list[str]:
    if out_path.lower().endswith(".wav"):
        return ["-c:a", "pcm_s16le", "-ar", "24000"]
    if out_path.lower().endswith(".mp3"):
        return ["-c:a", "libmp3lame", "-b:a", "192k", "-ar", "24000"]
    raise ValueError("voiceover output must end in .wav or .mp3")


def build_concat_filter(n: int, gap: float) -> str:
    """Append ``gap`` seconds of silence after each input, then concatenate in
    order (creating a "breathing pause")."""
    pad = "".join(f"[{k}:a]apad=pad_dur={gap}[a{k}];" for k in range(n))
    join = "".join(f"[a{k}]" for k in range(n))
    return f"{pad}{join}concat=n={n}:v=0:a=1[out]"


def concat_voiceover(audio_dir, ids, out_path, gap: float = 0.0,
                     loudnorm: bool = True) -> str:
    ff = ffmpeg_path()
    inputs = []
    for i in ids:
        inputs += ["-i", os.path.join(audio_dir, f"{i:03d}.wav")]
    if gap and gap > 0:
        filt = build_concat_filter(len(ids), gap)
        cleanup = SPEECH_FILTER + ("," + LOUDNORM if loudnorm else "")
        filt = filt.replace("[out]", f"[pre];[pre]{cleanup}[out]")
        subprocess.run([ff, "-y", *inputs, "-filter_complex", filt,
                        "-map", "[out]", *_audio_codec(out_path), out_path],
                       check=True, capture_output=True)
    else:
        lst = out_path + ".txt"
        try:
            with open(lst, "w", encoding="utf-8") as f:
                f.write(build_concat_file(ids, audio_dir))
            af = ["-af", SPEECH_FILTER + ("," + LOUDNORM if loudnorm else "")]
            subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                            *af, *_audio_codec(out_path), out_path],
                           check=True, capture_output=True)
        finally:
            if os.path.exists(lst):
                os.remove(lst)
    return out_path


def mux(video_path, audio_path, bgm_path, out_path) -> str:
    ff = ffmpeg_path()
    audio_codec = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    if bgm_path and os.path.exists(bgm_path):
        subprocess.run([
            ff, "-y", "-i", video_path, "-i", audio_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex",
            "[1:a]asplit=2[voice][sidechain];"
            "[2:a]volume=0.10[music];"
            "[music][sidechain]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=250[ducked];"
            "[voice][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", *audio_codec,
            "-shortest", out_path,
        ], check=True, capture_output=True)
    else:
        subprocess.run([ff, "-y", "-i", video_path, "-i", audio_path,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        *audio_codec, "-shortest", out_path],
                       check=True, capture_output=True)
    return out_path


def assert_av_sync(video_dur: float, audio_dur: float, tol: float = 0.3) -> None:
    assert abs(video_dur - audio_dur) <= tol, (
        "audio/video duration drift too large: "
        f"video={video_dur:.2f}s audio={audio_dur:.2f}s tol={tol}"
    )


def trim_audio(in_path, seconds, out_path=None) -> str:
    """Trim/pad the audio to ``seconds`` (pad to equal length so mux's -shortest
    does not cut off the tail)."""
    ff = ffmpeg_path()
    out_path = out_path or in_path
    in_place = os.path.abspath(out_path) == os.path.abspath(in_path)
    target = out_path
    if in_place:
        descriptor, target = tempfile.mkstemp(
            prefix=".trim-", suffix=os.path.splitext(out_path)[1],
            dir=os.path.dirname(os.path.abspath(out_path)),
        )
        os.close(descriptor)
    try:
        subprocess.run(
            [ff, "-y", "-i", in_path, "-t", f"{seconds:.3f}",
             "-af", f"apad=whole_dur={seconds:.3f}", target],
            check=True, capture_output=True,
        )
        if in_place:
            os.replace(target, out_path)
    finally:
        if in_place and os.path.exists(target):
            os.remove(target)
    return out_path
