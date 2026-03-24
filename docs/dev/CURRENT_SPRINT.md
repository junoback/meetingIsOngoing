# Current Sprint

> Updated: 2026-03-24
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
- **Status**: `[x]` Done (2026-03-24)
- **Target**: Move template builders to `templates.py`
- **Acceptance**: app.py imports from templates.py, no visual change
- **Result**: Created `templates.py` (536 lines). Moved constants, lookup helpers, data helpers, and 5 HTML builders. app.py reduced from 2550 → 2063 lines.

### 4. [P1-04] Circuit breaker for API failures
- **Status**: `[ ]` Not started
- **Target**: Add exponential backoff after 3 consecutive failures

## Blocked / Deferred
- P1-03 (st.fragment) deferred to next sprint — needs Streamlit version check first

## Session Handoff Notes
P1-02 (HTML template extraction) complete. templates.py now holds all HTML builders, constants, lookup/data helpers.
app.py still has ~930 lines of inline CSS (P1-01 not yet done) and main() UI logic.
Next task: P1-01 (CSS extraction) or P1-04 (circuit breaker).
