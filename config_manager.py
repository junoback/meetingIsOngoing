#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模組 - 負責儲存和讀取 OpenAI API Key 及其他設定
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    """配置管理器類別"""

    def __init__(self):
        """初始化配置管理器"""
        # 配置目錄：~/.meeting-translator/
        self.config_dir = Path.home() / ".meeting-translator"
        self.config_file = self.config_dir / "config.json"
        self.meeting_config_file = self.config_dir / "meeting_config.json"
        self.terminology_file = self.config_dir / "terminology.json"

        # 確保配置目錄存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 初始化會議配置檔案
        self._init_meeting_config()

        # 初始化術語詞典
        self._init_terminology()

    def load_config(self) -> Dict[str, Any]:
        """
        讀取配置檔案

        Returns:
            配置字典，如果檔案不存在則返回空字典
        """
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"讀取配置檔案失敗：{e}")
            return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        儲存配置到檔案

        Args:
            config: 配置字典

        Returns:
            儲存成功返回 True，失敗返回 False
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"儲存配置檔案失敗：{e}")
            return False

    def get_api_key(self) -> Optional[str]:
        """
        讀取 OpenAI API Key

        Returns:
            API Key 字串，如果不存在則返回 None
        """
        config = self.load_config()
        return config.get('openai_api_key')

    def save_api_key(self, api_key: str) -> bool:
        """
        儲存 OpenAI API Key

        Args:
            api_key: API Key 字串

        Returns:
            儲存成功返回 True，失敗返回 False
        """
        config = self.load_config()
        config['openai_api_key'] = api_key
        return self.save_config(config)

    def clear_api_key(self) -> bool:
        """
        清除 OpenAI API Key

        Returns:
            清除成功返回 True，失敗返回 False
        """
        config = self.load_config()
        if 'openai_api_key' in config:
            del config['openai_api_key']
            return self.save_config(config)
        return True

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        讀取指定的設定值

        Args:
            key: 設定鍵名
            default: 預設值

        Returns:
            設定值，如果不存在則返回預設值
        """
        config = self.load_config()
        return config.get(key, default)

    def save_setting(self, key: str, value: Any) -> bool:
        """
        儲存指定的設定值

        Args:
            key: 設定鍵名
            value: 設定值

        Returns:
            儲存成功返回 True，失敗返回 False
        """
        config = self.load_config()
        config[key] = value
        return self.save_config(config)

    # ========================================================================
    # 會議配置管理
    # ========================================================================

    def _init_meeting_config(self):
        """初始化會議配置檔案（如果不存在則建立預設配置）"""
        if not self.meeting_config_file.exists():
            default_config = {
                "meeting_names": [
                    "eFlash IP 設計及半導體製程開發公司，每週例會",
                    "eFlash IP 設計及半導體製程開發公司，專案進度會議",
                    "eFlash IP 設計及半導體製程開發公司，技術討論會"
                ],
                "meeting_topics": [
                    "專案管理",
                    "技術開發",
                    "半導體製程開發、IC設計、故障分析"
                ]
            }
            try:
                with open(self.meeting_config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
            except IOError:
                pass

    def get_meeting_config(self) -> Dict:
        """
        讀取會議配置

        Returns:
            會議配置字典
        """
        if not self.meeting_config_file.exists():
            self._init_meeting_config()

        try:
            with open(self.meeting_config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"meeting_names": [], "meeting_topics": []}

    def add_meeting_name(self, name: str) -> bool:
        """
        添加新的會議名稱

        Args:
            name: 會議名稱

        Returns:
            成功返回 True
        """
        config = self.get_meeting_config()
        if name and name not in config.get('meeting_names', []):
            config.setdefault('meeting_names', []).append(name)
            try:
                with open(self.meeting_config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                return True
            except IOError:
                return False
        return False

    def add_meeting_topic(self, topic: str) -> bool:
        """
        添加新的會議主題

        Args:
            topic: 會議主題

        Returns:
            成功返回 True
        """
        config = self.get_meeting_config()
        if topic and topic not in config.get('meeting_topics', []):
            config.setdefault('meeting_topics', []).append(topic)
            try:
                with open(self.meeting_config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                return True
            except IOError:
                return False
        return False

    # ========================================================================
    # 術語詞典管理
    # ========================================================================

    def _init_terminology(self):
        """初始化術語詞典（如果不存在則建立預設範例）"""
        if not self.terminology_file.exists():
            default_terminology = {
                "terms": {
                    "project": "專案",
                    "task": "任務",
                    "deadline": "截止日期",
                    "review": "審查",
                    "wafer": "晶圓",
                    "process": "製程",
                    "yield": "良率",
                    "defect": "缺陷",
                    "failure analysis": "故障分析",
                    "semiconductor": "半導體"
                }
            }
            try:
                with open(self.terminology_file, 'w', encoding='utf-8') as f:
                    json.dump(default_terminology, f, ensure_ascii=False, indent=2)
            except IOError:
                pass

    def get_terminology(self) -> Dict[str, str]:
        """
        讀取術語詞典

        Returns:
            術語詞典 {日語: 中文}
        """
        if not self.terminology_file.exists():
            self._init_terminology()

        try:
            with open(self.terminology_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('terms', {})
        except (json.JSONDecodeError, IOError):
            return {}

    def add_term(self, source: str, target: str) -> bool:
        """
        添加術語

        Args:
            source: 原文（英文或日文）
            target: 中文翻譯

        Returns:
            成功返回 True
        """
        terms = self.get_terminology()
        terms[source] = target

        try:
            with open(self.terminology_file, 'w', encoding='utf-8') as f:
                json.dump({"terms": terms}, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def delete_term(self, source: str) -> bool:
        """
        刪除術語

        Args:
            source: 原文（英文或日文）

        Returns:
            成功返回 True
        """
        terms = self.get_terminology()
        if source in terms:
            del terms[source]
            try:
                with open(self.terminology_file, 'w', encoding='utf-8') as f:
                    json.dump({"terms": terms}, f, ensure_ascii=False, indent=2)
                return True
            except IOError:
                return False
        return False


# 建立全域配置管理器實例
config_manager = ConfigManager()
