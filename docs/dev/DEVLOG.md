# Development Log

> Chronological record of development sessions. Newest entries at the top.
> Each entry records: date, what was done, issues encountered, decisions made.

---

## 2026-03-23 — Session: Bug Fix + Dev Infrastructure + Skills

### What was done (continued)
- **Fixed critical bug**: Settings reset during long recording sessions
  - Root cause 1: Language/mode widgets used keyless disabled variants during recording → values drifted on rerun
  - Root cause 2: Slider `value=config_manager.get_setting()` passed every rerun → overrode user's selection
  - Fix: Unified keyed widgets, `_init_once()` pattern, `_persist_setting_if_changed()` auto-save
- **Completed P3-04**: All settings now auto-saved to config.json on change
- **Created global Skills**: `/dev-continuity-init` and `/dev-sync` for cross-project reuse
- **Set up iCloud cloud-sync**: hooks auto-pull on session start, auto-push on commit and stop

### Issues encountered
- Streamlit's interaction between `key=` and `value=`/`index=` is subtle and poorly documented
- When a keyed widget receives `value=` that differs from session_state, behavior varies by widget type
- `_last_persisted` dict needs to be module-level to survive across reruns (Streamlit re-imports don't reset module globals)

### Decisions
- Bug fix prioritized over original sprint plan (P1-01 CSS extraction)
- Auto-save merged with bug fix since both touch the same widget code

---

## 2026-03-23 — Session: Initial Analysis & Dev Infrastructure

### What was done
- Full codebase analysis of all 4 modules (app.py, audio_recorder.py, transcriber.py, config_manager.py)
- Read CLAUDE_PROMPT.md (original project spec, 811 lines)
- Identified 13 improvement areas across functionality, architecture, and UX
- Created development continuity system:
  - `CLAUDE.md` — project-level instructions for Claude Code (auto-loaded every session)
  - `docs/dev/ARCHITECTURE.md` — module map, threading model, data flow, known issues
  - `docs/dev/BACKLOG.md` — prioritized task backlog with 13 items across 3 priority levels
  - `docs/dev/DEVLOG.md` — this file
  - `docs/dev/CURRENT_SPRINT.md` — current sprint tracking
  - Updated `memory/MEMORY.md` — Claude Code auto-memory

### Key findings
1. app.py is a 2550-line monolith: ~930 lines CSS, ~200 lines HTML templates, rest is UI logic
2. Polling via `time.sleep(1) + st.rerun()` causes full-page flicker
3. No automated tests
4. Architecture is solid for its complexity (proper thread separation via ProcessingController)
5. UI design is polished (custom CSS with light/dark mode, glassmorphism effects)

### Issues encountered
- app.py too large to read in one chunk (had to read in 300-line segments)
- No existing CLAUDE.md or development documentation

### Decisions
- Prioritize maintainability (P1) before new features (P2)
- Start with CSS extraction (P1-01) as the lowest-risk first step
- Build dev documentation system before any code changes

---

## Pre-2026-03-23 — Prior Development (reconstructed from git log)

### e1152e8 — Improve long-session UI stability
- Added `limit_visible_items()` to cap rendered feed items and transcript cards
- Prevents DOM bloat during multi-hour sessions

### dc3cbb9 — Add multilingual target flow and repo defaults
- Generalized translation from "Japanese→Chinese" to "any source→any target"
- Added `defaults/` directory for repo-bundled configs
- Added `target_language` concept and reading flow language selector

### 247cbfc — Update README with recent UI notes

### 5fd9cf4 — Refine translator UI and status diagnostics
- Sidebar diagnostic improvements
- UI refinements

### e328295 — Add port auto-cleanup feature
- Automatic port conflict resolution on startup
