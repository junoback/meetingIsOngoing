# Meeting Translator - Claude Code Development Guide

## Project Summary
Real-time meeting translation app (Python + Streamlit) for macOS.
Captures audio via BlackHole 2ch, uses OpenAI Whisper API + GPT-4o-mini for transcription/translation.
Primary use case: Japanese meetings → Chinese translation for semiconductor/eFlash IP company.

## Development Continuity
**IMPORTANT**: This project is developed across multiple sessions on different machines.
Before making ANY changes, always read the development log and backlog:
- `docs/dev/DEVLOG.md` — chronological development log (what was done, issues encountered)
- `docs/dev/BACKLOG.md` — prioritized task backlog with status tracking
- `docs/dev/ARCHITECTURE.md` — architecture decisions and module map
- `docs/dev/CURRENT_SPRINT.md` — current sprint focus and progress

After completing work, ALWAYS update these files before the session ends.

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
- No automated tests yet. Manual testing via `streamlit run app.py`.
- Requires BlackHole 2ch or a microphone for audio input.

## Common Commands
```bash
# Run the app
.venv/bin/streamlit run app.py

# Install dependencies
.venv/bin/pip install -r requirements.txt
```
