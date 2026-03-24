# Current Sprint

> Updated: 2026-03-24
> Sprint goal: **Sprint 6 — Polish, bug fixes, memory management**

## Sprint Tasks

### 1. [S6-01] Fix terminology zh-only guard
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Removed `if target_language == "zh"` guard in `start_recording()`. Terminology dictionary now loaded for all target languages, as P2-03 intended.

### 2. [S6-02] Replace remaining print() with logger
- **Status**: `[x]` Done (2026-03-24)
- **Result**: 3 remaining `print()` calls in app.py replaced with `logger.info()` / `logger.error()`. Now zero print() in production code.

### 3. [S6-03] Settings auto-persist on change
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Added `_persist_setting_if_changed()` with `_last_persisted` cache to avoid redundant disk I/O. Auto-saves: language, target_language, mode, selected_device, chunk_duration, silence_threshold, vad_enabled, show_bilingual.

### 4. [S6-04] Transcript memory cap for long sessions
- **Status**: `[x]` Done (2026-03-24)
- **Result**: ProcessingController.MAX_IN_MEMORY_TRANSCRIPTS = 500. Older transcripts evicted from memory but preserved in live transcript file. `total_transcript_count` tracks full count.

### 5. [S6-05] Fix history download bug
- **Status**: `[x]` Done (2026-03-24)
- **Result**: `preview` variable now initialized to None before try block. Download button only shown if file was successfully read.

### 6. Tests
- **Status**: `[x]` 147 total (+5 new for memory cap and auto-persist)

## Previous Sprints (completed)
- Sprint 3: P3-01, P3-03, P2-04, P3-02, P1-03
- Sprint 4: P4-01 (automated test suite)
- Sprint 5: S5-01–S5-06 (long session stability)

## Blocked / Deferred
- P2-05 (speaker diarization) — large effort, high risk, deferred

## Session Handoff Notes
Sprint 6 complete. All settings now auto-persist. Terminology works for all languages.
147 automated tests. Run with: `.venv/bin/python -m pytest tests/ -v`
Future work:
- P2-05 speaker diarization (if needed)
- Integration/E2E tests (would need Streamlit test harness)
- Meeting summary generation (GPT-based post-session summary)
- Auto-detect BlackHole audio device availability
