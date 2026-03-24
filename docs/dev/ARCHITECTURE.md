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

## Resolved Architecture Issues

1. ~~**app.py monolith**~~: CSS → styles.py (~940L), HTML builders → templates.py (~536L), app.py now ~1400L
2. ~~**Polling refresh**~~: st.fragment(run_every=2s) for partial re-renders, no full-page sleep+rerun
3. ~~**No error circuit breaker**~~: TranscriberWorker has exponential backoff circuit breaker
4. ~~**Memory: WAV download**~~: Fixed file handle leaks; with-statement for downloads
5. ~~**Print spam**~~: All modules use Python logging; high-frequency messages at DEBUG level

## Current Architecture Notes

- **Logging**: All modules use `logging.getLogger("meeting-translator")`. Default level INFO.
  Set `DEBUG` for verbose audio/API diagnostics.
- **Thread safety**: ProcessingController has exponential backoff on consecutive errors (max 30s).
- **Cross-midnight**: SRT/VTT export uses reference_date for monotonic timecodes.
