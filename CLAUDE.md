# Meeting Translator - Claude Code Development Guide

## Project Summary
Real-time meeting translation app (Python + Streamlit) for macOS.
Captures audio via BlackHole 2ch, uses OpenAI Whisper API + GPT-4o-mini for transcription/translation.
Primary use case: Japanese meetings → Chinese translation for semiconductor/eFlash IP company.

## Development Continuity
**IMPORTANT**: This project is developed across multiple sessions on different machines.

### Session Start Protocol
Before making ANY code changes, read these files in order:
1. `docs/dev/CURRENT_SPRINT.md` — what to work on NOW + handoff notes from last session
2. `docs/dev/BACKLOG.md` — full prioritized task list
3. `docs/dev/DEVLOG.md` — past session records (scan recent entries)
4. `docs/dev/ARCHITECTURE.md` — if needed for context on module structure

### Incremental Save Protocol (critical)
Do NOT wait until session end to update docs. Instead:
- **After completing each BACKLOG task**: immediately update CURRENT_SPRINT.md status + BACKLOG.md status, then commit the doc changes together with the code changes.
- **After every git commit**: check if docs/dev/ needs a status update (a PostToolUse hook will remind you).
- **Before starting a new task**: ensure previous task's doc updates are committed.

This way, even if the session is abruptly terminated, the latest completed task is always recorded.

### What goes where
- `CURRENT_SPRINT.md` — task status checkboxes + "Session Handoff Notes" section at bottom
- `DEVLOG.md` — append one entry per session summarizing what was done, issues, decisions
- `BACKLOG.md` — move completed items, add newly discovered tasks
- `ARCHITECTURE.md` — update only when module structure changes

## Code Conventions
- All user-facing UI text: English labels, Chinese descriptions where needed
- Code comments: Chinese (Traditional)
- Commit messages: English
- Module pattern: one class per file, file name = snake_case of class concept
- CSS: CSS custom properties with light/dark mode via prefers-color-scheme
- Threading: never access st.session_state from child threads; use ProcessingController pattern

## File Structure
```
app.py              — Streamlit main (UI + control logic)
audio_recorder.py   — Audio capture, WAV recording, silence detection
transcriber.py      — Whisper API, GPT translation, background worker
config_manager.py   — Config/terminology/meeting persistence
defaults/           — Repo-bundled default configs
docs/dev/           — Development documentation (log, backlog, architecture)
```

## Key Technical Notes
- Streamlit refresh: `time.sleep(1); st.rerun()` loop during recording
- Audio pipeline: sounddevice → AudioRecorder.audio_queue → ProcessingController → TranscriberWorker → output_queue
- Config priority: ~/.meeting-translator/ (local) > defaults/ (repo bundled)
- app.py is ~2550 lines and needs refactoring (CSS, HTML templates, business logic mixed)

## Testing
- **Automated**: 126 pytest tests covering config_manager, templates, transcriber, audio_recorder
- **Manual**: `streamlit run app.py` with BlackHole 2ch or microphone for audio input
- Run tests: `.venv/bin/python -m pytest tests/ -v`

## Cloud Memory Sync
Dev docs are synced to iCloud Drive for cross-machine continuity.
Hooks handle this automatically, but on a NEW machine you need to bootstrap:

```bash
# 1. Clone the repo and set up .claude/hooks/ (copy from another machine or iCloud)
# 2. The hooks live in .claude/ (gitignored), sync script at:
#    .claude/hooks/cloud-sync.sh
# 3. Manual commands:
.claude/hooks/cloud-sync.sh pull    # Cloud → Local (session start)
.claude/hooks/cloud-sync.sh push    # Local → Cloud (after changes)
.claude/hooks/cloud-sync.sh status  # Compare local vs cloud
.claude/hooks/cloud-sync.sh init    # First-time setup on new machine
```

Cloud path: `~/Library/Mobile Documents/com~apple~CloudDocs/claude-memory/meetingIsOngoing/`
To change provider, set env var: `export CLAUDE_CLOUD_MEMORY=~/Library/CloudStorage/GoogleDrive-.../claude-memory`

## Common Commands
```bash
# Run the app
.venv/bin/streamlit run app.py

# Install dependencies
.venv/bin/pip install -r requirements.txt
```
