# Current Sprint

> Updated: 2026-03-23
> Sprint goal: **Fix critical bug + improve maintainability**

## Sprint Tasks

### 0. [BUG] Fix settings reset during long recording sessions
- **Status**: `[x]` Done
- **Root cause**: Widget key flip-flopping + slider value= override on rerun
- **Fix**: Unified keyed widgets, init-once pattern, auto-save to config

### 1. [P3-04] Auto-save settings on change
- **Status**: `[x]` Done (merged with bug fix above)
- **Target**: Persist chunk_duration, silence_threshold, selected_device, language, mode on change
- **Implementation**: `_persist_setting_if_changed()` helper, writes to config only on actual change

### 2. [P1-01] Extract CSS from app.py
- **Status**: `[ ]` Not started
- **Target**: Move ~930 lines of CSS to `styles.py`
- **Acceptance**: app.py imports CSS from styles.py, no visual change

### 3. [P1-02] Extract HTML template builders from app.py
- **Status**: `[ ]` Not started
- **Target**: Move template builders to `templates.py`
- **Acceptance**: app.py imports from templates.py, no visual change

### 4. [P1-04] Circuit breaker for API failures
- **Status**: `[ ]` Not started
- **Target**: Add exponential backoff after 3 consecutive failures

## Blocked / Deferred
- P1-03 (st.fragment) deferred to next sprint — needs Streamlit version check first

## Session Handoff Notes
Bug fix and P3-04 complete. Next task: P1-01 (CSS extraction).
