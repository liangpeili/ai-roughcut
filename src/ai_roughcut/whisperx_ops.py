from __future__ import annotations

from pathlib import Path

from .ffmpeg_ops import run_command
from .io_utils import ensure_dir, read_json


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
            "json",
        ]
    )


def expected_json_path(audio_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{audio_path.stem}.json"


def expected_srt_path(audio_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{audio_path.stem}.srt"


def json_to_srt(json_path: Path, srt_path: Path) -> None:
    """Convert WhisperX JSON transcript to SRT using segment-level timings."""
    data = read_json(json_path)
    segments = data.get("segments", []) if isinstance(data, dict) else data
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = segment.get("start", 0.0)
        end = segment.get("end", 0.0)
        text = segment.get("text", "").strip()
        if not text:
            continue
        lines.append(f"{index}")
        lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
        lines.append(text)
        lines.append("")
    ensure_dir(srt_path.parent)
    srt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _format_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")
