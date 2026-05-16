# Current Sprint

> Updated: 2026-05-14
> Sprint goal: **Sprint 6 — Polish, bug fixes, memory management** (complete; post-sprint maintenance ongoing)

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

### Latest (2026-05-14)
Translation lag fix — pushed to GitHub:
- `11716b1` Skip English intermediate LLM call when STT lacks
  `audio.translations` AND target ≠ en. Pipeline drops from 1 STT + 2 LLM
  to 1 STT + 1 LLM per chunk on Groq + non-EN target. Should resolve the
  ~4 min queue accumulation lag reported on 1-2 hr meetings with
  Groq + DeepSeek defaults.
- 149 tests pass (147 prior + 2 new for the optimized path).
- Verified `deepseek-chat` already auto-maps to **DeepSeek-V4-Flash
  non-thinking mode** (newest cheap model). No off-peak discount currently.

### Pickup point for next session
Two queued items (user requested order: do P3-05 next):

**1. P3-05 SRT relative timestamps (NEW — primary)**:
User wants to record YouTube lectures via BlackHole, get translation, then
overlay `.srt` on the video for re-watching. Existing SRT export
(`app.py:577-628`) emits absolute clock time, breaking video subtitle use
case. Fix: compute time relative to recording start. Full plan in
`BACKLOG.md` → P3-05. Small scope, ~1 hour of work.

**2. OpenAI speed comparison (queued from 2026-05-14, deferred)**:
Test OpenAI (Whisper + GPT-4o-mini) as a speed baseline vs Groq + DeepSeek
after `11716b1` fix. Manual sidebar switch only, no code change needed. Look
at `transcripts/<meeting>.txt` per-line `(延遲：X.XX秒)` values to compare.

### Prior (2026-05-11)
Two bug fixes for Streamlit rerun model: `6e48ceb` (stale marker auto-Viewer
+ transcript server bind warning) and `73a55a7` (set Groq + DeepSeek as
bundled defaults). Key finding: `st.rerun(scope="app")` resets module
globals; use `sys` attributes for process-level state.

### Prior (Sprint 6, 2026-03-24)
Sprint 6 complete. All settings now auto-persist. Terminology works for all
languages.

### Future work / open ideas
- P2-05 speaker diarization (if needed)
- Integration/E2E tests (would need Streamlit test harness)
- Meeting summary generation (GPT-based post-session summary)
- Auto-detect BlackHole audio device availability
- Optional chunk-level timing logger (STT-time / LLM-time / queue-wait per
  chunk) for diagnosing future provider-comparison questions. Defer until
  needed.
- Optional: restructure translation system_prompt for DeepSeek cache-hit
  optimization (~50× cheaper input). Pure cost play, not speed. User said
  cost is not a concern, so low priority.
- `_last_persisted` cache in app.py resets on scope="app" rerun (silently
  inefficient but not broken) — same sys-attribute pattern would fix it
  if we ever care about the tiny extra config_manager.get_setting() calls.
