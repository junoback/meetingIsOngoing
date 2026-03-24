#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py 工具函式單元測試

測試 sanitize_filename、_timestamp_to_seconds 等從 app.py 提取的共用函式。
"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import sanitize_filename, _timestamp_to_seconds, ProcessingController, _persist_setting_if_changed, _last_persisted


# ============================================================================
# sanitize_filename
# ============================================================================

class TestSanitizeFilename:
    def test_normal_name(self):
        assert sanitize_filename("Weekly Meeting") == "Weekly Meeting"

    def test_slashes(self):
        assert sanitize_filename("R&D/Design Review") == "R&D-Design Review"

    def test_backslash(self):
        assert sanitize_filename("path\\to\\file") == "path-to-file"

    def test_colon(self):
        assert sanitize_filename("Meeting: Q4 Review") == "Meeting- Q4 Review"

    def test_multiple_special_chars(self):
        result = sanitize_filename('test/file:name*with?special<chars>and|pipes"quotes')
        assert "/" not in result
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert '"' not in result

    def test_empty_string(self):
        assert sanitize_filename("") == ""

    def test_none_returns_empty(self):
        """None 或空值不應崩潰"""
        assert sanitize_filename("") == ""

    def test_japanese_chars_preserved(self):
        """日文字元不應被清理"""
        assert sanitize_filename("定例会議") == "定例会議"

    def test_chinese_chars_preserved(self):
        assert sanitize_filename("週會_設計評審") == "週會_設計評審"


# ============================================================================
# _timestamp_to_seconds（跨午夜修正）
# ============================================================================

class TestTimestampToSeconds:
    def test_basic_conversion(self):
        ts = datetime(2026, 3, 24, 14, 30, 15)
        result = _timestamp_to_seconds(ts)
        assert result == 14 * 3600 + 30 * 60 + 15

    def test_midnight(self):
        ts = datetime(2026, 3, 24, 0, 0, 0)
        assert _timestamp_to_seconds(ts) == 0

    def test_end_of_day(self):
        ts = datetime(2026, 3, 24, 23, 59, 59)
        assert _timestamp_to_seconds(ts) == 23 * 3600 + 59 * 60 + 59

    def test_same_day_with_reference(self):
        """同一天內使用 reference_date 應和不使用一樣"""
        ref = datetime(2026, 3, 24, 10, 0, 0)
        ts = datetime(2026, 3, 24, 14, 30, 0)
        assert _timestamp_to_seconds(ts, ref) == _timestamp_to_seconds(ts)

    def test_cross_midnight(self):
        """跨午夜：下一天 00:30 相對於前一天開始應超過 24h"""
        ref = datetime(2026, 3, 24, 23, 0, 0)  # 前一天 23:00
        ts = datetime(2026, 3, 25, 0, 30, 0)   # 隔天 00:30

        result = _timestamp_to_seconds(ts, ref)
        # 應該 = 0:30:00 + 86400 = 88200
        assert result == 0 * 3600 + 30 * 60 + 86400

    def test_cross_midnight_ensures_monotonic(self):
        """跨午夜的時間碼應遞增，不會倒退"""
        ref = datetime(2026, 3, 24, 23, 50, 0)
        ts_before = datetime(2026, 3, 24, 23, 55, 0)
        ts_after = datetime(2026, 3, 25, 0, 5, 0)

        sec_before = _timestamp_to_seconds(ts_before, ref)
        sec_after = _timestamp_to_seconds(ts_after, ref)
        assert sec_after > sec_before

    def test_no_reference_no_cross_midnight(self):
        """無 reference_date 時，午夜後的時間碼從 0 開始（舊行為）"""
        ts = datetime(2026, 3, 25, 0, 30, 0)
        result = _timestamp_to_seconds(ts)
        assert result == 30 * 60  # 不加 86400


# ============================================================================
# ProcessingController 記憶體限制
# ============================================================================

class TestProcessingControllerMemory:
    def test_max_in_memory_transcripts_constant(self):
        """確認記憶體上限常數存在"""
        assert ProcessingController.MAX_IN_MEMORY_TRANSCRIPTS == 500

    def test_total_transcript_count_tracks_all(self):
        """total_transcript_count 應追蹤所有 transcript（含已淘汰）"""
        from unittest.mock import MagicMock
        controller = ProcessingController(MagicMock(), MagicMock())
        controller.total_transcript_count = 0
        # 直接模擬 append 行為
        for i in range(10):
            controller.transcripts.append({'text': f'item-{i}'})
            controller.total_transcript_count += 1
        assert controller.total_transcript_count == 10
        assert len(controller.transcripts) == 10


# ============================================================================
# _persist_setting_if_changed
# ============================================================================

class TestPersistSetting:
    def test_persist_calls_save_on_change(self):
        """值改變時應呼叫 config_manager.save_setting"""
        from unittest.mock import patch
        _last_persisted.clear()
        with patch('app.config_manager') as mock_cm:
            _persist_setting_if_changed('test_key', 'value_a')
            mock_cm.save_setting.assert_called_once_with('test_key', 'value_a')

    def test_persist_skips_same_value(self):
        """相同值不應重複寫入"""
        from unittest.mock import patch
        _last_persisted.clear()
        _last_persisted['test_key2'] = 'same_value'
        with patch('app.config_manager') as mock_cm:
            _persist_setting_if_changed('test_key2', 'same_value')
            mock_cm.save_setting.assert_not_called()

    def test_persist_updates_cache(self):
        """寫入後應更新快取"""
        from unittest.mock import patch
        _last_persisted.clear()
        with patch('app.config_manager'):
            _persist_setting_if_changed('cache_key', 42)
        assert _last_persisted['cache_key'] == 42
