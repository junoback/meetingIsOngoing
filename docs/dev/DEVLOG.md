# Development Log

> Chronological record of development sessions. Newest entries at the top.
> Each entry records: date, what was done, issues encountered, decisions made.

---

## 2026-05-14 — Session: Translation lag fix (skip English intermediate)

### What was done
- **Commit `11716b1`**: For mode `translate_target` with non-OpenAI STT and
  target language ≠ en, skip the English intermediate LLM call. Pipeline drops
  from 1 STT + 2 LLM calls per chunk to 1 STT + 1 LLM, matching the OpenAI
  Whisper path's call count.
- 2 new unit tests cover the optimized path and the target=en edge case.
  149/147 tests pass.

### Problem reported
User reported ~4 min lag between speech and translation appearing after
1-2 hour meetings using Groq Whisper + DeepSeek-V3 (the new bundled defaults
from `73a55a7`).

### Root cause
Single-threaded worker queue grew unbounded because per-chunk processing time
(~3-5s) exceeded chunk arrival rate (~10s × VAD smart). The extra LLM call
for English intermediate was the culprit:

```
ja audio
  → Groq STT (ja text)               ~0.5s
  → DeepSeek LLM (ja → en intermediate) ~1.5s    ← REMOVED
  → DeepSeek LLM (ja → zh, with en context) ~2s
```

The English intermediate served two purposes: (a) populating `texts['en']`
for bilingual UI display; (b) providing as reference in the target-translation
prompt. Neither is strictly necessary for non-English-target use cases with
modern LLMs.

### Decisions
- **Skip universally** when STT lacks `audio.translations` AND target ≠ en.
  Universal across all 7 source/target language combos, not specific to ja→zh.
- **Keep when target == en** (still needed; no audio.translations available).
- **Keep on OpenAI Whisper path** unchanged — there it's a free byproduct of
  the cheap STT call.
- **Trade-off accepted**: bilingual EN row won't show on non-OpenAI STT.
  Users wanting EN should switch back to OpenAI Whisper.

### Investigation notes (DeepSeek-side)
- Verified `deepseek-chat` model now auto-maps to **DeepSeek-V4-Flash
  non-thinking mode** (per pricing docs, "Legacy model names will be
  deprecated; for compatibility, they correspond to non-thinking and thinking
  modes of `deepseek-v4-flash`"). We are already on the newest cheap model.
- No off-peak hours discount currently advertised on DeepSeek pricing page
  (was a feature in the V3 era; appears removed in V4).
- `deepseek-v4-pro` available with 75% off until 2026/05/31 15:59 UTC, but
  3× more expensive than v4-flash at discount; no published latency benchmark
  showing pro is faster, and larger model likely means slower.
- Cache hit pricing ($0.0028/M, ~1/50 of cache miss) is a future cost-saving
  opportunity by structuring system prompt as cacheable prefix. Not done yet.

### Architecture/timing reference (added for future debugging)
**Pipeline** (after fix, Groq + non-EN target):
audio → AudioRecorder.audio_queue → ProcessingController →
TranscriberWorker.input_queue → [single worker: 1 STT + 1 LLM] →
output_queue → Streamlit fragment (run_every=2s) → UI.

**Healthy per-chunk latency** (queue empty):
- Short chunk (3s VAD-cut): ~6s end-to-end
- Long chunk (10s forced cut): ~14s end-to-end

**chunk_duration setting** (default 10s) controls:
1. Latency floor (results never appear faster than ~chunk_duration/2 in VAD
   mode, or full chunk_duration when speech is continuous).
2. Chunk arrival rate. Worker keep-up requires `processing_time < arrival_interval`.
   Smaller chunk_duration = more API calls per minute = faster queue accumulation
   if API is slow.

### Open follow-ups (not blocking)
- User to test OpenAI (Whisper + GPT-4o-mini) next time as a speed comparison
  baseline. If OpenAI is dramatically faster than Groq + DeepSeek even after
  the fix, the bottleneck is on DeepSeek's side (not code).
- Optional: add chunk-level timing logger that prints per-chunk
  STT-time / LLM-time / queue-wait-time. Useful for quantifying bottlenecks
  when comparing providers. Not built — wait until needed.
- Optional: restructure the translation system_prompt for DeepSeek cache-hit
  optimization (50× cheaper input). Pure cost play, not speed.

### Related files
- [transcriber.py:417-450](transcriber.py:417-450) — translate_target mode logic;
  the `else:` clause was changed to `elif target_language == "en":`.
- [tests/test_transcriber.py:184-237](tests/test_transcriber.py:184-237) —
  new tests `test_translate_target_skips_english_for_non_openai_stt` and
  `test_translate_target_to_english_with_non_openai_stt`.

---

## 2026-05-11 — Session: Stale marker + transcript server warning (proper fix)

### What was done
- **Commit `6e48ceb`**: Fix two bugs that both stem from Streamlit's `st.rerun(scope="app")` re-executing the script's module body with fresh globals.
- **Bug A — stale marker triggers auto-Viewer**: `_write_active_session_marker()` now stores `os.getpid()`; `_cleanup_stale_marker_on_startup()` runs once at process startup (guarded by `sys._mt_stale_marker_checked`) and deletes markers whose owner PID is dead OR which lack a PID (legacy format). Marker whose PID == `os.getpid()` is kept.
- **Bug B — spurious "port 8580 already in use" warning**: `_start_transcript_server()` switched from module-level `_transcript_server_started` flag to `sys._mt_transcript_server_started`. The sys attribute survives module re-execution, so the bind is attempted exactly once per process.
- Pre-existing 147 tests still pass; no new tests added (both fixes are integration-level behavior best verified by running the app, which we did manually with multiple stop/start cycles).

### Issues encountered & key finding
**Streamlit's two flavors of rerun** (poorly documented, the key insight from this session):
- A normal button-click rerun re-calls `main()` but reuses the module's globals dict, so module-level variables survive.
- `st.rerun(scope="app")` (which `start_recording()` calls at end) re-executes the entire module body with **fresh globals** — equivalent to a fresh `exec(code, new_globals)`. Any `_module_level_flag = False` line resets the flag.

Evidence captured during debug:
- Added one-line DEBUG log at module level checking `globals().get('_transcript_server_started')`.
- On scope="app" rerun, prev flag = `<unset>` (not the expected `True`), proving the globals dict is fresh.
- Same effect would apply to `_last_persisted: dict = {}` (settings-persist cache) — it gets reset on every scope="app" rerun, which is functionally correct but defeats the optimization. Not fixing for now; it's silently inefficient, not broken.

### Decisions
- **Use `sys` attributes for process-level state** that must survive module re-execution. Module-level flags don't work in this codebase because `start_recording()` triggers scope="app" rerun.
- Cleanup runs **once per process** via sys guard — never on subsequent reruns. Critical so it can't accidentally delete a marker we just wrote in `start_recording()`.
- A previous session (commit `cd75526`, rolled back during this session) had attempted the marker fix but contained a latent bug: when `owner_pid == os.getpid()` it would "delete as safety" — which would delete the marker the current session just wrote (after `st.rerun(scope="app")` re-ran cleanup). Corrected here: same-PID marker is kept.
- Two commits were rolled back mid-session (`cd75526` stale-marker + `bb79a4f` SO_REUSEADDR) under the wrong belief that the bugs were worktree artifacts. The hard reset was safe (neither was pushed). Re-implemented both fixes from scratch with the correct sys-attribute pattern. Details in `SESSION_HANDOFF_20260511.md` (correction at top).

### Related files
- [app.py:7-18](app.py:7-18) — added `import os`, `import sys`
- [app.py:292-302](app.py:292-302) — `_write_active_session_marker` now stores `pid`
- [app.py:346-403](app.py:346-403) — new `_pid_alive()` and `_cleanup_stale_marker_on_startup()`
- [app.py:410-426](app.py:410-426) — `_start_transcript_server` uses sys attribute
- [app.py:1132-1138](app.py:1132-1138) — `main()` calls cleanup before viewer detection

---

## 2026-03-24 — Session: Sprint 6 — Widget Reset Bug Fix & Polish

### What was done
- **BUG FIX (critical)**: Widget state reset on Start Recording — 3-layer defense:
  1. `_force_sync_widget_keys()` called before every `st.rerun(scope="app")` — force-writes authoritative values to widget keys
  2. `index=` parameter on all selectboxes/radio as fallback (computed from authoritative `st.session_state`)
  3. Auto-persist compares against config baseline to prevent transient resets from corrupting saved settings
  - Also fixed `StreamlitAPIException` for `reading_flow_language_widget` (inside fragment, already instantiated — wrapped in try/except, index= fallback protects it)
- **S6-01**: Fixed terminology zh-only guard — removed `target_language == "zh"` guard in `start_recording()`
- **S6-02**: Replaced 3 remaining `print()` calls with `logger`
- **S6-03**: Added settings auto-persist with `_persist_setting_if_changed()`
- **S6-04**: Transcript memory cap (MAX_IN_MEMORY_TRANSCRIPTS=500)
- **S6-05**: Fixed history download bug (`preview` safety)
- **Tests**: 147 total (+5 new)

### Issues encountered
- **Root cause of widget reset**: `st.rerun(scope="app")` from inside a `@st.fragment` causes Streamlit to lose/reset sidebar widget keys. Without `index=`, selectboxes default to item 0 (Japanese/Transcribe).
- Previous fix (commit 4b6bbec, unified widget keys) was insufficient — the keys themselves were being discarded by Streamlit during fragment-triggered full-page reruns.
- Auto-persist initially made it worse by saving the reset values to config, corrupting the user's settings. Fixed by comparing against config baseline instead of memory cache.
- `reading_flow_language_widget` is inside the fragment, so `_force_sync_widget_keys()` can't modify it after instantiation. Wrapped in try/except; `index=` fallback is sufficient.

### Decisions
- 3-layer defense is intentional overkill — Streamlit's widget state behavior across fragment/page boundaries is poorly documented and may change between versions.
- Auto-persist only fires on genuine user change (value differs from authoritative state), never on render-cycle echo.

---

## 2026-03-24 — Session: Sprint 3+ (Polish + All Remaining Features)

### What was done
- **P3-01**: Streaming WAV download — replaced `f.read()` with `open(file, 'rb')` for memory efficiency
- **P3-03**: Keyboard shortcuts — Ctrl/Cmd+Shift+R/P/S for start/pause/stop via JS injection
- **P2-04**: Session history & review — lists up to 20 past transcripts with expandable preview and download
- **P3-02**: Mode/language switching during recording — mode radio, target language, and bilingual toggle enabled during recording; audio language stays locked for Whisper consistency
- **P1-03**: Reduced flickering with `st.fragment` — main content area wrapped in fragment with `run_every=2s` during recording; removed `time.sleep(1); st.rerun()` loop; controls use `st.rerun(scope="app")`

### What was done (continued — infrastructure)
- **P4-01**: Added automated test suite (126 tests)
  - `test_config_manager.py` — config I/O, API key, meeting config, terminology (24 tests)
  - `test_templates.py` — constants, lookups, mode helpers, transcript data processing (33 tests)
  - `test_transcriber.py` — mode setup, stats, text extraction, mocked API, circuit breaker (29 tests)
  - `test_audio_recorder.py` — setup, silence detection, buffer ops, VAD boundary, WAV conversion (28 tests)
- **Bug fix**: Circuit breaker `_record_success()` didn't reset backoff after half-open → success path (backoff stayed doubled)

### Decisions
- Keyboard shortcuts use Ctrl+Shift (or Cmd+Shift on Mac) prefix to avoid conflicts with browser shortcuts
- Session history only shown when not recording to avoid UI clutter during active sessions
- P3-02: Audio language locked during recording (Whisper needs consistent source), but target language and mode can switch freely — Python GIL makes simple attribute assignment thread-safe
- P1-03: st.fragment wraps live feed + status + controls + metrics + transcripts as one fragment; sidebar stats only update on user interaction (acceptable trade-off)
- Tests use `unittest.mock` for API calls, `tmp_path` for config isolation; no hardware (microphone) needed

---

## 2026-03-24 — Session: Two Sprints Complete (P1 + P2)

### What was done (Sprint 2 — Feature Enhancements)
- **P2-03**: Terminology dictionary now works for all target languages (removed zh-only guard)
- **P2-02**: SRT/VTT subtitle export with format selector in UI
- **P2-01**: Energy-based VAD smart chunking in AudioRecorder
  - Scans from tail for silence gaps (≥0.3s low energy) to find natural split points
  - Min chunk 3s, max = user's chunk_duration setting, no new dependencies
  - Toggleable via "Smart chunking (VAD)" checkbox in sidebar

### Decisions (Sprint 2)
- VAD uses simple energy detection (RMS) instead of silero-vad to avoid heavy dependency
- Scan direction is tail-to-head so we split at the latest silence boundary (maximizes chunk quality)
- SRT/VTT timecodes derived from timestamp + duration fields already on each chunk

---

## 2026-03-24 — Session: Sprint Complete (P1-01, P1-02, P1-04) + Launch/Stop Commands

### What was done
- **P1-02**: Extracted HTML template builders → `templates.py` (536 lines)
  - Constants, lookup helpers, data helpers, 5 HTML builders moved from app.py
- **P1-01**: Extracted ~900 lines of inline CSS → `styles.py` with `get_main_css()`
- **P1-04**: Added circuit breaker to `TranscriberWorker`
  - 3 consecutive failures → trip, 10s initial backoff, 2x exponential up to 300s
  - Half-open auto-retry after cooldown, UI status display in sidebar
- **Launch/Stop commands**: Rewrote `run_meeting_translator.command` (PID file, auto browser open, duplicate launch protection), created `stop_meeting_translator.command`
- **app.py**: Reduced from ~2550 → ~1175 lines

### File structure after this session
```
app.py           (1175 lines) — session state, control flow, main UI
styles.py        (940 lines)  — all CSS via get_main_css()
templates.py     (536 lines)  — HTML builders, constants, lookup/data helpers
transcriber.py   (530 lines)  — Whisper API, GPT translation, circuit breaker
audio_recorder.py              — audio capture (unchanged)
config_manager.py              — config persistence (unchanged)
```

### Decisions
- Constants and lookup helpers moved to templates.py (not app.py) to avoid circular imports
- Circuit breaker lives in TranscriberWorker (not ProcessingController) since it's closest to the API call boundary
- Sprint fully complete; next sprint should start from P2 features

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
