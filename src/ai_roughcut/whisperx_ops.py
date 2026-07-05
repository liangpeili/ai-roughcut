from __future__ import annotations

from pathlib import Path

from .ffmpeg_ops import run_command
from .io_utils import ensure_dir


def transcribe(audio_path: Path, output_dir: Path, model: str = "large-v3", language: str = "zh") -> None:
    ensure_dir(output_dir)
    run_command(
        [
            "whisperx",
            str(audio_path),
            "--model",
            model,
            "--language",
            language,
            "--output_dir",
            str(output_dir),
            "--output_format",
            "json,srt",
        ]
    )


def expected_json_path(audio_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{audio_path.stem}.json"


def expected_srt_path(audio_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{audio_path.stem}.srt"
