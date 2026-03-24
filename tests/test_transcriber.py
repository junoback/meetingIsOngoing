#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcriber / TranscriberWorker 單元測試

Transcriber: 測試模式設定、統計、API 結果解析（API 呼叫用 mock）
TranscriberWorker: 測試 circuit breaker 邏輯
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcriber import Transcriber, TranscriberWorker


# ============================================================================
# Transcriber — 初始化與設定
# ============================================================================

class TestTranscriberSetup:
    def test_default_mode(self):
        t = Transcriber("fake-key")
        assert t.mode == "transcribe"

    def test_default_language(self):
        t = Transcriber("fake-key")
        assert t.language == "ja"
        assert t.target_language == "zh"

    def test_set_mode_valid(self):
        t = Transcriber("fake-key")
        t.set_mode("translate_en")
        assert t.mode == "translate_en"

    def test_set_mode_legacy_translate(self):
        t = Transcriber("fake-key")
        t.set_mode("translate")
        assert t.mode == "translate_en"

    def test_set_mode_legacy_translate_zh(self):
        t = Transcriber("fake-key")
        t.set_mode("translate_zh")
        assert t.mode == "translate_target"

    def test_set_mode_invalid_raises(self):
        t = Transcriber("fake-key")
        with pytest.raises(ValueError):
            t.set_mode("invalid_mode")

    def test_set_language(self):
        t = Transcriber("fake-key")
        t.set_language("en")
        assert t.language == "en"

    def test_set_target_language(self):
        t = Transcriber("fake-key")
        t.set_target_language("ko")
        assert t.target_language == "ko"

    def test_set_meeting_context(self):
        t = Transcriber("fake-key")
        t.set_meeting_context(
            meeting_topic="eFlash Qualification",
            terminology={"wafer": "晶圓", "die": "晶粒"}
        )
        assert t.meeting_topic == "eFlash Qualification"
        assert len(t.terminology) == 2


# ============================================================================
# Transcriber — 統計
# ============================================================================

class TestTranscriberStats:
    def test_initial_stats(self):
        t = Transcriber("fake-key")
        stats = t.get_stats()
        assert stats["total_calls"] == 0
        assert stats["translation_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["estimated_cost"] == 0

    def test_api_cost_estimate(self):
        t = Transcriber("fake-key")
        t.total_audio_duration = 60  # 1 分鐘
        cost = t.get_api_cost_estimate()
        assert cost == pytest.approx(0.006, abs=1e-6)

    def test_api_cost_proportional(self):
        t = Transcriber("fake-key")
        t.total_audio_duration = 120  # 2 分鐘
        cost = t.get_api_cost_estimate()
        assert cost == pytest.approx(0.012, abs=1e-6)


# ============================================================================
# Transcriber — _extract_text
# ============================================================================

class TestExtractText:
    def test_extract_from_string(self):
        t = Transcriber("fake-key")
        assert t._extract_text("  hello  ") == "hello"

    def test_extract_from_object_with_text(self):
        t = Transcriber("fake-key")
        obj = MagicMock()
        obj.text = "  from object  "
        assert t._extract_text(obj) == "from object"

    def test_extract_from_dict(self):
        t = Transcriber("fake-key")
        assert t._extract_text({"text": "  from dict  "}) == "from dict"

    def test_extract_fallback(self):
        t = Transcriber("fake-key")
        assert t._extract_text(12345) == "12345"


# ============================================================================
# Transcriber — transcribe_audio (mocked API)
# ============================================================================

class TestTranscribeAudio:
    def _make_audio_file(self):
        return BytesIO(b"\x00" * 100)

    @patch.object(Transcriber, '_transcribe_source_text', return_value="テスト音声")
    def test_transcribe_mode(self, mock_transcribe):
        t = Transcriber("fake-key")
        t.set_mode("transcribe")
        t.set_language("ja")

        result = t.transcribe_audio(self._make_audio_file(), 5.0)

        assert result is not None
        assert result["success"] is True
        assert result["text"] == "テスト音声"
        assert result["mode"] == "transcribe"
        assert result["language"] == "ja"
        assert result["duration"] == 5.0
        assert "latency" in result
        assert t.total_api_calls == 1

    @patch.object(Transcriber, '_translate_audio_to_english', return_value="Test audio")
    @patch.object(Transcriber, '_transcribe_source_text', return_value="テスト音声")
    def test_translate_en_mode(self, mock_transcribe, mock_translate):
        t = Transcriber("fake-key")
        t.set_mode("translate_en")
        t.set_language("ja")

        result = t.transcribe_audio(self._make_audio_file(), 5.0)

        assert result["success"] is True
        assert result["text"] == "Test audio"
        assert result["texts"]["ja"] == "テスト音声"
        assert result["texts"]["en"] == "Test audio"
        assert t.total_api_calls == 2  # 1 transcribe + 1 translate

    @patch.object(Transcriber, 'translate_to_target_language', return_value="測試音訊")
    @patch.object(Transcriber, '_translate_audio_to_english', return_value="Test audio")
    @patch.object(Transcriber, '_transcribe_source_text', return_value="テスト音声")
    def test_translate_target_mode(self, mock_transcribe, mock_translate_en, mock_translate_target):
        t = Transcriber("fake-key")
        t.set_mode("translate_target")
        t.set_language("ja")
        t.set_target_language("zh")

        result = t.transcribe_audio(self._make_audio_file(), 5.0)

        assert result["success"] is True
        assert result["text"] == "測試音訊"
        assert result["texts"]["ja"] == "テスト音声"
        assert result["texts"]["en"] == "Test audio"
        assert result["texts"]["zh"] == "測試音訊"

    @patch.object(Transcriber, '_transcribe_source_text', return_value="")
    def test_empty_text_returns_none(self, mock_transcribe):
        """空白結果應回傳 None"""
        t = Transcriber("fake-key")
        result = t.transcribe_audio(self._make_audio_file(), 5.0)
        assert result is None

    @patch.object(Transcriber, '_transcribe_source_text', side_effect=Exception("API down"))
    def test_api_failure_retries(self, mock_transcribe):
        t = Transcriber("fake-key")
        t.max_retries = 2
        t.retry_delay = 0  # 加速測試

        result = t.transcribe_audio(self._make_audio_file(), 5.0)

        assert result["success"] is False
        assert "API down" in result["error"]
        assert mock_transcribe.call_count == 2
        assert t.failed_calls == 1

    @patch.object(Transcriber, '_transcribe_source_text', return_value="English source")
    def test_translate_en_from_english_source(self, mock_transcribe):
        """英文來源 + translate_en 不應額外呼叫翻譯"""
        t = Transcriber("fake-key")
        t.set_mode("translate_en")
        t.set_language("en")

        result = t.transcribe_audio(self._make_audio_file(), 5.0)

        assert result["texts"]["en"] == "English source"
        assert t.total_api_calls == 1  # 不需要第二次 Whisper 呼叫


# ============================================================================
# TranscriberWorker — Circuit Breaker
# ============================================================================

class TestCircuitBreaker:
    def _make_worker(self):
        transcriber = MagicMock()
        worker = TranscriberWorker(transcriber)
        return worker

    def test_initial_state_closed(self):
        w = self._make_worker()
        status = w.get_circuit_breaker_status()
        assert status["is_open"] is False
        assert status["consecutive_failures"] == 0

    def test_success_resets_failures(self):
        w = self._make_worker()
        w._consecutive_failures = 2
        w._record_success()
        assert w._consecutive_failures == 0

    def test_failure_increments_counter(self):
        w = self._make_worker()
        w._record_failure()
        assert w._consecutive_failures == 1

    def test_circuit_opens_at_threshold(self):
        w = self._make_worker()
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        assert w._circuit_open is True
        status = w.get_circuit_breaker_status()
        assert status["is_open"] is True

    def test_circuit_stays_closed_below_threshold(self):
        w = self._make_worker()
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD - 1):
            w._record_failure()
        assert w._circuit_open is False

    def test_circuit_reopens_after_cooldown(self):
        w = self._make_worker()
        # 觸發熔斷
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()
        assert w._is_circuit_open() is True

        # 模擬冷卻結束
        w._circuit_reopen_at = time.time() - 1
        assert w._is_circuit_open() is False

    def test_backoff_increases_exponentially(self):
        w = self._make_worker()
        initial = w._current_backoff

        # 第一次觸發
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        # 冷卻後重置，再次觸發
        w._circuit_reopen_at = time.time() - 1
        w._is_circuit_open()  # 觸發 half-open
        w._consecutive_failures = 0

        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        assert w._current_backoff == initial * (TranscriberWorker.CB_BACKOFF_MULTIPLIER ** 2)

    def test_backoff_capped_at_max(self):
        w = self._make_worker()
        w._current_backoff = TranscriberWorker.CB_MAX_BACKOFF

        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        assert w._current_backoff <= TranscriberWorker.CB_MAX_BACKOFF

    def test_success_after_half_open_resets_failures(self):
        w = self._make_worker()
        # 觸發熔斷
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()
        assert w._circuit_open is True

        # 模擬冷卻結束 → half-open（_is_circuit_open 會把 _circuit_open 設為 False）
        w._circuit_reopen_at = time.time() - 1
        assert w._is_circuit_open() is False
        assert w._circuit_open is False  # half-open 後已關閉

        # API 呼叫成功
        w._record_success()
        assert w._consecutive_failures == 0
        assert w._circuit_open is False

    def test_success_after_half_open_resets_backoff(self):
        """Bug fix: half-open → 成功後 backoff 應重置回初始值"""
        w = self._make_worker()
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        # backoff 此時已加倍
        assert w._current_backoff > TranscriberWorker.CB_INITIAL_BACKOFF

        # half-open → 成功
        w._circuit_reopen_at = time.time() - 1
        w._is_circuit_open()
        w._record_success()

        assert w._current_backoff == TranscriberWorker.CB_INITIAL_BACKOFF

    def test_circuit_breaker_status_remaining_seconds(self):
        w = self._make_worker()
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        status = w.get_circuit_breaker_status()
        assert status["remaining_seconds"] > 0

    def test_output_queue_receives_circuit_breaker_event(self):
        w = self._make_worker()
        for _ in range(TranscriberWorker.CB_FAILURE_THRESHOLD):
            w._record_failure()

        event = w.output_queue.get_nowait()
        assert event["circuit_breaker"] is True
        assert event["success"] is False
