# AI Roughcut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python CLI that creates a conservative, reviewable rough cut for Chinese interview footage.

**Architecture:** The CLI coordinates small modules for normalization, transcription, candidate detection, Kimi decisions, cut-list generation, ffmpeg rendering, subtitles, and review reports. Pure editing-policy logic is isolated and covered by unit tests; external tools are invoked through subprocess wrappers.

**Tech Stack:** Python 3.10+, ffmpeg, WhisperX CLI, Auto-Editor CLI as optional preview, Moonshot/Kimi through the OpenAI-compatible SDK, pytest.

---

### Task 1: Project Skeleton And Policy Logic

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/ai_roughcut/models.py`
- Create: `src/ai_roughcut/config.py`
- Create: `src/ai_roughcut/silence.py`
- Create: `src/ai_roughcut/fillers.py`
- Create: `tests/test_silence.py`
- Create: `tests/test_fillers.py`

- [x] Create package and directory structure.
- [x] Implement conservative silence classification.
- [x] Implement filler-word candidate extraction from WhisperX-style JSON.
- [x] Add unit tests for both modules.

### Task 2: Decision Merge And Output Contracts

**Files:**
- Create: `src/ai_roughcut/decisions.py`
- Create: `tests/test_decisions.py`

- [x] Convert Kimi actions into executable edit intervals.
- [x] Enforce confidence thresholds and keep/review behavior.
- [x] Merge nearby cuts and generate keep intervals.
- [x] Add unit tests for delete, compress, review, and merging.

### Task 3: Tool Wrappers And Pipeline

**Files:**
- Create: `src/ai_roughcut/ffmpeg_ops.py`
- Create: `src/ai_roughcut/whisperx_ops.py`
- Create: `src/ai_roughcut/kimi.py`
- Create: `src/ai_roughcut/subtitles.py`
- Create: `src/ai_roughcut/reports.py`
- Create: `src/ai_roughcut/pipeline.py`
- Create: `src/ai_roughcut/cli.py`
- Create: `roughcut.py`

- [x] Add subprocess wrappers for ffmpeg, WhisperX, and Auto-Editor preview.
- [x] Add optional Kimi call guarded by `--kimi` and `MOONSHOT_API_KEY`.
- [x] Add report generation for CSV and HTML review.
- [x] Wire stages into the command-line entry point.

### Task 4: Documentation And Verification

**Files:**
- Create: `README.md`

- [x] Document install, external tool prerequisites, command examples, and outputs.
- [x] Run `python -m pytest`.
