from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from .io_utils import ensure_dir, write_json
from .models import CutList


DECISION_FIELDNAMES = [
    "type",
    "source_start",
    "source_end",
    "source_duration",
    "timeline_start",
    "timeline_end",
    "timeline_duration",
    "reason",
]


def format_seconds(value: float) -> str:
    return f"{value:.3f}"


def format_fcpxml_time(value: float) -> str:
    milliseconds = round(value * 1000)
    if milliseconds == 0:
        return "0s"
    return f"{milliseconds}/1000s"


def build_fcpxml(cut_list: CutList, project_name: str) -> str:
    source = Path(cut_list.source).resolve()
    source_uri = source.as_uri()
    asset_duration = max((interval.end for interval in cut_list.keep_intervals), default=0.0)
    sequence_duration = sum(max(0.0, interval.end - interval.start) for interval in cut_list.keep_intervals)
    timeline_offset = 0.0
    clips: list[str] = []
    for index, interval in enumerate(cut_list.keep_intervals, start=1):
        duration = max(0.0, interval.end - interval.start)
        clips.append(
            " " * 12
            + (
                f'<asset-clip name="{index:03d}" ref="r1" '
                f'offset="{format_fcpxml_time(timeline_offset)}" '
                f'start="{format_fcpxml_time(interval.start)}" '
                f'duration="{format_fcpxml_time(duration)}"/>'
            )
        )
        timeline_offset += duration
    clip_xml = "\n".join(clips)
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<!DOCTYPE fcpxml>",
            '<fcpxml version="1.10">',
            "  <resources>",
            (
                f'    <asset id="r1" name="{escape(source.name)}" '
                f'start="0s" duration="{format_fcpxml_time(asset_duration)}" '
                f'hasVideo="1" hasAudio="1" format="r2">'
            ),
            f'      <media-rep kind="original-media" src="{escape(source_uri)}"/>',
            "    </asset>",
            '    <format id="r2" name="FFVideoFormat1080p30" frameDuration="100/3000s" width="1920" height="1080"/>',
            "  </resources>",
            "  <library>",
            '    <event name="AI Roughcut">',
            f'      <project name="{escape(project_name)}">',
            f'        <sequence duration="{format_fcpxml_time(sequence_duration)}" format="r2">',
            "          <spine>",
            clip_xml,
            "          </spine>",
            "        </sequence>",
            "      </project>",
            "    </event>",
            "  </library>",
            "</fcpxml>",
            "",
        ]
    )


def build_decision_rows(cut_list: CutList) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    timeline_cursor = 0.0
    for interval in cut_list.keep_intervals:
        duration = max(0.0, interval.end - interval.start)
        rows.append(
            {
                "type": "keep",
                "source_start": format_seconds(interval.start),
                "source_end": format_seconds(interval.end),
                "source_duration": format_seconds(duration),
                "timeline_start": format_seconds(timeline_cursor),
                "timeline_end": format_seconds(timeline_cursor + duration),
                "timeline_duration": format_seconds(duration),
                "reason": "",
            }
        )
        timeline_cursor += duration
    for interval in cut_list.edit_intervals:
        duration = max(0.0, interval.end - interval.start)
        rows.append(
            {
                "type": "delete",
                "source_start": format_seconds(interval.start),
                "source_end": format_seconds(interval.end),
                "source_duration": format_seconds(duration),
                "timeline_start": "",
                "timeline_end": "",
                "timeline_duration": "",
                "reason": interval.reason,
            }
        )
    return rows


def build_roughcut_recipe(cut_list: CutList, project_name: str) -> dict:
    timeline_cursor = 0.0
    segments: list[dict] = []
    for interval in cut_list.keep_intervals:
        duration = round(max(0.0, interval.end - interval.start), 3)
        timeline_start = round(timeline_cursor, 3)
        timeline_end = round(timeline_cursor + duration, 3)
        segments.append(
            {
                "index": len(segments) + 1,
                "type": "keep",
                "source_start": round(interval.start, 3),
                "source_end": round(interval.end, 3),
                "source_duration": duration,
                "timeline_start": timeline_start,
                "timeline_end": timeline_end,
                "timeline_duration": duration,
                "review_required": False,
                "reason": "",
            }
        )
        timeline_cursor += duration
    for interval in cut_list.edit_intervals:
        segments.append(
            {
                "index": len(segments) + 1,
                "type": "delete",
                "source_start": round(interval.start, 3),
                "source_end": round(interval.end, 3),
                "source_duration": round(max(0.0, interval.end - interval.start), 3),
                "timeline_start": None,
                "timeline_end": None,
                "timeline_duration": None,
                "review_required": False,
                "reason": interval.reason,
            }
        )
    for item in cut_list.review_items:
        segments.append(
            {
                "index": len(segments) + 1,
                "type": "review",
                "source_start": round(item.start, 3),
                "source_end": round(item.end, 3),
                "source_duration": round(max(0.0, item.end - item.start), 3),
                "timeline_start": None,
                "timeline_end": None,
                "timeline_duration": None,
                "review_required": True,
                "reason": item.reason,
                "confidence": None if item.confidence is None else round(item.confidence, 3),
                "speaker": item.speaker,
                "text": item.text,
            }
        )
    return {
        "project": project_name,
        "source": str(Path(cut_list.source).resolve()),
        "summary": {
            "source_duration": _source_duration(cut_list),
            "timeline_duration": round(timeline_cursor, 3),
            "keep_count": len(cut_list.keep_intervals),
            "delete_count": len(cut_list.edit_intervals),
            "review_count": len(cut_list.review_items),
        },
        "segments": segments,
    }


def _source_duration(cut_list: CutList) -> float:
    ends = [item.end for item in cut_list.keep_intervals]
    ends.extend(item.end for item in cut_list.edit_intervals)
    ends.extend(item.end for item in cut_list.review_items)
    return round(max(ends, default=0.0), 3)


def build_import_notes(project_name: str, subtitle_enabled: bool) -> str:
    subtitle_note = (
        "- If subtitle generation was enabled, import `../subtitle.srt` for editable captions."
        if subtitle_enabled
        else "- No subtitle file is expected unless you rerun with `--subtitle`."
    )
    return "\n".join(
        [
            f"# {project_name} Jianying Handoff",
            "",
            "Files in this folder:",
            "",
            "- `timeline.fcpxml`: Try importing this first in Jianying/CapCut desktop if your version supports XML timeline import.",
            "- `edit_decisions.csv`: Reviewable source and timeline timecodes for kept and removed ranges.",
            "- `roughcut_recipe.json`: Machine-readable rough-cut recipe with source ranges, timeline ranges, and review markers.",
            "- `import_notes.md`: This guide.",
            "",
            "Fallback workflow:",
            "",
            "- If XML import is unavailable, import `../rough_cut.mp4` or `../final_clean.mp4` and continue editing manually.",
            "- Use `edit_decisions.csv` with `../review_report.html` to inspect what AI Roughcut removed.",
            subtitle_note,
            "- Keep the `work/<project>/00_normalized.mp4` source available because `timeline.fcpxml` references it.",
            "",
        ]
    )


def write_handoff_package(
    cut_list: CutList,
    output_dir: Path,
    project_name: str,
    subtitle_enabled: bool,
) -> dict[str, str]:
    ensure_dir(output_dir)
    fcpxml_path = output_dir / "timeline.fcpxml"
    decisions_path = output_dir / "edit_decisions.csv"
    recipe_path = output_dir / "roughcut_recipe.json"
    notes_path = output_dir / "import_notes.md"
    fcpxml_path.write_text(build_fcpxml(cut_list, project_name), encoding="utf-8")
    with decisions_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=DECISION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(build_decision_rows(cut_list))
    write_json(recipe_path, build_roughcut_recipe(cut_list, project_name))
    notes_path.write_text(build_import_notes(project_name, subtitle_enabled), encoding="utf-8")
    return {
        "handoff_dir": str(output_dir),
        "fcpxml": str(fcpxml_path),
        "edit_decisions": str(decisions_path),
        "roughcut_recipe": str(recipe_path),
        "import_notes": str(notes_path),
    }
