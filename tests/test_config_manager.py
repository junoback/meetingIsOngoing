#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigManager 單元測試

測試配置讀寫、API key 管理、會議配置、術語字典等功能。
使用 tmp_path 隔離，不影響使用者實際設定。
"""

import json
import pytest
from pathlib import Path

# 直接 import class，避免觸發全域 singleton
import importlib


@pytest.fixture
def config_mgr(tmp_path):
    """建立隔離的 ConfigManager，config_dir 指向 tmp"""
    import config_manager as cm_module

    mgr = cm_module.ConfigManager()
    # 覆寫路徑到 tmp
    mgr.config_dir = tmp_path / "config"
    mgr.config_file = mgr.config_dir / "config.json"
    mgr.meeting_config_file = mgr.config_dir / "meeting_config.json"
    mgr.terminology_file = mgr.config_dir / "terminology.json"
    # defaults 也指向 tmp（不讀真正的 defaults/）
    mgr.defaults_dir = tmp_path / "defaults"
    mgr.default_config_file = mgr.defaults_dir / "config.json"
    mgr.default_meeting_config_file = mgr.defaults_dir / "meeting_config.json"
    mgr.default_terminology_file = mgr.defaults_dir / "terminology.json"
    return mgr


# ============================================================================
# 基本配置讀寫
# ============================================================================

class TestConfigBasics:
    def test_load_config_returns_empty_when_no_file(self, config_mgr):
        """無設定檔時應回傳空字典"""
        assert config_mgr.load_config() == {}

    def test_save_and_load_config(self, config_mgr):
        """儲存後再讀取應一致"""
        data = {"key1": "value1", "key2": 42}
        assert config_mgr.save_config(data) is True
        loaded = config_mgr.load_config()
        assert loaded == data

    def test_save_creates_config_dir(self, config_mgr):
        """儲存時應自動建立目錄"""
        assert not config_mgr.config_dir.exists()
        config_mgr.save_config({"test": True})
        assert config_mgr.config_dir.exists()

    def test_load_falls_back_to_defaults(self, config_mgr, tmp_path):
        """本機無設定時，退回 defaults/"""
        defaults_dir = tmp_path / "defaults"
        defaults_dir.mkdir()
        default_data = {"from_defaults": True, "language": "ja"}
        with open(defaults_dir / "config.json", "w") as f:
            json.dump(default_data, f)

        loaded = config_mgr.load_config()
        assert loaded == default_data

    def test_local_overrides_defaults(self, config_mgr, tmp_path):
        """本機設定存在時，不讀 defaults"""
        # 建立 default
        defaults_dir = tmp_path / "defaults"
        defaults_dir.mkdir()
        with open(defaults_dir / "config.json", "w") as f:
            json.dump({"source": "default"}, f)

        # 建立 local
        local_data = {"source": "local"}
        config_mgr.save_config(local_data)

        loaded = config_mgr.load_config()
        assert loaded["source"] == "local"

    def test_corrupt_json_returns_none(self, config_mgr):
        """損壞的 JSON 應回傳 None（走 fallback）"""
        config_mgr._ensure_config_dir()
        config_mgr.config_file.write_text("not valid json {{{")
        loaded = config_mgr.load_config()
        assert loaded == {}  # fallback 空字典


# ============================================================================
# API Key 管理
# ============================================================================

class TestApiKey:
    def test_get_api_key_none_when_missing(self, config_mgr):
        assert config_mgr.get_api_key() is None

    def test_save_and_get_api_key(self, config_mgr):
        config_mgr.save_api_key("sk-test123")
        assert config_mgr.get_api_key() == "sk-test123"

    def test_clear_api_key(self, config_mgr):
        config_mgr.save_api_key("sk-test123")
        assert config_mgr.clear_api_key() is True
        assert config_mgr.get_api_key() is None

    def test_clear_nonexistent_key_returns_true(self, config_mgr):
        """清除不存在的 key 應回傳 True（no-op）"""
        assert config_mgr.clear_api_key() is True

    def test_api_key_preserves_other_settings(self, config_mgr):
        """儲存 API key 不應覆蓋其他設定"""
        config_mgr.save_config({"language": "ja", "mode": "transcribe"})
        config_mgr.save_api_key("sk-test")
        config = config_mgr.load_config()
        assert config["language"] == "ja"
        assert config["openai_api_key"] == "sk-test"


# ============================================================================
# 通用設定
# ============================================================================

class TestSettings:
    def test_get_setting_default(self, config_mgr):
        assert config_mgr.get_setting("missing_key", 42) == 42

    def test_save_and_get_setting(self, config_mgr):
        config_mgr.save_setting("chunk_duration", 10)
        assert config_mgr.get_setting("chunk_duration") == 10

    def test_multiple_settings(self, config_mgr):
        config_mgr.save_setting("a", 1)
        config_mgr.save_setting("b", 2)
        assert config_mgr.get_setting("a") == 1
        assert config_mgr.get_setting("b") == 2


# ============================================================================
# 會議配置
# ============================================================================

class TestMeetingConfig:
    def test_default_meeting_config(self, config_mgr):
        config = config_mgr.get_meeting_config()
        assert "meeting_names" in config
        assert "meeting_topics" in config

    def test_add_meeting_name(self, config_mgr):
        assert config_mgr.add_meeting_name("Weekly Standup") is True
        config = config_mgr.get_meeting_config()
        assert "Weekly Standup" in config["meeting_names"]

    def test_add_duplicate_meeting_name(self, config_mgr):
        config_mgr.add_meeting_name("Meeting A")
        assert config_mgr.add_meeting_name("Meeting A") is False

    def test_add_empty_meeting_name(self, config_mgr):
        assert config_mgr.add_meeting_name("") is False

    def test_add_meeting_topic(self, config_mgr):
        assert config_mgr.add_meeting_topic("Design Review") is True
        config = config_mgr.get_meeting_config()
        assert "Design Review" in config["meeting_topics"]

    def test_add_duplicate_meeting_topic(self, config_mgr):
        config_mgr.add_meeting_topic("Topic A")
        assert config_mgr.add_meeting_topic("Topic A") is False


# ============================================================================
# 術語字典
# ============================================================================

class TestTerminology:
    def test_empty_terminology(self, config_mgr):
        terms = config_mgr.get_terminology()
        assert terms == {}

    def test_add_and_get_term(self, config_mgr):
        assert config_mgr.add_term("wafer", "晶圓") is True
        terms = config_mgr.get_terminology()
        assert terms["wafer"] == "晶圓"

    def test_add_multiple_terms(self, config_mgr):
        config_mgr.add_term("wafer", "晶圓")
        config_mgr.add_term("die", "晶粒")
        terms = config_mgr.get_terminology()
        assert len(terms) == 2

    def test_overwrite_existing_term(self, config_mgr):
        config_mgr.add_term("wafer", "晶圓")
        config_mgr.add_term("wafer", "矽片")
        terms = config_mgr.get_terminology()
        assert terms["wafer"] == "矽片"

    def test_delete_term(self, config_mgr):
        config_mgr.add_term("wafer", "晶圓")
        assert config_mgr.delete_term("wafer") is True
        terms = config_mgr.get_terminology()
        assert "wafer" not in terms

    def test_delete_nonexistent_term(self, config_mgr):
        assert config_mgr.delete_term("nonexistent") is False
