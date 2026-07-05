# Jianying Handoff Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export a Jianying/CapCut-friendly handoff package with FCPXML, CSV edit decisions, and import notes after each rough-cut run.

**Architecture:** Add a focused `ai_roughcut.handoff` module that converts the existing `CutList` model into interchange artifacts. Keep the pipeline integration thin: after `cut_list.json` and review files are written, call the handoff writer and include the handoff path in CLI output.

**Tech Stack:** Python standard library (`csv`, `html`, `pathlib`), existing dataclasses in `ai_roughcut.models`, pytest.

---

## File Structure

- Create `src/ai_roughcut/handoff.py`: Pure conversion and writer functions for `timeline.fcpxml`, `edit_decisions.csv`, and `import_notes.md`.
- Create `tests/test_handoff.py`: Unit tests for FCPXML generation, CSV rows, and file writing.
- Modify `src/ai_roughcut/pipeline.py`: Call `write_handoff_package` after cut-list and review output are created, and return the handoff directory.
- Modify `README.md`: Document the new handoff outputs and the Jianying/CapCut workflow.

## Task 1: Add Handoff Unit Tests

**Files:**
- Create: `tests/test_handoff.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_handoff.py` with:

```python
from pathlib import Path

from ai_roughcut.handoff import (
    build_decision_rows,
    build_fcpxml,
    format_fcpxml_time,
    write_handoff_package,
)
from ai_roughcut.models import CutList, EditInterval, KeepInterval


def sample_cut_list(tmp_path: Path) -> CutList:
    source = tmp_path / "work" / "demo" / "00_normalized.mp4"
    source.parent.mkdir(parents=True)
    source.write_text("fake video fixture", encoding="utf-8")
    return CutList(
        source=str(source),
        keep_intervals=[
            KeepInterval(start=0.0, end=2.5),
            KeepInterval(start=4.0, end=6.25),
        ],
        edit_intervals=[
            EditInterval(start=2.5, end=4.0, kind="delete", reason="长空白"),
        ],
    )


def test_format_fcpxml_time_uses_millisecond_rationals():
    assert format_fcpxml_time(0.0) == "0s"
    assert format_fcpxml_time(2.5) == "2500/1000s"
    assert format_fcpxml_time(6.25) == "6250/1000s"


def test_build_fcpxml_creates_sequential_timeline_clips(tmp_path):
    cut_list = sample_cut_list(tmp_path)

    xml = build_fcpxml(cut_list, project_name="demo")

    assert '<project name="demo">' in xml
    assert 'name="001"' in xml
    assert 'offset="0s"' in xml
    assert 'start="0s"' in xml
    assert 'duration="2500/1000s"' in xml
    assert 'name="002"' in xml
    assert 'offset="2500/1000s"' in xml
    assert 'start="4000/1000s"' in xml
    assert 'duration="2250/1000s"' in xml
    assert str(Path(cut_list.source).resolve().as_uri()) in xml


def test_build_decision_rows_includes_keep_timeline_positions_and_delete_reasons(tmp_path):
    cut_list = sample_cut_list(tmp_path)

    rows = build_decision_rows(cut_list)

    assert rows == [
        {
            "type": "keep",
            "source_start": "0.000",
            "source_end": "2.500",
            "source_duration": "2.500",
            "timeline_start": "0.000",
            "timeline_end": "2.500",
            "timeline_duration": "2.500",
            "reason": "",
        },
        {
            "type": "keep",
            "source_start": "4.000",
            "source_end": "6.250",
            "source_duration": "2.250",
            "timeline_start": "2.500",
            "timeline_end": "4.750",
            "timeline_duration": "2.250",
            "reason": "",
        },
        {
            "type": "delete",
            "source_start": "2.500",
            "source_end": "4.000",
            "source_duration": "1.500",
            "timeline_start": "",
            "timeline_end": "",
            "timeline_duration": "",
            "reason": "长空白",
        },
    ]


def test_write_handoff_package_creates_expected_files(tmp_path):
    cut_list = sample_cut_list(tmp_path)
    output_dir = tmp_path / "output" / "demo" / "handoff"

    result = write_handoff_package(cut_list, output_dir, project_name="demo", subtitle_enabled=True)

    assert result == {
        "handoff_dir": str(output_dir),
        "fcpxml": str(output_dir / "timeline.fcpxml"),
        "edit_decisions": str(output_dir / "edit_decisions.csv"),
        "import_notes": str(output_dir / "import_notes.md"),
    }
    assert (output_dir / "timeline.fcpxml").read_text(encoding="utf-8").startswith("<?xml version=")
    assert "type,source_start,source_end" in (output_dir / "edit_decisions.csv").read_text(encoding="utf-8")
    notes = (output_dir / "import_notes.md").read_text(encoding="utf-8")
    assert "timeline.fcpxml" in notes
    assert "subtitle.srt" in notes
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_handoff.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ai_roughcut.handoff'`.

## Task 2: Implement Handoff Module

**Files:**
- Create: `src/ai_roughcut/handoff.py`
- Test: `tests/test_handoff.py`

- [ ] **Step 1: Add minimal implementation**

Create `src/ai_roughcut/handoff.py` with:

```python
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
            '<!DOCTYPE fcpxml>',
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
```

- [ ] **Step 2: Run handoff tests**

Run:

```bash
python -m pytest tests/test_handoff.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit handoff module**

Run:

```bash
git add src/ai_roughcut/handoff.py tests/test_handoff.py
git commit -m "feat: add Jianying handoff export files"
```

## Task 3: Integrate Handoff Export Into Pipeline

**Files:**
- Modify: `src/ai_roughcut/pipeline.py`
- Test: existing full test suite

- [ ] **Step 1: Modify pipeline imports and call site**

In `src/ai_roughcut/pipeline.py`, add:

```python
from .handoff import write_handoff_package
```

After:

```python
write_review_csv(paths.work / "cuts" / "review_items.csv", cut_list.review_items)
write_review_html(paths.output / "review_report.html", cut_list.review_items)
```

Add:

```python
handoff = write_handoff_package(
    cut_list,
    paths.output / "handoff",
    project_name=options.input_path.stem,
    subtitle_enabled=options.subtitle,
)
```

In the return dict, add:

```python
"handoff_dir": handoff["handoff_dir"],
"fcpxml": handoff["fcpxml"],
"edit_decisions": handoff["edit_decisions"],
```

- [ ] **Step 2: Run full tests**

Run:

```bash
python -m pytest
```

Expected: PASS.

- [ ] **Step 3: Commit pipeline integration**

Run:

```bash
git add src/ai_roughcut/pipeline.py
git commit -m "feat: export handoff package from pipeline"
```

## Task 4: Document Jianying Handoff Workflow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update output tree**

In the README output tree, under `output/`, add:

```text
│   └── handoff/
│       ├── timeline.fcpxml
│       ├── edit_decisions.csv
│       └── import_notes.md
```

- [ ] **Step 2: Update run/output docs**

Add a short subsection near the output list:

```markdown
### 剪映 / CapCut 后续精剪

每次生成 `cut_list.json` 后，项目会额外写入 `output/<素材名>/handoff/`：

- `timeline.fcpxml`: 基于保留片段生成的单轨时间线，可优先尝试导入支持 FCPXML/XML 的剪映或 CapCut 桌面版。
- `edit_decisions.csv`: 保留和删除片段的源时间码、时间线时间码和删除原因。
- `import_notes.md`: 导入建议和 XML 不兼容时的兜底流程。

如果当前剪映版本不能导入 XML，可以直接导入 `rough_cut.mp4` 或 `final_clean.mp4`，再参考 `edit_decisions.csv`、`review_report.html` 和可选的 `subtitle.srt` 继续精剪。
```

- [ ] **Step 3: Run tests after docs change**

Run:

```bash
python -m pytest
```

Expected: PASS.

- [ ] **Step 4: Commit docs**

Run:

```bash
git add README.md
git commit -m "docs: describe Jianying handoff workflow"
```

## Task 5: Final Verification

**Files:**
- Review all changed files

- [ ] **Step 1: Check git status**

Run:

```bash
git status --short --branch
```

Expected: branch is ahead of origin with no uncommitted changes.

- [ ] **Step 2: Run full test suite**

Run:

```bash
python -m pytest
```

Expected: PASS.

- [ ] **Step 3: Review recent commits**

Run:

```bash
git log --oneline -5
```

Expected: includes the design, handoff module, pipeline integration, and docs commits.
