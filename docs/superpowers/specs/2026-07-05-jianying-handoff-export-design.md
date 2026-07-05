# Jianying Handoff Export Design

## Context

AI Roughcut currently produces a conservative rough cut from interview footage:

- `work/<project>/cuts/cut_list.json` stores source media, executable delete intervals, keep intervals, and review items.
- `output/<project>/rough_cut.mp4` and `final_clean.mp4` provide rendered rough-cut videos when rendering is enabled.
- Optional subtitle output creates `subtitle.srt`, `subtitle.ass`, and `subtitle.json`.

The next workflow step is manual finishing in Jianying/CapCut. Jianying's native draft format is not treated as a stable public interface, so the first export should use maintainable interchange files and a clear handoff package.

## Goals

- Generate a handoff package under `output/<project>/handoff/`.
- Provide a standard timeline interchange file that represents the rough cut as source-media ranges.
- Provide human-readable decision files for review and manual reconstruction.
- Keep the export independent from video rendering so `--no-render` still produces handoff files.
- Preserve all existing outputs and behavior.

## Non-Goals

- Do not generate Jianying native draft directories in this iteration.
- Do not promise that every Jianying/CapCut version can import the interchange file.
- Do not add new external runtime dependencies.
- Do not change the AI decision policy or cut-list generation behavior.

## Proposed Output Files

The pipeline writes these files to `output/<project>/handoff/` after `cut_list.json` is generated:

- `timeline.fcpxml`: A single-track FCPXML timeline built from `keep_intervals`.
- `edit_decisions.csv`: A reviewable table of kept and deleted ranges.
- `import_notes.md`: Practical instructions for using the handoff package in Jianying/CapCut, including fallback steps if XML import is unavailable.

Existing files remain in their current locations, including `rough_cut.mp4`, `final_clean.mp4`, `subtitle.srt`, and `review_report.html`.

## Timeline Export

`timeline.fcpxml` references the normalized source video at `work/<project>/00_normalized.mp4`. Each `keep_interval` becomes a clip on a single primary timeline:

- Clip source start equals the keep interval start.
- Clip duration equals `end - start`.
- Clip timeline offset is cumulative, starting at zero.
- The exported timeline name uses the input stem.
- Times are written with millisecond precision as rational FCPXML time values.

This produces a rough-cut timeline that can be imported by editors that support FCPXML. If Jianying/CapCut rejects the XML, the user still has rendered video and CSV notes.

## Decision CSV

`edit_decisions.csv` includes both kept and deleted ranges:

- `type`: `keep` or `delete`.
- `source_start`, `source_end`, `source_duration`.
- `timeline_start`, `timeline_end`, `timeline_duration` for kept ranges.
- `reason` for deleted ranges.

Deleted ranges do not have timeline positions because they are absent from the rough-cut timeline.

## Import Notes

`import_notes.md` should explain:

- Try importing `timeline.fcpxml` into Jianying/CapCut desktop if the installed version supports timeline XML import.
- If XML import is unsupported, import `rough_cut.mp4` or `final_clean.mp4` and continue finishing manually.
- Use `edit_decisions.csv` and `review_report.html` to inspect what was removed.
- Import `subtitle.srt` if subtitle generation was enabled.
- Keep `work/<project>/00_normalized.mp4` available because the XML references it.

## Code Shape

Add a focused module, likely `src/ai_roughcut/handoff.py`, with pure functions for:

- Building FCPXML text from a `CutList`.
- Building CSV rows from a `CutList`.
- Writing the complete handoff package.

`pipeline.py` should call the handoff writer immediately after `cut_list.json`, review CSV, and review HTML are written. The returned pipeline result should include the handoff directory or key files so the CLI prints them.

## Testing

Add unit tests for the new handoff module:

- Multiple keep intervals become sequential timeline clips with cumulative offsets.
- CSV output reports keep intervals with timeline positions and delete intervals without timeline positions.
- The handoff writer creates all expected files from a small synthetic `CutList`.

Update existing CLI or pipeline-facing tests only if result keys or printed output require it.

## Risks

- Jianying/CapCut XML support can vary by version. The design mitigates this with a rendered-video fallback and explicit import notes.
- FCPXML details can be strict. Tests should verify deterministic XML structure, but real import validation may still require manual testing with the user's installed editor.
