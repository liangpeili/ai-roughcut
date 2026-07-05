from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import Profile
from .decisions import build_cut_list
from .ffmpeg_ops import (
    burn_subtitles,
    detect_silence,
    extract_audio,
    media_duration,
    normalize_video,
    render_keep_intervals,
    run_command,
)
from .fillers import find_filler_candidates
from .handoff import write_handoff_package
from .io_utils import ensure_dir, read_json, write_json
from .llm import build_ai_task, call_openai_compatible, load_ai_results, validate_ai_results
from .reports import write_review_csv, write_review_html
from .silence import parse_ffmpeg_silencedetect
from .subtitles import srt_to_ass
from .whisperx_ops import expected_json_path, expected_srt_path, json_to_srt, transcribe


@dataclass(frozen=True)
class PipelineOptions:
    input_path: Path
    project_dir: Path
    profile: Profile
    use_ai: bool = False
    subtitle: bool = False
    render: bool = True
    autoeditor_preview: bool = False
    whisperx_model: str = "large-v3"
    language: str = "zh"


def run_pipeline(options: PipelineOptions) -> dict:
    paths = ProjectPaths(options.project_dir, options.input_path)
    paths.create()

    normalized = paths.work / "00_normalized.mp4"
    audio = paths.work / "audio.wav"
    normalize_video(options.input_path, normalized)
    extract_audio(normalized, audio)

    transcript_dir = paths.work / "transcript"
    transcribe(audio, transcript_dir, model=options.whisperx_model, language=options.language)
    transcript_path = expected_json_path(audio, transcript_dir)
    transcript = read_json(transcript_path)

    silence_log = detect_silence(audio, min_duration=options.profile.silence.mark_after)
    silence_candidates = parse_ffmpeg_silencedetect(silence_log, options.profile.silence)
    filler_candidates = find_filler_candidates(transcript, options.profile.filler_words)
    write_json(paths.work / "candidates" / "silence_candidates.json", [item.to_dict() for item in silence_candidates])
    write_json(paths.work / "candidates" / "filler_candidates.json", [item.to_dict() for item in filler_candidates])

    if options.autoeditor_preview:
        run_autoeditor_preview(normalized, paths.work / "01_autoeditor_preview.mp4")

    candidates = [item.to_dict() for item in silence_candidates + filler_candidates]
    task = build_ai_task(transcript, candidates, options.profile.name)
    ai_task_path = paths.work / "ai" / "ai_task_001.json"
    ai_result_path = paths.work / "ai" / "ai_result_001.json"
    write_json(ai_task_path, task)

    raw_decisions: list[dict]
    if options.use_ai:
        call_openai_compatible(ai_task_path, ai_result_path)
        raw_decisions = validate_ai_results(candidates, load_ai_results(ai_result_path))
    else:
        raw_decisions = conservative_local_decisions(candidates)
        write_json(ai_result_path, {"cuts": raw_decisions})

    duration = media_duration(normalized)
    cut_list = build_cut_list(str(normalized), duration, raw_decisions, options.profile.decisions)
    cut_list_path = paths.work / "cuts" / "cut_list.json"
    write_json(cut_list_path, cut_list.to_dict())
    write_review_csv(paths.work / "cuts" / "review_items.csv", cut_list.review_items)
    write_review_html(paths.output / "review_report.html", cut_list.review_items)
    handoff = write_handoff_package(
        cut_list,
        paths.output / "handoff",
        project_name=options.input_path.stem,
        subtitle_enabled=options.subtitle,
    )

    rough_cut = paths.output / "rough_cut.mp4"
    if options.render:
        render_keep_intervals(normalized, cut_list.keep_intervals, rough_cut, paths.work)
        shutil.copyfile(rough_cut, paths.output / "final_clean.mp4")

    if options.subtitle and options.render:
        rough_audio = paths.work / "rough_audio.wav"
        final_subtitles = paths.work / "final_subtitles"
        extract_audio(rough_cut, rough_audio)
        transcribe(rough_audio, final_subtitles, model=options.whisperx_model, language=options.language)
        srt_path = expected_srt_path(rough_audio, final_subtitles)
        json_path = expected_json_path(rough_audio, final_subtitles)
        json_to_srt(json_path, srt_path)
        output_srt = paths.output / "subtitle.srt"
        output_ass = paths.output / "subtitle.ass"
        shutil.copyfile(srt_path, output_srt)
        shutil.copyfile(json_path, paths.output / "subtitle.json")
        srt_to_ass(output_srt, output_ass)
        burn_subtitles(rough_cut, output_ass, paths.output / "final_burned.mp4")

    return {
        "normalized": str(normalized),
        "cut_list": str(cut_list_path),
        "review_report": str(paths.output / "review_report.html"),
        "handoff_dir": handoff["handoff_dir"],
        "fcpxml": handoff["fcpxml"],
        "edit_decisions": handoff["edit_decisions"],
        "rough_cut": str(rough_cut) if options.render else "",
    }


def conservative_local_decisions(candidates: list[dict]) -> list[dict]:
    decisions = []
    for candidate in candidates:
        action = "review"
        confidence = 0.8
        target_duration = None
        if candidate["type"] == "silence" and candidate.get("suggestion") == "compress":
            action = "compress"
            confidence = 0.86
            target_duration = 0.6 if candidate["duration"] >= 3.0 else 0.4
        decision = {
            "start": candidate["start"],
            "end": candidate["end"],
            "action": action,
            "reason": candidate.get("reason", "本地保守规则"),
            "confidence": confidence,
        }
        if target_duration is not None:
            decision["target_duration"] = target_duration
        if candidate.get("speaker"):
            decision["speaker"] = candidate["speaker"]
        if candidate.get("text"):
            decision["text"] = candidate["text"]
        decisions.append(decision)
    return decisions


def run_autoeditor_preview(source: Path, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    run_command(
        [
            "auto-editor",
            str(source),
            "--edit",
            "audio:threshold=4%",
            "--margin",
            "0.25s",
            "-o",
            str(output_path),
        ]
    )


class ProjectPaths:
    def __init__(self, project_dir: Path, input_path: Path) -> None:
        self.project_dir = project_dir
        self.input = project_dir / "input"
        project_name = input_path.stem
        self.work = project_dir / "work" / project_name
        self.output = project_dir / "output" / project_name

    def create(self) -> None:
        for path in [
            self.input,
            self.work,
            self.work / "transcript",
            self.work / "candidates",
            self.work / "ai",
            self.work / "cuts",
            self.work / "clips",
            self.output,
        ]:
            ensure_dir(path)
