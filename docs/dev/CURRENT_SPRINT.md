# Current Sprint

> Updated: 2026-03-24
> Sprint goal: **Feature enhancements (P2)**

## Sprint Tasks

### 1. [P2-03] Terminology dictionary for all target languages
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Removed zh-only guard, prompt now language-agnostic

### 2. [P2-02] SRT/VTT subtitle export
- **Status**: `[x]` Done (2026-03-24)
- **Result**: Added SRT/VTT export with format selector in UI

### 3. [P2-01] Smart VAD for chunking
- **Status**: `[x]` Done (2026-03-24)
- **Target**: Use energy-based VAD to detect speech boundaries, avoid mid-sentence cuts
- **Result**: Energy-based VAD in AudioRecorder. Scans from tail for silence gaps (≥0.3s). Min chunk 3s, max = user setting. Toggleable via sidebar checkbox. No new dependency.

## Blocked / Deferred
- P1-03 (st.fragment) still deferred — needs Streamlit version check

## Session Handoff Notes
P2-01, P2-02, P2-03 all done. Sprint 2 complete.
Remaining P2 tasks: P2-04 (session history), P2-05 (speaker diarization — large/risky).
P3 tasks: P3-01 (streaming WAV), P3-02 (mode switch during recording), P3-03 (keyboard shortcuts).
