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
- **Status**: `[ ]`
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
- **Status**: `[ ]`
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
- **Status**: `[ ]`
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
- **Status**: `[ ]`
- **Why**: `f.read()` loads entire WAV into memory; problematic for 2+ hour meetings.
- **Plan**: Use `st.download_button` with file path or chunked reading.
- **Effort**: Small
- **Risk**: Low

### P3-02: Allow mode switching during recording
- **Status**: `[ ]`
- **Why**: Currently all sidebar controls are disabled during recording.
- **Plan**: Allow mode/language change mid-session by updating transcriber settings on the fly.
- **Effort**: Medium
- **Risk**: Medium (thread safety for mode changes)

### P3-03: Keyboard shortcuts
- **Status**: `[ ]`
- **Why**: Start/stop/pause require mouse clicks.
- **Plan**: Add JS-based keyboard shortcuts (e.g., Space=pause, Escape=stop).
- **Effort**: Small
- **Risk**: Low

### P3-04: Auto-save settings on change
- **Status**: `[x]` Done (2026-03-23)

---

## Completed

### BUG: Settings reset during long recording sessions (2026-03-23)
- **Root cause**: Streamlit widget key flip-flopping + slider value= override during rerun loop
- **Fix**: Unified keyed widgets for recording/non-recording, init-once pattern, auto-save to config
- **Also completed**: P3-04 (auto-save settings) was merged into this fix
