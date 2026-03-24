#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AudioRecorder 單元測試

測試 VAD 邏輯、靜音偵測、chunk 處理、設定驗證。
不測試實際音訊串流（需要硬體裝置）。
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio_recorder import AudioRecorder


# ============================================================================
# 初始化與設定
# ============================================================================

class TestRecorderSetup:
    def test_default_sample_rate(self):
        r = AudioRecorder()
        assert r.sample_rate == 16000

    def test_default_channels(self):
        r = AudioRecorder()
        assert r.channels == 1

    def test_default_vad_enabled(self):
        r = AudioRecorder()
        assert r.vad_enabled is True

    def test_set_chunk_duration_normal(self):
        r = AudioRecorder()
        r.set_chunk_duration(10)
        assert r.chunk_duration == 10

    def test_set_chunk_duration_clamped_low(self):
        r = AudioRecorder()
        r.set_chunk_duration(0)
        assert r.chunk_duration == 1

    def test_set_chunk_duration_clamped_high(self):
        r = AudioRecorder()
        r.set_chunk_duration(60)
        assert r.chunk_duration == 30

    def test_set_silence_threshold_normal(self):
        r = AudioRecorder()
        r.set_silence_threshold(0.05)
        assert r.silence_threshold == pytest.approx(0.05)

    def test_set_silence_threshold_clamped(self):
        r = AudioRecorder()
        r.set_silence_threshold(-0.1)
        assert r.silence_threshold == 0.0
        r.set_silence_threshold(1.5)
        assert r.silence_threshold == 1.0


# ============================================================================
# 靜音偵測
# ============================================================================

class TestSilenceDetection:
    def test_silent_audio(self):
        r = AudioRecorder()
        r.silence_threshold = 0.01
        silence = np.zeros(1600, dtype=np.float32)
        assert r._is_silent(silence) == True

    def test_loud_audio(self):
        r = AudioRecorder()
        r.silence_threshold = 0.01
        loud = np.ones(1600, dtype=np.float32) * 0.5
        assert r._is_silent(loud) == False

    def test_threshold_boundary(self):
        """RMS 剛好等於閾值時不算靜音"""
        r = AudioRecorder()
        threshold = 0.1
        r.silence_threshold = threshold
        audio = np.ones(100, dtype=np.float32) * threshold
        assert r._is_silent(audio) == False

    def test_near_silence(self):
        """略高於閾值的訊號不算靜音"""
        r = AudioRecorder()
        r.silence_threshold = 0.01
        audio = np.ones(1600, dtype=np.float32) * 0.015
        assert r._is_silent(audio) == False


# ============================================================================
# _buffer_sample_count / _extract_samples
# ============================================================================

class TestBufferOperations:
    def test_empty_buffer_count(self):
        r = AudioRecorder()
        assert r._buffer_sample_count() == 0

    def test_buffer_count_single_chunk(self):
        r = AudioRecorder()
        r.audio_buffer = [np.zeros((100, 1))]
        assert r._buffer_sample_count() == 100

    def test_buffer_count_multiple_chunks(self):
        r = AudioRecorder()
        r.audio_buffer = [np.zeros((100, 1)), np.zeros((200, 1))]
        assert r._buffer_sample_count() == 300

    def test_extract_exact_samples(self):
        r = AudioRecorder()
        data = np.arange(100, dtype=np.float32).reshape(-1, 1)
        r.audio_buffer = [data]

        extracted = r._extract_samples(100)
        assert len(extracted) == 100
        assert r._buffer_sample_count() == 0

    def test_extract_partial_samples(self):
        r = AudioRecorder()
        data = np.arange(100, dtype=np.float32).reshape(-1, 1)
        r.audio_buffer = [data]

        extracted = r._extract_samples(50)
        assert len(extracted) == 50
        assert r._buffer_sample_count() == 50

    def test_extract_across_chunks(self):
        r = AudioRecorder()
        chunk1 = np.ones((30, 1), dtype=np.float32)
        chunk2 = np.ones((30, 1), dtype=np.float32) * 2
        r.audio_buffer = [chunk1, chunk2]

        extracted = r._extract_samples(50)
        assert len(extracted) == 50
        # 前 30 = 1.0, 後 20 = 2.0
        assert extracted[0, 0] == pytest.approx(1.0)
        assert extracted[35, 0] == pytest.approx(2.0)
        assert r._buffer_sample_count() == 10


# ============================================================================
# _find_silence_boundary (VAD 核心)
# ============================================================================

class TestFindSilenceBoundary:
    def _make_recorder(self, sample_rate=16000, min_chunk=1.0, silence_dur=0.3, window=0.1, threshold=0.01):
        r = AudioRecorder(sample_rate=sample_rate)
        r.vad_min_chunk = min_chunk
        r.vad_silence_duration = silence_dur
        r.vad_window_size = window
        r.silence_threshold = threshold
        return r

    def test_all_loud_no_boundary(self):
        """全程有聲音，找不到邊界"""
        r = self._make_recorder(sample_rate=1000, min_chunk=1.0)
        # 3 秒的聲音
        audio = np.ones(3000, dtype=np.float32) * 0.5
        boundary = r._find_silence_boundary(audio)
        assert boundary == -1

    def test_silence_at_end(self):
        """尾端有靜音，應找到邊界"""
        r = self._make_recorder(sample_rate=1000, min_chunk=1.0, silence_dur=0.3, window=0.1)
        # 2 秒聲音 + 0.5 秒靜音
        loud = np.ones(2000, dtype=np.float32) * 0.5
        silent = np.zeros(500, dtype=np.float32)
        audio = np.concatenate([loud, silent])

        boundary = r._find_silence_boundary(audio)
        assert boundary > 0
        assert boundary >= 1000  # 至少在 min_chunk 之後

    def test_too_short_for_min_chunk(self):
        """音訊短於 min_chunk，不搜尋"""
        r = self._make_recorder(sample_rate=1000, min_chunk=2.0)
        audio = np.zeros(1500, dtype=np.float32)  # 1.5 秒
        boundary = r._find_silence_boundary(audio)
        assert boundary == -1

    def test_silence_before_min_chunk_ignored(self):
        """min_chunk 之前的靜音不計"""
        r = self._make_recorder(sample_rate=1000, min_chunk=2.0, silence_dur=0.3, window=0.1)
        # 0.5 秒靜音 + 2.5 秒聲音
        silent_early = np.zeros(500, dtype=np.float32)
        loud = np.ones(2500, dtype=np.float32) * 0.5
        audio = np.concatenate([silent_early, loud])

        boundary = r._find_silence_boundary(audio)
        assert boundary == -1  # 靜音在 min_chunk 之前，不切

    def test_finds_latest_silence(self):
        """多段靜音時，應找到最晚的（tail-to-head 掃描）"""
        r = self._make_recorder(sample_rate=1000, min_chunk=1.0, silence_dur=0.3, window=0.1)
        # 1.5 秒聲音 + 0.4 秒靜音 + 0.5 秒聲音 + 0.4 秒靜音
        part1 = np.ones(1500, dtype=np.float32) * 0.5
        gap1 = np.zeros(400, dtype=np.float32)
        part2 = np.ones(500, dtype=np.float32) * 0.5
        gap2 = np.zeros(400, dtype=np.float32)
        audio = np.concatenate([part1, gap1, part2, gap2])

        boundary = r._find_silence_boundary(audio)
        # 應找到第二段靜音（較晚的）
        assert boundary > 2400  # 在第二段靜音區域


# ============================================================================
# _numpy_to_wav_bytes
# ============================================================================

class TestNumpyToWav:
    def test_produces_valid_wav(self):
        r = AudioRecorder()
        audio = np.zeros(1600, dtype=np.float32)
        wav_bytes = r._numpy_to_wav_bytes(audio)

        assert wav_bytes is not None
        # WAV 檔案以 RIFF 開頭
        wav_bytes.seek(0)
        header = wav_bytes.read(4)
        assert header == b"RIFF"

    def test_wav_size_proportional(self):
        r = AudioRecorder()
        short = r._numpy_to_wav_bytes(np.zeros(1600, dtype=np.float32))
        long = r._numpy_to_wav_bytes(np.zeros(16000, dtype=np.float32))

        short_size = short.getbuffer().nbytes
        long_size = long.getbuffer().nbytes
        # 10x audio 應產生接近 10x 的 wav（加上 header overhead）
        assert long_size > short_size * 5


# ============================================================================
# get_recording_stats
# ============================================================================

class TestRecordingStats:
    def test_initial_stats(self):
        r = AudioRecorder()
        stats = r.get_recording_stats()
        assert stats["duration"] == 0
        assert stats["chunks_processed"] == 0
        assert stats["chunks_captured"] == 0
        assert stats["chunks_skipped_silence"] == 0
        assert stats["is_recording"] is False
        assert stats["is_paused"] is False

    def test_stats_file_path_none_initially(self):
        r = AudioRecorder()
        stats = r.get_recording_stats()
        assert stats["file_path"] is None
