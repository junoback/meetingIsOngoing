# Current Sprint

> Updated: 2026-03-24
> Sprint goal: **Polish & remaining features (Sprint 3+)**

## Sprint Tasks

### 1. [P3-01] Streaming WAV download
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Changed to `data=open(file, 'rb')` instead of `f.read()` for memory-efficient streaming

### 2. [P3-03] Keyboard shortcuts
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Ctrl/Cmd+Shift+R/P/S for start/pause/stop via JS injection in `render_keyboard_shortcuts()`

### 3. [P2-04] Session history & review
- **Status**: `[x]` Done (2026-03-24)
- **Result**: History section lists up to 20 transcript files with expandable preview and download buttons

### 4. [P3-02] Allow mode/language switching during recording
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Mode radio, target language, and bilingual toggle now enabled during recording. Audio language and audio settings remain locked. Changes applied to transcriber on the fly via set_mode()/set_target_language().

### 5. [P1-03] Reduce st.rerun() flickering with st.fragment
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Main content area (live feed, status, controls, metrics, transcripts) wrapped in `@st.fragment(run_every=2s)`. Removed `time.sleep(1); st.rerun()` loop. Controls use `st.rerun(scope="app")` for full-page updates. Sidebar stats update on user interaction only.

### 6. [P4-01] Automated test suite
- **Status**: `[x]` Done (2026-03-24)
- **Result**: 126 pytest tests across 4 modules. Covers ConfigManager I/O, templates lookup/data functions, Transcriber modes/API mocking/circuit breaker, AudioRecorder VAD/silence detection. Also fixed a circuit breaker bug (backoff not resetting after half-open success).

## Blocked / Deferred
- P2-05 (speaker diarization) — large effort, high risk, deferred

## Session Handoff Notes
All backlog items complete except P2-05 (speaker diarization — large/risky, intentionally deferred).
The app is feature-complete and has 126 automated tests. Run with: `.venv/bin/python -m pytest tests/ -v`
Future work:
- P2-05 speaker diarization (if needed)
- Performance profiling for long sessions
- Integration/E2E tests (would need Streamlit test harness)
