# Current Sprint

> Updated: 2026-03-23
> Sprint goal: **Improve maintainability by refactoring app.py monolith**

## Sprint Tasks

### 1. [P1-01] Extract CSS from app.py
- **Status**: `[ ]` Not started
- **Target**: Move ~930 lines of CSS to `styles.py`
- **Acceptance**: app.py imports CSS from styles.py, no visual change

### 2. [P1-02] Extract HTML template builders from app.py
- **Status**: `[ ]` Not started
- **Target**: Move `render_live_feed_panel`, `build_language_panel`, `render_metric_card`, `render_sidebar_summary_card`, `render_transcript_card` to `templates.py`
- **Acceptance**: app.py imports from templates.py, no visual change

### 3. [P1-04] Circuit breaker for API failures
- **Status**: `[ ]` Not started
- **Target**: Add exponential backoff after 3 consecutive failures
- **Acceptance**: After 3 failures, pause 30s→60s→120s, show error state in UI

### 4. [P3-04] Auto-save settings on change
- **Status**: `[ ]` Not started
- **Target**: Persist chunk_duration, silence_threshold, selected_device on change
- **Acceptance**: Settings survive app restart without manual save

## Blocked / Deferred
- P1-03 (st.fragment) deferred to next sprint — needs Streamlit version check first

## Session Handoff Notes
<!-- When ending a session, write what's in progress and next steps here -->
_No active work yet. Next session should start with P1-01 (CSS extraction)._
