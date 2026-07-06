from pathlib import Path

from ai_roughcut.handoff import (
    build_decision_rows,
    build_fcpxml,
    build_roughcut_recipe,
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


def test_build_roughcut_recipe_describes_source_timeline_and_review_segments(tmp_path):
    cut_list = sample_cut_list(tmp_path)

    recipe = build_roughcut_recipe(cut_list, project_name="demo")

    assert recipe["project"] == "demo"
    assert recipe["source"] == str(Path(cut_list.source).resolve())
    assert recipe["summary"] == {
        "source_duration": 6.25,
        "timeline_duration": 4.75,
        "keep_count": 2,
        "delete_count": 1,
        "review_count": 0,
    }
    assert recipe["segments"] == [
        {
            "index": 1,
            "type": "keep",
            "source_start": 0.0,
            "source_end": 2.5,
            "source_duration": 2.5,
            "timeline_start": 0.0,
            "timeline_end": 2.5,
            "timeline_duration": 2.5,
            "review_required": False,
            "reason": "",
        },
        {
            "index": 2,
            "type": "keep",
            "source_start": 4.0,
            "source_end": 6.25,
            "source_duration": 2.25,
            "timeline_start": 2.5,
            "timeline_end": 4.75,
            "timeline_duration": 2.25,
            "review_required": False,
            "reason": "",
        },
        {
            "index": 3,
            "type": "delete",
            "source_start": 2.5,
            "source_end": 4.0,
            "source_duration": 1.5,
            "timeline_start": None,
            "timeline_end": None,
            "timeline_duration": None,
            "review_required": False,
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
        "roughcut_recipe": str(output_dir / "roughcut_recipe.json"),
        "import_notes": str(output_dir / "import_notes.md"),
    }
    assert (output_dir / "timeline.fcpxml").read_text(encoding="utf-8").startswith("<?xml version=")
    assert "type,source_start,source_end" in (output_dir / "edit_decisions.csv").read_text(encoding="utf-8")
    assert '"segments"' in (output_dir / "roughcut_recipe.json").read_text(encoding="utf-8")
    notes = (output_dir / "import_notes.md").read_text(encoding="utf-8")
    assert "timeline.fcpxml" in notes
    assert "roughcut_recipe.json" in notes
    assert "subtitle.srt" in notes
