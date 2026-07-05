from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from .io_utils import ensure_dir
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
    notes_path = output_dir / "import_notes.md"
    fcpxml_path.write_text(build_fcpxml(cut_list, project_name), encoding="utf-8")
    with decisions_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=DECISION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(build_decision_rows(cut_list))
    notes_path.write_text(build_import_notes(project_name, subtitle_enabled), encoding="utf-8")
    return {
        "handoff_dir": str(output_dir),
        "fcpxml": str(fcpxml_path),
        "edit_decisions": str(decisions_path),
        "import_notes": str(notes_path),
    }
