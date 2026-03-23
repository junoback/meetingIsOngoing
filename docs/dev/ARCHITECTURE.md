# Architecture Overview

> Last updated: 2026-03-23

## Module Map

```
┌─────────────────────────────────────────────────────────┐
│                     app.py (Streamlit)                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Sidebar   │  │ Main Panel   │  │ CSS Theme (~930L) │  │
│  │ - Config  │  │ - Feed Panel │  │ - Light/Dark mode │  │
│  │ - Controls│  │ - Status     │  │ - Custom props    │  │
│  │ - Stats   │  │ - Transcript │  │                   │  │
│  │ - Terms   │  │ - Export     │  │                   │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
│                                                          │
│  ProcessingController (background thread)                │
│  ┌─────────────────────────────────────────────────┐     │
│  │ recorder.get_next_chunk()                        │     │
│  │   → worker.add_audio_chunk()                     │     │
│  │   → worker.get_result() → self.transcripts[]     │     │
│  └─────────────────────────────────────────────────┘     │
└──────────┬──────────────────┬────────────────────────────┘
           │                  │
    ┌──────▼──────┐   ┌──────▼──────────┐
    │audio_recorder│   │  transcriber.py  │
    │     .py      │   │                  │
    │              │   │ Transcriber      │
    │ AudioRecorder│   │  - Whisper API   │
    │  - sounddev  │   │  - GPT translate │
    │  - WAV write │   │                  │
    │  - silence   │   │ TranscriberWorker│
    │    detect    │   │  - bg thread     │
    │  - chunking  │   │  - input/output  │
    │              │   │    queues        │
    └──────────────┘   └────────┬─────────┘
                                │
                       ┌────────▼─────────┐
                       │ config_manager.py │
                       │                   │
                       │ - API key         │
                       │ - meeting config  │
                       │ - terminology     │
                       │ - defaults/       │
                       └───────────────────┘
```

## Threading Model

```
Main Thread (Streamlit)
  │
  ├── reads controller.transcripts[] (list append is thread-safe in CPython)
  ├── reads recorder.get_recording_stats()
  ├── reads transcriber.get_stats()
  ├── time.sleep(1) + st.rerun() loop
  │
  └── Background Threads:
        │
        ├── AudioRecorder._recording_loop (Thread #1)
        │     - reads audio_buffer[]
        │     - writes to audio_queue
        │     - writes WAV file
        │
        ├── TranscriberWorker._worker_loop (Thread #2)
        │     - reads input_queue
        │     - calls Whisper API / GPT API
        │     - writes output_queue
        │
        └── ProcessingController._processing_loop (Thread #3)
              - bridges recorder → worker
              - reads recorder.audio_queue via get_next_chunk()
              - writes worker.input_queue via add_audio_chunk()
              - reads worker.output_queue via get_result()
              - appends to self.transcripts[]
              - writes live transcript file
```

## Data Flow

```
Mic/BlackHole → sounddevice callback → audio_buffer[]
  → _recording_loop chunks into segments
  → silence check (RMS vs threshold)
  → if not silent: audio_queue.put(WAV BytesIO)
  → ProcessingController: get_next_chunk() → add_audio_chunk()
  → TranscriberWorker: Whisper API call
    → mode=transcribe: source text only
    → mode=translate_en: source + Whisper translate to English
    → mode=translate_target: source + English + GPT translate to target
  → result dict with texts={lang_code: text} → output_queue
  → ProcessingController: get_result() → transcripts.append()
  → Main thread renders on next st.rerun()
```

## Known Architecture Issues

1. **app.py monolith**: ~2550 lines mixing CSS, HTML templates, UI logic, business logic
2. **Polling refresh**: time.sleep(1) + st.rerun() causes full page re-render every second
3. **iframe rebuild**: Reading Flow panel HTML rebuilt from scratch every rerun
4. **No error circuit breaker**: continuous API failures keep retrying without backoff escalation
5. **Memory**: WAV download loads entire file into memory via f.read()

## Planned Architecture Changes

See BACKLOG.md for prioritized tasks. Key structural changes planned:
- Extract CSS to separate file/function
- Extract HTML template builders to separate module
- Consider st.fragment (Streamlit 1.33+) for partial re-renders
