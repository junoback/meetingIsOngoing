# Development Backlog

> Last updated: 2026-03-23
> Status legend: `[ ]` todo, `[~]` in progress, `[x]` done, `[!]` blocked

---

## Priority 1 — Stability & Maintainability

### P1-01: Extract CSS from app.py
- **Status**: `[x]` Done (2026-03-24)
- **Why**: app.py has ~930 lines of CSS inline. Hard to maintain, slows code navigation.
- **Plan**: Move to `styles.py` as a function returning CSS string, or external `.css` loaded at runtime.
- **Effort**: Small
- **Risk**: Low

### P1-02: Extract HTML template builders from app.py
- **Status**: `[x]` Done (2026-03-24)
- **Why**: `render_live_feed_panel()` alone is ~200 lines of HTML/CSS/JS. Multiple `build_*` functions embed large HTML blocks.
- **Plan**: Create `templates.py` with all HTML builder functions.
- **Effort**: Medium
- **Risk**: Low (pure extraction, no behavior change)

### P1-03: Reduce st.rerun() flickering
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Full page re-render every 1 second causes visible UI flicker during recording.
- **Plan**: Investigate `st.fragment` (available since Streamlit 1.33) for partial re-renders of just the transcript area and status panel. Alternatively, increase refresh interval to 2-3 seconds with client-side JS updates for the feed panel.
- **Effort**: Medium
- **Risk**: Medium (Streamlit fragment API may have limitations)

### P1-04: Circuit breaker for API failures
- **Status**: `[x]` Done (2026-03-24)
- **Why**: If OpenAI API goes down, the app keeps retrying every chunk without escalating backoff.
- **Plan**: After N consecutive failures, pause API calls for exponential backoff period. Show clear error state in UI.
- **Effort**: Small
- **Risk**: Low

---

## Priority 2 — Feature Enhancements

### P2-01: Smart voice activity detection (VAD) for chunking
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Fixed 5-10s chunks often cut mid-sentence, hurting translation quality.
- **Plan**: Use `silero-vad` or energy-based VAD to detect speech boundaries. Fall back to max chunk length (15s) if no pause detected.
- **Effort**: Medium-Large
- **Risk**: Medium (new dependency, tuning needed)

### P2-02: SRT/VTT subtitle export
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Users may want to import transcripts into video editing tools.
- **Plan**: Add SRT and VTT export options alongside existing TXT.
- **Effort**: Small
- **Risk**: Low

### P2-03: Terminology dictionary for all target languages
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Currently terminology is only applied when target_language == "zh".
- **Plan**: Remove the "zh" guard in transcriber.py, adjust prompt to be language-agnostic.
- **Effort**: Small
- **Risk**: Low

### P2-04: Session history & review
- **Status**: `[x]` Done (2026-03-24)
- **Why**: No way to review past meeting transcripts within the app.
- **Plan**: Add a "History" tab that lists saved transcript files with preview.
- **Effort**: Medium
- **Risk**: Low

### P2-05: Speaker diarization
- **Status**: `[ ]`
- **Why**: All audio mixed together, no way to tell who said what.
- **Plan**: Evaluate pyannote-audio or simple energy-based segmentation. Complex feature.
- **Effort**: Large
- **Risk**: High (accuracy, latency, dependency weight)

---

## Priority 3 — Polish & Nice-to-have

### P3-01: Streaming WAV download
- **Status**: `[x]` Done (2026-03-24)
- **Why**: `f.read()` loads entire WAV into memory; problematic for 2+ hour meetings.
- **Plan**: Use `st.download_button` with file path or chunked reading.
- **Effort**: Small
- **Risk**: Low

### P3-02: Allow mode switching during recording
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Currently all sidebar controls are disabled during recording.
- **Plan**: Allow mode/language change mid-session by updating transcriber settings on the fly.
- **Effort**: Medium
- **Risk**: Medium (thread safety for mode changes)

### P3-03: Keyboard shortcuts
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Start/stop/pause require mouse clicks.
- **Plan**: Add JS-based keyboard shortcuts (e.g., Space=pause, Escape=stop).
- **Effort**: Small
- **Risk**: Low

### P3-04: Auto-save settings on change
- **Status**: `[x]` Done (2026-03-23)

### P3-05: SRT/VTT relative timestamps for video subtitle overlay
- **Status**: `[ ]` planned (2026-05-16)
- **Why**: User want to overlay generated translation as subtitle on a YouTube
  recording. Records audio via BlackHole while watching YT, then plays the
  recorded audio (or original video) with the generated `.srt` loaded in VLC
  or YT to see Chinese subtitles. Current SRT export emits absolute clock
  time (e.g. `14:30:05,000 --> 14:30:10,000`) via `_timestamp_to_seconds()`
  at `app.py:80-92`, which makes the SRT unusable for video overlay (player
  interprets it as "starts 14.5 hours into the video").
- **Plan**:
  1. Modify `save_transcript_to_srt` / `save_transcript_to_vtt` (app.py:577-628)
     to compute times relative to recording start (= first chunk timestamp,
     or read `started_at` from `_write_active_session_marker` if available).
  2. Either add a second time-mode option ("Absolute clock" vs "Relative to
     recording start") OR just switch to relative — absolute is rarely useful
     for SRT/VTT (those formats assume relative time by spec).
  3. Optional UI: add a "Subtitle time offset (seconds, +/-)" field so user
     can nudge timing if YT-play and Record-start were not pressed exactly
     together. Could even support negative offset (trim leading silence).
  4. Consider merging adjacent short VAD chunks (< 1.5s gap) into one
     subtitle line to reduce subtitle flicker on playback. Optional polish.
- **Effort**: Small (the data — chunk timestamp + duration — already exists)
- **Risk**: Low

---

## Priority 5 — Long Session Stability (Sprint 5)

### S5-01: Fix file handle leaks in download buttons
- **Status**: `[x]` Done (2026-03-24)
- **Why**: `open(file, 'rb')` passed directly to `st.download_button` leaks file descriptors.
- **Fix**: Use `with open()` or reuse already-read content.

### S5-02: Extract shared filename sanitizer
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Same `.replace("/", "-").replace(...)` chain duplicated 4 times across export functions.
- **Fix**: New `sanitize_filename()` utility function, handles more special chars.

### S5-03: Structured logging (replace print spam)
- **Status**: `[x]` Done (2026-03-24)
- **Why**: 10+ prints/second during recording → 72K+ lines in 2-hour session, hard to find real errors.
- **Fix**: Replaced all `print()` with Python `logging` module. High-frequency messages at DEBUG level.

### S5-04: ProcessingController error recovery
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Generic catch-all with `time.sleep(1)` silently swallows errors; user never informed.
- **Fix**: Exponential backoff on consecutive errors, errors propagated to UI via error_messages list.

### S5-05: Audio device fallback warning
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Silent fallback to system default mic → may record keyboard/ambient noise instead of meeting.
- **Fix**: Changed from `st.warning` to `st.error` with clear instructions about BlackHole 2ch.

### S5-06: Cross-midnight SRT/VTT timecodes
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Meetings spanning midnight produce backward-jumping timecodes.
- **Fix**: `_timestamp_to_seconds()` now accepts reference_date for day-offset calculation.

---

## Priority 4 — Infrastructure

### P4-01: Automated test suite
- **Status**: `[x]` Done (2026-03-24)
- **Why**: No automated tests existed. Manual testing only via streamlit run.
- **Plan**: Add pytest suite covering config_manager, templates, transcriber, audio_recorder.
- **Effort**: Medium
- **Risk**: Low
- **Result**: 126 tests across 4 test files, covering config I/O, language lookups, VAD logic, circuit breaker, API mocking. Also found and fixed a circuit breaker backoff reset bug.

---

## Sprint 6 — Polish & Bug Fixes

### S6-01: Fix terminology zh-only guard
- **Status**: `[x]` Done (2026-03-24)
- **Why**: P2-03 marked done but `target_language == "zh"` guard remained in app.py `start_recording()`.
- **Fix**: Removed guard; terminology dictionary now loaded unconditionally for all target languages.

### S6-02: Replace remaining print() with logger
- **Status**: `[x]` Done (2026-03-24)
- **Why**: 3 print() calls remained in app.py (add_debug_log, add_error_message, ProcessingController.start).
- **Fix**: Replaced with logger.info() / logger.error().

### S6-03: Settings auto-persist on change
- **Status**: `[x]` Done (2026-03-24)
- **Why**: Sidebar widget changes (language, mode, device, etc.) not saved to config.json between sessions.
- **Fix**: `_persist_setting_if_changed()` with `_last_persisted` cache. 8 settings auto-saved.

### S6-04: Transcript memory cap for long sessions
- **Status**: `[x]` Done (2026-03-24)
- **Why**: `controller.transcripts` list grows unbounded; 4+ hour sessions risk memory exhaustion.
- **Fix**: MAX_IN_MEMORY_TRANSCRIPTS=500. Older entries evicted from memory; all data preserved in live transcript file.

### S6-05: Fix history download bug
- **Status**: `[x]` Done (2026-03-24)
- **Why**: `preview` variable used in download_button could be undefined if file read raised an exception.
- **Fix**: Initialize `preview=None`, only render download button if read succeeded.

---

## Completed

### BUG: Settings reset during long recording sessions (2026-03-23)
- **Root cause**: Streamlit widget key flip-flopping + slider value= override during rerun loop
- **Fix**: Unified keyed widgets for recording/non-recording, init-once pattern, auto-save to config
- **Also completed**: P3-04 (auto-save settings) was merged into this fix
