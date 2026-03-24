#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
templates.py 單元測試

測試常數、查找輔助函式、資料處理輔助函式。
HTML builder 函式因需要 Streamlit runtime，不在此測試。
"""

import pytest
import sys
from pathlib import Path

# 把專案根目錄加到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from templates import (
    LANGUAGE_OPTIONS, LANGUAGE_FILE_LABELS, LANGUAGE_TONE_CLASSES,
    MODE_ORDER, LEGACY_MODE_ALIASES,
    TOP_PANEL_HEIGHT, MAX_VISIBLE_FEED_ITEMS, MAX_VISIBLE_TRANSCRIPT_CARDS,
    normalize_mode, get_language_label, get_file_language_label, get_language_tone,
    get_mode_options, get_mode_summary, get_default_mode,
    get_flow_language_options, get_default_flow_language,
    limit_visible_items,
    normalize_transcript_payload, get_transcript_language_order,
    get_text_for_language, get_feed_items,
)


# ============================================================================
# 常數完整性
# ============================================================================

class TestConstants:
    def test_language_options_has_minimum_languages(self):
        assert "ja" in LANGUAGE_OPTIONS
        assert "en" in LANGUAGE_OPTIONS
        assert "zh" in LANGUAGE_OPTIONS

    def test_language_file_labels_covers_options(self):
        """LANGUAGE_FILE_LABELS 至少要涵蓋 LANGUAGE_OPTIONS 的 key"""
        for code in LANGUAGE_OPTIONS:
            assert code in LANGUAGE_FILE_LABELS, f"{code} missing from LANGUAGE_FILE_LABELS"

    def test_mode_order_has_three_modes(self):
        assert len(MODE_ORDER) == 3
        assert "transcribe" in MODE_ORDER
        assert "translate_en" in MODE_ORDER
        assert "translate_target" in MODE_ORDER

    def test_legacy_aliases_map_to_valid_modes(self):
        for alias, target in LEGACY_MODE_ALIASES.items():
            assert target in MODE_ORDER

    def test_display_limits_are_positive(self):
        assert TOP_PANEL_HEIGHT > 0
        assert MAX_VISIBLE_FEED_ITEMS > 0
        assert MAX_VISIBLE_TRANSCRIPT_CARDS > 0


# ============================================================================
# normalize_mode
# ============================================================================

class TestNormalizeMode:
    def test_current_mode_unchanged(self):
        assert normalize_mode("transcribe") == "transcribe"
        assert normalize_mode("translate_en") == "translate_en"
        assert normalize_mode("translate_target") == "translate_target"

    def test_legacy_translate_alias(self):
        assert normalize_mode("translate") == "translate_en"

    def test_legacy_translate_zh_alias(self):
        assert normalize_mode("translate_zh") == "translate_target"

    def test_unknown_mode_passthrough(self):
        assert normalize_mode("custom_mode") == "custom_mode"


# ============================================================================
# get_language_label / get_file_language_label / get_language_tone
# ============================================================================

class TestLanguageLookups:
    def test_get_language_label_known(self):
        assert get_language_label("ja") == "Japanese"
        assert get_language_label("zh") == "Chinese"

    def test_get_language_label_unknown(self):
        """未知語言回傳大寫代碼"""
        assert get_language_label("xx") == "XX"

    def test_get_file_language_label_known(self):
        assert get_file_language_label("ja") == "日語"
        assert get_file_language_label("en") == "英文"

    def test_get_file_language_label_unknown(self):
        assert get_file_language_label("xx") == "XX"

    def test_get_language_tone_known(self):
        assert get_language_tone("ja") == "tone-ja"
        assert get_language_tone("en") == "tone-en"

    def test_get_language_tone_unknown(self):
        assert get_language_tone("xx") == "tone-neutral"


# ============================================================================
# get_mode_options / get_mode_summary / get_default_mode
# ============================================================================

class TestModeHelpers:
    def test_mode_options_returns_three_modes(self):
        options = get_mode_options("ja", "zh")
        assert len(options) == 3
        assert "transcribe" in options
        assert "translate_en" in options
        assert "translate_target" in options

    def test_mode_options_includes_language_names(self):
        options = get_mode_options("ja", "zh")
        assert "Japanese" in options["transcribe"]
        assert "English" in options["translate_en"]
        assert "Chinese" in options["translate_target"]

    def test_mode_summary_transcribe(self):
        summary = get_mode_summary("transcribe", "ja", "zh")
        assert "Japanese" in summary

    def test_mode_summary_translate_en(self):
        summary = get_mode_summary("translate_en", "ja", "zh")
        assert "English" in summary

    def test_default_mode_is_valid(self):
        mode = get_default_mode("ja", "zh")
        assert mode in MODE_ORDER


# ============================================================================
# get_flow_language_options / get_default_flow_language
# ============================================================================

class TestFlowLanguage:
    def test_transcribe_mode_returns_source_only(self):
        options = get_flow_language_options("transcribe", "ja", "zh")
        assert "ja" in options

    def test_translate_en_mode_includes_english(self):
        options = get_flow_language_options("translate_en", "ja", "zh")
        assert "en" in options

    def test_translate_target_includes_target(self):
        options = get_flow_language_options("translate_target", "ja", "zh")
        assert "zh" in options

    def test_default_flow_language_is_in_options(self):
        mode = "translate_target"
        source, target = "ja", "zh"
        options = get_flow_language_options(mode, source, target)
        default = get_default_flow_language(mode, source, target)
        assert default in options


# ============================================================================
# limit_visible_items
# ============================================================================

class TestLimitVisibleItems:
    def test_returns_all_when_under_limit(self):
        items = [1, 2, 3]
        visible, hidden = limit_visible_items(items, 10)
        assert visible == [1, 2, 3]
        assert hidden == 0

    def test_truncates_when_over_limit(self):
        items = list(range(20))
        visible, hidden = limit_visible_items(items, 5)
        assert len(visible) == 5
        assert hidden == 15

    def test_keeps_newest_items(self):
        """截斷時應保留最新（尾端）的項目"""
        items = [1, 2, 3, 4, 5]
        visible, hidden = limit_visible_items(items, 3)
        assert visible == [3, 4, 5]
        assert hidden == 2

    def test_empty_list(self):
        visible, hidden = limit_visible_items([], 10)
        assert visible == []
        assert hidden == 0

    def test_exact_limit(self):
        items = [1, 2, 3]
        visible, hidden = limit_visible_items(items, 3)
        assert visible == [1, 2, 3]
        assert hidden == 0


# ============================================================================
# normalize_transcript_payload
# ============================================================================

class TestNormalizeTranscriptPayload:
    def test_payload_with_texts_dict(self):
        """已有 texts 欄位的 payload 應保留所有語言"""
        payload = {
            "text": "hello",
            "texts": {"en": "hello", "ja": "こんにちは"},
            "mode": "translate_en",
            "language": "en"
        }
        source_lang, target_lang, texts, mode = normalize_transcript_payload(payload)
        assert texts["en"] == "hello"
        assert texts["ja"] == "こんにちは"
        assert mode == "translate_en"

    def test_payload_without_texts_builds_from_text(self):
        """沒有 texts 欄位時應從 text + language 建立"""
        payload = {
            "text": "hello",
            "mode": "transcribe",
            "language": "en"
        }
        source_lang, target_lang, texts, mode = normalize_transcript_payload(payload)
        assert texts["en"] == "hello"
        assert source_lang == "en"

    def test_legacy_mode_normalized(self):
        """舊模式名稱應被轉換"""
        payload = {
            "text": "test",
            "texts": {"en": "test"},
            "mode": "translate",
            "language": "en"
        }
        _, _, _, mode = normalize_transcript_payload(payload)
        assert mode == "translate_en"


# ============================================================================
# get_transcript_language_order / get_text_for_language
# ============================================================================

class TestTranscriptLanguageOrder:
    def test_returns_list_of_language_codes(self):
        item = {
            "texts": {"ja": "テスト", "en": "test", "zh": "測試"},
            "mode": "translate_target",
            "source_language": "ja",
            "target_language": "zh"
        }
        order = get_transcript_language_order(item)
        assert isinstance(order, list)
        assert len(order) > 0
        for code in order:
            assert code in item["texts"]


class TestGetTextForLanguage:
    def test_returns_matching_text(self):
        item = {"texts": {"ja": "テスト", "en": "test"}}
        assert get_text_for_language(item, "ja") == "テスト"
        assert get_text_for_language(item, "en") == "test"

    def test_returns_empty_for_missing_language(self):
        item = {"texts": {"ja": "テスト"}}
        result = get_text_for_language(item, "ko")
        assert result == ""

    def test_fallback_to_text_field(self):
        """沒有 texts 欄位時應退回到 text"""
        item = {"text": "hello", "language": "en"}
        result = get_text_for_language(item, "en")
        assert result == "hello"


# ============================================================================
# get_feed_items
# ============================================================================

class TestGetFeedItems:
    def test_empty_transcripts(self):
        assert get_feed_items([], "ja") == []

    def test_extracts_items_for_language(self):
        from datetime import datetime
        ts = datetime.now()
        transcripts = [
            {"texts": {"ja": "こんにちは", "en": "hello"}, "mode": "translate_en",
             "language": "en", "text": "hello", "timestamp": ts},
            {"texts": {"ja": "テスト", "en": "test"}, "mode": "translate_en",
             "language": "en", "text": "test", "timestamp": ts},
        ]
        items = get_feed_items(transcripts, "ja")
        assert len(items) == 2

    def test_skips_empty_texts(self):
        from datetime import datetime
        ts = datetime.now()
        transcripts = [
            {"texts": {"ja": "", "en": "hello"}, "mode": "translate_en",
             "language": "en", "text": "hello", "timestamp": ts},
        ]
        items = get_feed_items(transcripts, "ja")
        assert len(items) == 0
