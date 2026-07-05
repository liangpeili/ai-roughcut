from __future__ import annotations

import argparse
from pathlib import Path

from .config import get_profile
from .pipeline import PipelineOptions, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a conservative, reviewable rough cut for interview footage.")
    parser.add_argument("input", type=Path, help="Input video file.")
    parser.add_argument("--project-dir", type=Path, default=Path("."), help="Project directory containing work/ and output/.")
    parser.add_argument("--profile", default="lianglaoshi", help="Editing profile name.")
    parser.add_argument("--kimi", action="store_true", help="Call Kimi/Moonshot for delete/compress/keep/review decisions.")
    parser.add_argument("--subtitle", action="store_true", help="Run WhisperX again after rough cut and generate SRT/ASS subtitles.")
    parser.add_argument("--no-render", action="store_true", help="Only generate candidates, Kimi task/result, cut list, and review report.")
    parser.add_argument("--autoeditor-preview", action="store_true", help="Also generate work/01_autoeditor_preview.mp4.")
    parser.add_argument("--whisperx-model", default="large-v3", help="WhisperX model name.")
    parser.add_argument("--language", default="zh", help="WhisperX language code.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile = get_profile(args.profile)
    result = run_pipeline(
        PipelineOptions(
            input_path=args.input,
            project_dir=args.project_dir,
            profile=profile,
            use_kimi=args.kimi,
            subtitle=args.subtitle,
            render=not args.no_render,
            autoeditor_preview=args.autoeditor_preview,
            whisperx_model=args.whisperx_model,
            language=args.language,
        )
    )
    print("AI roughcut outputs:")
    for key, value in result.items():
        if value:
            print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
