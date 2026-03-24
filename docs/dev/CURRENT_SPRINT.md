# Current Sprint

> Updated: 2026-03-24
> Sprint goal: **Polish & remaining features (Sprint 3)**

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

## Blocked / Deferred
- P1-03 (st.fragment) — Streamlit 1.37.1 confirmed, can implement
- P2-05 (speaker diarization) — large effort, high risk, deferred

## Session Handoff Notes
Sprint 3 complete (all 4 tasks done).
Remaining tasks:
- P1-03 (st.fragment for flicker reduction) — Streamlit 1.37.1 supports it, ready to implement
- P2-05 (speaker diarization) — large effort, high risk
All other backlog items done.
