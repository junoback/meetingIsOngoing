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
- **Status**: `[x]` Done (2026-03-24)
- **Target**: Move ~930 lines of CSS to `styles.py`
- **Acceptance**: app.py imports CSS from styles.py, no visual change
- **Result**: Created `styles.py` with `get_main_css()`. app.py reduced from 2063 → 1163 lines.

### 3. [P1-02] Extract HTML template builders from app.py
- **Status**: `[x]` Done (2026-03-24)
- **Target**: Move template builders to `templates.py`
- **Acceptance**: app.py imports from templates.py, no visual change
- **Result**: Created `templates.py` (536 lines). Moved constants, lookup helpers, data helpers, and 5 HTML builders. app.py reduced from 2550 → 2063 lines.

### 4. [P1-04] Circuit breaker for API failures
- **Status**: `[x]` Done (2026-03-24)
- **Target**: Add exponential backoff after 3 consecutive failures
- **Result**: Added to `TranscriberWorker`. 3 consecutive failures → circuit open, 10s initial backoff, 2x exponential up to 300s max. Half-open auto-retry on cooldown. UI shows status in sidebar.

## Blocked / Deferred
- P1-03 (st.fragment) deferred to next sprint — needs Streamlit version check first

## Session Handoff Notes
**Sprint complete!** All P1 tasks done:
- P1-01: CSS → styles.py
- P1-02: HTML builders → templates.py
- P1-04: Circuit breaker in TranscriberWorker
- app.py reduced from ~2550 → ~1175 lines

Next sprint should pick from P2 (feature enhancements) in BACKLOG.md.
P1-03 (st.fragment) still deferred — needs Streamlit version check.
