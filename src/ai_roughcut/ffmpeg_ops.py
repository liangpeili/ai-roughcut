from __future__ import annotations

import subprocess
from pathlib import Path

from .io_utils import ensure_dir
from .models import KeepInterval


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def _ffmpeg_supports_filter(filter_name: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-filters"],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return False
    return filter_name in result.stdout


def normalize_video(input_path: Path, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vf",
            "scale=1920:-2,fps=30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(output_path),
        ]
    )


def extract_audio(input_path: Path, output_path: Path, sample_rate: int = 16000) -> None:
    ensure_dir(output_path.parent)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            str(output_path),
        ]
    )


def media_duration(input_path: Path) -> float:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ]
    )
    return float(result.stdout.strip())


def detect_silence(input_path: Path, noise: str = "-35dB", min_duration: float = 0.8) -> str:
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            f"silencedetect=noise={noise}:d={min_duration}",
            "-f",
            "null",
            "-",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stderr


def render_keep_intervals(source: Path, keep_intervals: list[KeepInterval], output_path: Path, work_dir: Path) -> None:
    clips_dir = ensure_dir(work_dir / "clips")
    concat_path = work_dir / "concat.txt"
    clip_paths: list[Path] = []
    for index, interval in enumerate(keep_intervals, start=1):
        clip_path = clips_dir / f"{index:03d}.mp4"
        clip_paths.append(clip_path)
        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-ss",
                f"{interval.start:.3f}",
                "-to",
                f"{interval.end:.3f}",
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                str(clip_path),
            ]
        )
    concat_path.write_text("".join(f"file '{path.resolve()}'\n" for path in clip_paths), encoding="utf-8")
    ensure_dir(output_path.parent)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            str(output_path),
        ]
    )


def burn_subtitles(input_path: Path, ass_path: Path, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    if not _ffmpeg_supports_filter("subtitles"):
        print(f"[warn] ffmpeg does not support the subtitles filter (libass missing); skipping burned subtitle output: {output_path}")
        return
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vf",
            f"subtitles={ass_path}",
            "-c:a",
            "copy",
            str(output_path),
        ]
    )
