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

## Blocked / Deferred
- P1-03 (st.fragment) — needs Streamlit version check
- P2-05 (speaker diarization) — large effort, high risk, deferred

## Session Handoff Notes
Sprint 3 complete. P3-01, P3-03, P2-04 all done.
Remaining tasks:
- P3-02 (mode switch during recording) — medium effort, medium risk (thread safety)
- P2-05 (speaker diarization) — large effort, high risk
- P1-03 (st.fragment for flicker reduction) — deferred, needs version check
