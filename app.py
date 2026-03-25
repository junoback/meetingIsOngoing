#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
即時會議翻譯 App - Streamlit 主程式
"""

import streamlit as st
import logging
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
import threading
import html as html_module

from config_manager import config_manager
from audio_recorder import AudioRecorder
from transcriber import Transcriber, TranscriberWorker
from styles import get_main_css
from templates import (
    LANGUAGE_OPTIONS, LANGUAGE_FILE_LABELS, LANGUAGE_TONE_CLASSES,
    MODE_ORDER, LEGACY_MODE_ALIASES,
    TOP_PANEL_HEIGHT, MAX_VISIBLE_FEED_ITEMS, MAX_VISIBLE_TRANSCRIPT_CARDS,
    STT_PROVIDERS, TRANSLATION_PROVIDERS, PROVIDER_KEY_GROUPS,
    normalize_mode, get_language_label, get_file_language_label, get_language_tone,
    get_mode_options, get_mode_summary, get_default_mode,
    get_flow_language_options, get_default_flow_language,
    limit_visible_items,
    normalize_transcript_payload, get_transcript_language_order,
    get_text_for_language, get_feed_items,
    build_language_panel, render_metric_card, render_sidebar_summary_card,
    render_transcript_card, render_live_feed_panel,
    render_keyboard_shortcuts,
)


# ============================================================================
# 日誌設定（取代直接 print，可控制輸出量）
# ============================================================================
logger = logging.getLogger("meeting-translator")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# 設定自動儲存（追蹤變更，避免每次 rerun 都寫入磁碟）
# ============================================================================
_last_persisted: dict = {}

def _persist_setting_if_changed(key: str, value):
    """只在值真正改變時才寫入 config，減少磁碟 I/O。

    用 config_manager 的實際儲存值做基準比對（不是記憶體快取），
    避免 widget 暫態重置被錯誤寫入。
    """
    # 首次呼叫時從 config 載入基準值
    if key not in _last_persisted:
        _last_persisted[key] = config_manager.get_setting(key)
    if _last_persisted.get(key) != value:
        config_manager.save_setting(key, value)
        _last_persisted[key] = value


def sanitize_filename(name: str) -> str:
    """清理檔案名稱中的特殊字元（共用工具函式）"""
    if not name:
        return ""
    return name.replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "").replace('"', "").replace("<", "").replace(">", "").replace("|", "")


def _timestamp_to_seconds(ts, reference_date=None) -> float:
    """
    將 datetime timestamp 轉為秒數（支援跨午夜）

    Args:
        ts: datetime 物件
        reference_date: 參考日期（會議開始時間），用於跨午夜計算
    """
    if reference_date and ts.date() > reference_date.date():
        # 跨午夜：加上跨過的天數
        day_offset = (ts.date() - reference_date.date()).days * 86400
        return ts.hour * 3600 + ts.minute * 60 + ts.second + day_offset
    return ts.hour * 3600 + ts.minute * 60 + ts.second


# 設定頁面配置
st.set_page_config(
    page_title="Meeting Translator — Real-time AI Translation",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 深色模式友善的 UI 主題（CSS 已提取至 styles.py）
st.markdown(get_main_css(), unsafe_allow_html=True)


# 常數、查找輔助、資料輔助、HTML 樣板建構器已移至 templates.py


def init_session_state():
    """初始化 Session State"""
    if 'recorder' not in st.session_state:
        st.session_state.recorder = None
    if 'transcriber' not in st.session_state:
        st.session_state.transcriber = None
    if 'worker' not in st.session_state:
        st.session_state.worker = None
    if 'controller' not in st.session_state:
        st.session_state.controller = None
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'is_paused' not in st.session_state:
        st.session_state.is_paused = False
    if 'api_key' not in st.session_state:
        st.session_state.api_key = config_manager.get_api_key() or ""
    if 'stt_provider' not in st.session_state:
        st.session_state.stt_provider = config_manager.get_setting('stt_provider', 'openai_whisper')
    if 'translation_provider' not in st.session_state:
        st.session_state.translation_provider = config_manager.get_setting('translation_provider', 'openai_gpt')
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    if 'error_messages' not in st.session_state:
        st.session_state.error_messages = []
    if 'show_bilingual' not in st.session_state:
        st.session_state.show_bilingual = config_manager.get_setting('show_bilingual', True)
    if 'meeting_name' not in st.session_state:
        st.session_state.meeting_name = ""
    if 'meeting_topic' not in st.session_state:
        st.session_state.meeting_topic = ""
    if 'live_transcript_path' not in st.session_state:
        st.session_state.live_transcript_path = None
    if 'language' not in st.session_state:
        st.session_state.language = config_manager.get_setting('language', "ja")
    if 'target_language' not in st.session_state:
        st.session_state.target_language = config_manager.get_setting('target_language', "zh")
    if 'mode' not in st.session_state:
        st.session_state.mode = config_manager.get_setting('mode', "translate_target")
    if st.session_state.mode in LEGACY_MODE_ALIASES:
        st.session_state.mode = LEGACY_MODE_ALIASES[st.session_state.mode]
    if 'reading_flow_language' not in st.session_state:
        st.session_state.reading_flow_language = st.session_state.target_language
    if 'viewer_mode' not in st.session_state:
        st.session_state.viewer_mode = False
    if 'viewer_host' not in st.session_state:
        st.session_state.viewer_host = config_manager.get_setting('viewer_host', '')




def add_debug_log(message: str):
    """添加調試日誌"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.debug_logs.append(log_entry)
    # 只保留最近 50 條日誌
    if len(st.session_state.debug_logs) > 50:
        st.session_state.debug_logs = st.session_state.debug_logs[-50:]
    logger.info(log_entry)


def add_error_message(message: str):
    """添加錯誤訊息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    error_entry = f"[{timestamp}] ❌ {message}"
    st.session_state.error_messages.append(error_entry)
    if len(st.session_state.error_messages) > 10:
        st.session_state.error_messages = st.session_state.error_messages[-10:]
    logger.error(error_entry)


def get_status_metadata():
    """回傳目前錄音狀態的文案與樣式"""
    if st.session_state.is_recording:
        if st.session_state.is_paused:
            return {
                "label": "Paused",
                "description": "Capture is temporarily on hold. Resume when the conversation starts again.",
                "css_class": "status-paused",
                "icon_html": "<span class='status-icon'>⏸</span>"
            }
        return {
            "label": "Recording",
            "description": "Audio capture and translation are running live. New lines will appear below in real time.",
            "css_class": "status-recording",
            "icon_html": "<span class='recording-indicator'></span>"
        }
    return {
        "label": "Ready",
        "description": "Set the audio route and meeting context, then start a fresh session.",
        "css_class": "status-stopped",
        "icon_html": "<span class='status-icon'>⏹</span>"
    }




def create_live_transcript_file(
    meeting_name: str = "",
    meeting_topic: str = "",
    recording_file_path: str = ""
) -> str:
    """
    創建即時逐字稿檔案（錄音開始時調用）

    檔名與錄音檔對應（同 base name，不同目錄與副檔名），
    方便事後對照音檔與文字記錄。

    Args:
        meeting_name: 會議名稱
        meeting_topic: 會議主題
        recording_file_path: 對應的錄音檔路徑（用來衍生一致的檔名）

    Returns:
        檔案路徑
    """
    transcripts_dir = Path("transcripts")
    transcripts_dir.mkdir(exist_ok=True)

    # 與錄音檔共用 base name（僅副檔名不同）
    if recording_file_path:
        base_name = Path(recording_file_path).stem  # e.g. "每週例會_主題_20260324_151153"
        filename = f"{base_name}.txt"
    else:
        # fallback：獨立生成（不應走到這裡）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_parts = ["transcript"]
        if meeting_name:
            filename_parts.append(sanitize_filename(meeting_name))
        if meeting_topic:
            filename_parts.append(sanitize_filename(meeting_topic))
        filename_parts.append(timestamp)
        filename = "_".join(filename_parts) + ".txt"

    file_path = transcripts_dir / filename

    # 寫入標題
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("即時會議逐字稿 — Real-time Meeting Transcript\n")
        if meeting_name:
            f.write(f"會議名稱：{meeting_name}\n")
        if meeting_topic:
            f.write(f"會議主題：{meeting_topic}\n")
        f.write(f"開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if recording_file_path:
            f.write(f"對應錄音：{Path(recording_file_path).name}\n")
        f.write("=" * 60 + "\n\n")

    return str(file_path)


def append_to_live_transcript(file_path: str, item: dict):
    """
    追加內容到即時逐字稿檔案

    Args:
        file_path: 檔案路徑
        item: 辨識結果字典
    """
    if not file_path or not Path(file_path).exists():
        return

    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"[{item['timestamp'].strftime('%H:%M:%S')}]")
        f.write(f" (延遲：{item['latency']}秒)\n")

        for language_code in get_transcript_language_order(item):
            text = get_text_for_language(item, language_code)
            if text:
                f.write(f"{get_file_language_label(language_code)}：{text}\n")

        f.write("-" * 60 + "\n\n")


# ============================================================================
# Active Session Marker（跨 session / 跨機器共享錄音狀態）
# ============================================================================
ACTIVE_SESSION_MARKER = Path("transcripts/.active_session.json")
TRANSCRIPT_SHARE_PORT = 8580  # 主電腦的 transcript 分享 HTTP port


def _write_active_session_marker(transcript_path: str, meeting_name: str = "", meeting_topic: str = ""):
    """錄音開始時寫入 marker，讓其他 session / 機器進入 Viewer 模式"""
    Path("transcripts").mkdir(exist_ok=True)
    marker = {
        "transcript_path": transcript_path,
        "meeting_name": meeting_name,
        "meeting_topic": meeting_topic,
        "started_at": datetime.now().isoformat(),
    }
    ACTIVE_SESSION_MARKER.write_text(json.dumps(marker, ensure_ascii=False), encoding='utf-8')


def _read_active_session_marker() -> dict | None:
    """讀取本機 active session marker，不存在或超過 12 小時視為過期"""
    if not ACTIVE_SESSION_MARKER.exists():
        return None
    try:
        marker = json.loads(ACTIVE_SESSION_MARKER.read_text(encoding='utf-8'))
        started = datetime.fromisoformat(marker.get("started_at", ""))
        if (datetime.now() - started).total_seconds() > 43200:
            ACTIVE_SESSION_MARKER.unlink(missing_ok=True)
            return None
        marker['_source'] = 'local'
        return marker
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _read_remote_marker(host_ip: str) -> dict | None:
    """從主電腦的 HTTP server 讀取 active session marker"""
    if not host_ip:
        return None
    url = f"http://{host_ip}:{TRANSCRIPT_SHARE_PORT}/.active_session.json"
    content = _fetch_remote_file(url)
    if not content:
        return None
    try:
        marker = json.loads(content)
        started = datetime.fromisoformat(marker.get("started_at", ""))
        if (datetime.now() - started).total_seconds() > 43200:
            return None
        marker['_source'] = 'remote'
        marker['_remote_host'] = host_ip
        return marker
    except (json.JSONDecodeError, ValueError):
        return None


def _clear_active_session_marker():
    """錄音停止時清除 marker"""
    if ACTIVE_SESSION_MARKER.exists():
        ACTIVE_SESSION_MARKER.unlink(missing_ok=True)


# ============================================================================
# Transcript 分享 HTTP Server（主電腦用，讓子電腦讀取 transcripts/）
# ============================================================================
_transcript_server_started = False


class _QuietHTTPHandler(SimpleHTTPRequestHandler):
    """不輸出 access log 的 HTTP handler"""
    def log_message(self, format, *args):
        pass  # 靜默，避免 console 充斥 HTTP log


def _start_transcript_server():
    """啟動背景 HTTP server，提供 transcripts/ 目錄的檔案"""
    global _transcript_server_started
    if _transcript_server_started:
        return
    try:
        handler = partial(_QuietHTTPHandler, directory="transcripts")
        server = HTTPServer(("0.0.0.0", TRANSCRIPT_SHARE_PORT), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _transcript_server_started = True
        logger.info(f"📡 Transcript 分享 server 已啟動 (port {TRANSCRIPT_SHARE_PORT})")
    except OSError as e:
        logger.warning(f"📡 Transcript server 啟動失敗（port {TRANSCRIPT_SHARE_PORT} 可能已被佔用）：{e}")


def _fetch_remote_file(url: str) -> str | None:
    """從遠端 HTTP URL 讀取文字內容"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.read().decode('utf-8')
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _parse_live_transcript_content(content: str) -> list[dict]:
    """
    解析 live transcript 內容字串，回傳 feed items 列表。
    格式：[HH:MM:SS] (延遲：X.XX秒)\\n語言：文字\\n---...
    """
    items = []
    entries = content.split("-" * 60)
    for entry in entries:
        entry = entry.strip()
        if not entry or entry.startswith("="):
            continue

        lines = entry.split("\n")
        timestamp = ""
        texts = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("即時會議") or line.startswith("Real-time") or \
               line.startswith("會議名稱") or line.startswith("會議主題") or \
               line.startswith("開始時間") or line.startswith("對應錄音"):
                continue
            if line.startswith("[") and "]" in line:
                timestamp = line[1:line.index("]")]
                continue
            if "：" in line:
                label, _, text = line.partition("：")
                if text:
                    texts[label.strip()] = text.strip()

        if timestamp and texts:
            items.append({"timestamp": timestamp, "texts": texts})

    return items


def _parse_live_transcript_file(file_path: str, remote_host: str = "") -> list[dict]:
    """
    解析 live transcript 檔案（支援本機或遠端）。

    Args:
        file_path: 檔案路徑（本機用完整路徑，遠端用檔名）
        remote_host: 遠端主電腦 IP（空字串表示讀本機）
    """
    if remote_host:
        filename = Path(file_path).name
        url = f"http://{remote_host}:{TRANSCRIPT_SHARE_PORT}/{filename}"
        content = _fetch_remote_file(url)
        if not content:
            return []
        return _parse_live_transcript_content(content)
    else:
        if not file_path or not Path(file_path).exists():
            return []
        try:
            content = Path(file_path).read_text(encoding='utf-8')
        except OSError:
            return []
        return _parse_live_transcript_content(content)


def save_transcript_to_file(transcripts: list, meeting_name: str = "", meeting_topic: str = "", language_selection: str = "all") -> str:
    """
    將逐字稿儲存為文字檔

    Args:
        transcripts: 逐字稿列表
        meeting_name: 會議名稱
        meeting_topic: 會議主題
        language_selection: 語言選擇 ("ja", "en", "zh", "all")

    Returns:
        檔案路徑
    """
    transcripts_dir = Path("transcripts")
    transcripts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 構建檔案名稱
    filename_parts = ["transcript"]
    if meeting_name:
        filename_parts.append(sanitize_filename(meeting_name))
    if meeting_topic:
        filename_parts.append(sanitize_filename(meeting_topic))
    filename_parts.append(timestamp)

    filename = "_".join(filename_parts) + ".txt"
    file_path = transcripts_dir / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("會議逐字稿\n")
        if meeting_name:
            f.write(f"會議名稱：{meeting_name}\n")
        if meeting_topic:
            f.write(f"會議主題：{meeting_topic}\n")
        f.write(f"產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for item in reversed(transcripts):
            f.write(f"[{item['timestamp'].strftime('%H:%M:%S')}]")
            f.write(f" (延遲：{item['latency']}秒)\n")

            if language_selection == "all":
                for language_code in get_transcript_language_order(item):
                    text_to_write = get_text_for_language(item, language_code)
                    if text_to_write:
                        f.write(f"{get_file_language_label(language_code)}：{text_to_write}\n")
            else:
                text_to_write = get_text_for_language(item, language_selection)
                if text_to_write:
                    f.write(f"{text_to_write}\n")

            f.write("-" * 60 + "\n\n")

    return str(file_path)


def _format_srt_time(seconds: float) -> str:
    """將秒數格式化為 SRT 時間碼 (HH:MM:SS,mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt_time(seconds: float) -> str:
    """將秒數格式化為 VTT 時間碼 (HH:MM:SS.mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def save_transcript_to_srt(
    transcripts: list,
    language_selection: str = "all",
    meeting_name: str = "",
    meeting_topic: str = ""
) -> str:
    """
    將逐字稿儲存為 SRT 字幕檔

    每個 chunk 為一個 subtitle entry，時間碼根據 timestamp 與 duration 計算。
    """
    transcripts_dir = Path("transcripts")
    transcripts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_parts = ["transcript"]
    if meeting_name:
        filename_parts.append(sanitize_filename(meeting_name))
    filename_parts.append(timestamp)
    filename = "_".join(filename_parts) + ".srt"
    file_path = transcripts_dir / filename

    # 取得最早的 transcript 作為跨午夜參考
    ordered = list(reversed(transcripts))
    ref_date = ordered[0]['timestamp'] if ordered else None

    with open(file_path, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(ordered, 1):
            start_sec = _timestamp_to_seconds(item['timestamp'], ref_date)
            end_sec = start_sec + item.get('duration', 5.0)

            start_tc = _format_srt_time(start_sec)
            end_tc = _format_srt_time(end_sec)

            # 收集要顯示的文字
            lines = []
            if language_selection == "all":
                for lc in get_transcript_language_order(item):
                    text = get_text_for_language(item, lc)
                    if text:
                        lines.append(text)
            else:
                text = get_text_for_language(item, language_selection)
                if text:
                    lines.append(text)

            if lines:
                f.write(f"{idx}\n")
                f.write(f"{start_tc} --> {end_tc}\n")
                f.write("\n".join(lines) + "\n\n")

    return str(file_path)


def save_transcript_to_vtt(
    transcripts: list,
    language_selection: str = "all",
    meeting_name: str = "",
    meeting_topic: str = ""
) -> str:
    """
    將逐字稿儲存為 WebVTT 字幕檔
    """
    transcripts_dir = Path("transcripts")
    transcripts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_parts = ["transcript"]
    if meeting_name:
        filename_parts.append(sanitize_filename(meeting_name))
    filename_parts.append(timestamp)
    filename = "_".join(filename_parts) + ".vtt"
    file_path = transcripts_dir / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n")
        if meeting_name or meeting_topic:
            note_parts = [p for p in [meeting_name, meeting_topic] if p]
            f.write(f"NOTE {' — '.join(note_parts)}\n")
        f.write("\n")

        ordered = list(reversed(transcripts))
        ref_date = ordered[0]['timestamp'] if ordered else None

        for idx, item in enumerate(ordered, 1):
            start_sec = _timestamp_to_seconds(item['timestamp'], ref_date)
            end_sec = start_sec + item.get('duration', 5.0)

            start_tc = _format_vtt_time(start_sec)
            end_tc = _format_vtt_time(end_sec)

            lines = []
            if language_selection == "all":
                for lc in get_transcript_language_order(item):
                    text = get_text_for_language(item, lc)
                    if text:
                        lines.append(text)
            else:
                text = get_text_for_language(item, language_selection)
                if text:
                    lines.append(text)

            if lines:
                f.write(f"{start_tc} --> {end_tc}\n")
                f.write("\n".join(lines) + "\n\n")

    return str(file_path)


class ProcessingController:
    """處理控制器（避免在子執行緒中訪問 st.session_state）"""

    # 記憶體中保留的最大 transcript 數量（更早的仍保存在 live transcript 檔案中）
    MAX_IN_MEMORY_TRANSCRIPTS = 500

    def __init__(self, recorder, worker):
        self.recorder = recorder
        self.worker = worker
        self.stop_flag = False
        self.is_paused = False
        self.transcripts = []
        self.total_transcript_count = 0  # 總筆數（含已淘汰的）
        self.error_messages = []
        self.thread = None
        self.live_transcript_path = None  # 即時逐字稿檔案路徑

    def set_live_transcript_path(self, path: str):
        """設定即時逐字稿檔案路徑"""
        self.live_transcript_path = path

    def start(self):
        """啟動處理執行緒"""
        self.stop_flag = False
        self.thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.thread.start()
        logger.info("✅ ProcessingController 執行緒已啟動")

    def stop(self):
        """停止處理執行緒"""
        self.stop_flag = True
        if self.thread:
            self.thread.join(timeout=2)

    def pause(self):
        """暫停處理"""
        self.is_paused = True

    def resume(self):
        """恢復處理"""
        self.is_paused = False

    def _processing_loop(self):
        """處理迴圈（在背景執行緒中執行）"""
        logger.info("🔄 處理迴圈已啟動 (worker_running=%s)", self.worker.is_running)
        consecutive_errors = 0

        while not self.stop_flag:
            try:
                if not self.is_paused:
                    # 從錄音器取得音訊片段
                    chunk = self.recorder.get_next_chunk(timeout=0.5)
                    if chunk:
                        logger.info("🎵 音訊片段 %.1fs → API 佇列 (qsize=%d)",
                                    chunk['duration'], self.worker.get_queue_size())
                        self.worker.add_audio_chunk(chunk)

                    # 從 Worker 取得處理結果
                    result = self.worker.get_result(timeout=0.1)
                    if result:
                        if result.get('success', True):
                            self.transcripts.append(result)
                            self.total_transcript_count += 1
                            # 記憶體限制：超過上限時淘汰最舊的（檔案中仍完整保留）
                            if len(self.transcripts) > self.MAX_IN_MEMORY_TRANSCRIPTS:
                                self.transcripts = self.transcripts[-self.MAX_IN_MEMORY_TRANSCRIPTS:]
                            logger.info("✅ 辨識完成：%s", result['text'][:50])

                            if self.live_transcript_path:
                                append_to_live_transcript(self.live_transcript_path, result)
                        else:
                            error_msg = result.get('error', '未知錯誤')
                            logger.warning("❌ API 失敗：%s", error_msg)
                            self.error_messages.append(
                                f"[{datetime.now().strftime('%H:%M:%S')}] API 失敗：{error_msg}"
                            )

                    consecutive_errors = 0  # 正常迴圈完成，重置錯誤計數
                else:
                    time.sleep(0.1)

            except Exception as e:
                consecutive_errors += 1
                logger.error("❌ 處理迴圈錯誤 (#%d)：%s", consecutive_errors, e, exc_info=True)
                self.error_messages.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 內部錯誤：{e}"
                )
                # 指數退避：連續錯誤時逐漸拉長等待，避免 CPU 空轉
                backoff = min(1.0 * (2 ** (consecutive_errors - 1)), 30.0)
                time.sleep(backoff)

        logger.info("⏹️ 處理迴圈已停止")


def _force_sync_widget_keys():
    """強制同步所有 widget key 到權威 session_state 值。

    【關鍵修復】st.rerun(scope="app") 從 fragment 內觸發時，
    Streamlit 可能在 full-page rerun 時把 sidebar widget key 重置為 index=0。
    在 rerun 前呼叫此函式，確保 widget key 與權威值一致，
    這樣即使 Streamlit 重建 widget，也會從 session_state 讀到正確值。
    """
    language_options = list(LANGUAGE_OPTIONS.keys())

    lang = st.session_state.get('language', 'ja')
    if lang in language_options:
        st.session_state.language_widget = lang

    target = st.session_state.get('target_language', 'zh')
    if target in language_options:
        st.session_state.target_language_widget = target

    mode_opts = get_mode_options(
        st.session_state.get('language', 'ja'),
        st.session_state.get('target_language', 'zh')
    )
    mode_val = st.session_state.get('mode', 'translate_target')
    if mode_val in mode_opts:
        st.session_state.mode_widget = mode_val

    # Reading Flow Language — 此 widget 在 fragment 內，
    # 若從 fragment 內部呼叫（按鈕），widget 已 instantiated，不可修改 key。
    # 用 try/except 安全處理；index= fallback 仍會保護它。
    try:
        flow_opts = get_flow_language_options(
            normalize_mode(mode_val),
            st.session_state.get('language', 'ja'),
            st.session_state.get('target_language', 'zh')
        )
        flow_val = st.session_state.get('reading_flow_language')
        if flow_val in flow_opts:
            st.session_state.reading_flow_language_widget = flow_val
    except Exception:
        pass  # widget 已 instantiated，靠 index= fallback


def start_recording():
    """開始錄音"""
    # 檢查所有需要的 API key 是否已設定
    stt_prov = st.session_state.get('stt_provider', 'openai_whisper')
    trans_prov = st.session_state.get('translation_provider', 'openai_gpt')
    stt_grp = PROVIDER_KEY_GROUPS.get(stt_prov, 'openai')
    trans_grp = PROVIDER_KEY_GROUPS.get(trans_prov, 'openai')

    def _has_key(grp: str) -> bool:
        """檢查指定 group 是否有可用的 API key"""
        if config_manager.get_provider_api_key(grp):
            return True
        if st.session_state.get(f'api_key_{grp}'):
            return True
        if grp == "openai" and st.session_state.get('api_key'):
            return True
        return False

    missing = []
    if not _has_key(stt_grp):
        missing.append(f"{stt_grp.upper()} ({STT_PROVIDERS[stt_prov]['name']})")
    if not _has_key(trans_grp):
        missing.append(f"{trans_grp.upper()} ({TRANSLATION_PROVIDERS[trans_prov]['name']})")
    if missing:
        st.error(f"請先輸入 API Key：{', '.join(missing)}")
        add_error_message(f"缺少 API Key：{', '.join(missing)}")
        return

    try:
        add_debug_log("🎬 開始初始化錄音...")

        # 清空調試日誌和錯誤訊息
        st.session_state.debug_logs = []
        st.session_state.error_messages = []

        # 初始化錄音器
        if st.session_state.recorder is None:
            st.session_state.recorder = AudioRecorder()
            add_debug_log("✅ 錄音器已初始化")

        # 設定錄音參數
        device_name = st.session_state.get('selected_device', 'BlackHole 2ch')
        add_debug_log(f"🔊 設定音訊裝置：{device_name}")

        try:
            st.session_state.recorder.set_device(device_name=device_name)
            add_debug_log(f"✅ 音訊裝置設定成功：{device_name}")
        except ValueError as e:
            # 音訊裝置找不到是嚴重問題 — 可能錄到錯誤來源
            st.error(
                f"⚠️ 找不到音訊裝置「{device_name}」！\n\n"
                f"已退回系統預設裝置（可能是內建麥克風，不是會議音源）。\n"
                f"請確認 BlackHole 2ch 已安裝並在 Audio MIDI Setup 中啟用。"
            )
            add_error_message(f"⚠️ 找不到裝置 '{device_name}'，已退回系統預設 — 請確認音源")
            st.session_state.recorder.set_device(device_index=None)

        st.session_state.recorder.set_chunk_duration(st.session_state.chunk_duration)
        st.session_state.recorder.set_silence_threshold(st.session_state.silence_threshold)
        st.session_state.recorder.vad_enabled = st.session_state.get('vad_enabled', True)
        vad_label = "VAD smart" if st.session_state.recorder.vad_enabled else "fixed"
        add_debug_log(f"⚙️ 音訊片段長度：{st.session_state.chunk_duration}秒，靜音閾值：{st.session_state.silence_threshold}，切割模式：{vad_label}")

        # 初始化 Transcriber（依選擇的 Provider 建立對應的 client）
        stt_prov = st.session_state.get('stt_provider', 'openai_whisper')
        trans_prov = st.session_state.get('translation_provider', 'openai_gpt')
        stt_group = PROVIDER_KEY_GROUPS.get(stt_prov, 'openai')
        trans_group = PROVIDER_KEY_GROUPS.get(trans_prov, 'openai')

        def _resolve_api_key(group: str) -> str:
            """依序從 config → sidebar widget → 舊 api_key 取得 key"""
            # 1. 從 config 檔案讀取（最可靠）
            key = config_manager.get_provider_api_key(group)
            if key:
                return key
            # 2. 從 sidebar 的 text_input widget 直接讀（剛輸入還未存檔的情況）
            widget_key = st.session_state.get(f'api_key_{group}', '')
            if widget_key:
                # 順便存一份到 config
                config_manager.save_provider_api_key(group, widget_key)
                return widget_key
            # 3. 只有 openai group 才 fallback 到舊的 api_key
            if group == "openai":
                return st.session_state.get('api_key', '')
            return ''

        stt_key = _resolve_api_key(stt_group)
        trans_key = _resolve_api_key(trans_group)

        add_debug_log(f"🤖 正在初始化 STT={STT_PROVIDERS[stt_prov]['name']} ({stt_group}), 翻譯={TRANSLATION_PROVIDERS[trans_prov]['name']} ({trans_group})")
        add_debug_log(f"🔑 STT key: {stt_key[:8]}... , Trans key: {trans_key[:8]}..." if stt_key and trans_key else f"⚠️ Key 缺失！STT={bool(stt_key)}, Trans={bool(trans_key)}")

        st.session_state.transcriber = Transcriber(
            stt_api_key=stt_key,
            stt_provider=stt_prov,
            translation_api_key=trans_key,
            translation_provider=trans_prov,
        )
        add_debug_log(f"✅ API 已初始化")

        st.session_state.transcriber.set_mode(st.session_state.mode)
        st.session_state.transcriber.set_language(st.session_state.language)
        st.session_state.transcriber.set_target_language(st.session_state.target_language)
        add_debug_log(
            f"🌐 模式：{st.session_state.mode}，來源語言：{st.session_state.language}，母語：{st.session_state.target_language}"
        )

        # 設定會議上下文（提高翻譯準確性）
        terminology = config_manager.get_terminology()
        st.session_state.transcriber.set_meeting_context(
            meeting_topic=st.session_state.meeting_topic,
            terminology=terminology
        )
        add_debug_log(
            f"📚 已載入會議上下文：主題={st.session_state.meeting_topic}，術語數={len(terminology)}"
        )

        # 初始化 Worker（每次都重新初始化以確保使用最新的 Transcriber）
        if st.session_state.worker is not None:
            add_debug_log("🛑 停止舊的 Worker 執行緒...")
            st.session_state.worker.stop()

        add_debug_log("👷 正在啟動 Worker 執行緒...")
        st.session_state.worker = TranscriberWorker(st.session_state.transcriber)
        st.session_state.worker.start()
        add_debug_log("✅ Worker 執行緒已啟動")

        # 開始錄音
        add_debug_log("🎙️ 正在開啟音訊串流...")
        recording_file = st.session_state.recorder.start_recording(
            "recordings",
            meeting_name=st.session_state.meeting_name,
            meeting_topic=st.session_state.meeting_topic
        )
        st.session_state.is_recording = True
        st.session_state.is_paused = False
        add_debug_log(f"✅ 錄音已開始，檔案：{recording_file}")

        # 啟動處理控制器
        add_debug_log("🚀 正在啟動處理控制器...")
        st.session_state.controller = ProcessingController(
            st.session_state.recorder,
            st.session_state.worker
        )

        # 創建即時逐字稿檔案（與錄音檔對應）
        add_debug_log("📝 正在創建即時逐字稿檔案...")
        live_transcript_path = create_live_transcript_file(
            meeting_name=st.session_state.meeting_name,
            meeting_topic=st.session_state.meeting_topic,
            recording_file_path=recording_file
        )
        st.session_state.controller.set_live_transcript_path(live_transcript_path)
        st.session_state.live_transcript_path = live_transcript_path
        add_debug_log(f"✅ 即時逐字稿檔案已創建：{live_transcript_path}")

        # 寫入 active session marker（讓手機等遠端 session 進入 Viewer 模式）
        _write_active_session_marker(
            live_transcript_path,
            meeting_name=st.session_state.meeting_name,
            meeting_topic=st.session_state.meeting_topic
        )

        st.session_state.controller.start()
        add_debug_log("✅ 處理控制器已啟動")

        st.success(f"✅ 錄音已開始！請說話測試...")
        add_debug_log("🚀 所有系統已就緒，等待音訊輸入...")

    except Exception as e:
        error_msg = f"啟動錄音失敗：{e}"
        st.error(error_msg)
        add_error_message(error_msg)
        import traceback
        add_debug_log(f"錯誤詳情：{traceback.format_exc()}")


def pause_recording():
    """暫停錄音"""
    if st.session_state.recorder:
        st.session_state.recorder.pause_recording()
        st.session_state.is_paused = True
    if st.session_state.controller:
        st.session_state.controller.pause()


def resume_recording():
    """恢復錄音"""
    if st.session_state.recorder:
        st.session_state.recorder.resume_recording()
        st.session_state.is_paused = False
    if st.session_state.controller:
        st.session_state.controller.resume()


def stop_recording():
    """停止錄音"""
    if st.session_state.recorder:
        # 停止處理控制器
        if st.session_state.controller:
            st.session_state.controller.stop()

        # 停止錄音
        st.session_state.recorder.stop_recording()
        st.session_state.is_recording = False
        st.session_state.is_paused = False

        # 停止 Worker
        if st.session_state.worker:
            st.session_state.worker.stop()
            st.session_state.worker = None

        # 清除 active session marker
        _clear_active_session_marker()

        st.success("錄音已停止")


# ============================================================================
# Viewer Mode（手機/遠端裝置唯讀檢視）
# ============================================================================

def _render_viewer_mode(marker: dict):
    """
    遠端 Viewer 模式：讀取主電腦正在寫入的 live transcript 檔案，
    使用與主畫面相同的 Reading Flow 面板顯示。
    適用於手機、平板、Parallels VM 等。
    """
    transcript_path = marker.get("transcript_path", "")
    meeting_name = marker.get("meeting_name", "") or "Untitled meeting"
    meeting_topic = marker.get("meeting_topic", "") or "Topic not set"
    remote_host = marker.get("_remote_host", "")  # 空 = 本機, 有值 = 遠端

    st.markdown(get_main_css(), unsafe_allow_html=True)

    # 返回按鈕（小巧不佔空間）
    if st.button("← 返回主畫面", key='viewer_back'):
        st.session_state.viewer_mode = False
        st.rerun()

    # 語言選擇（與主畫面相同的 LANGUAGE_OPTIONS）
    viewer_language_options = list(LANGUAGE_OPTIONS.keys())
    viewer_default_idx = viewer_language_options.index('zh') if 'zh' in viewer_language_options else 0

    flow_selector_col, flow_selector_spacer = st.columns([2.3, 3.7])
    with flow_selector_col:
        st.markdown("<div class='section-label'>Reading Flow Language</div>", unsafe_allow_html=True)
        viewer_flow_lang = st.selectbox(
            "Reading Flow Language",
            viewer_language_options,
            index=viewer_default_idx,
            format_func=get_language_label,
            key='viewer_flow_language',
            label_visibility="collapsed"
        )

    # 從檔案語言標籤到語言代碼的對照
    _file_label_to_code = {v: k for k, v in LANGUAGE_FILE_LABELS.items()}

    # 自動刷新的 fragment — 使用與主畫面相同的 Reading Flow 面板
    @st.fragment(run_every=timedelta(seconds=2))
    def _viewer_feed():
        # 檢查 marker 是否還存在（錄音是否已結束）
        if remote_host:
            current_marker = _read_remote_marker(remote_host)
        else:
            current_marker = _read_active_session_marker()
        if not current_marker:
            st.warning("⏹ 錄音已結束。點擊「返回主畫面」繼續使用。")
            return

        items = _parse_live_transcript_file(transcript_path, remote_host=remote_host)

        # 將解析結果轉為 feed_items 格式（與 get_feed_items 輸出一致）
        viewer_lang_label = get_file_language_label(viewer_flow_lang)
        feed_items = []
        for item in items:
            text = item["texts"].get(viewer_lang_label, "")
            if not text:
                # fallback：嘗試用語言代碼反查
                for label, t in item["texts"].items():
                    code = _file_label_to_code.get(label)
                    if code == viewer_flow_lang and t:
                        text = t
                        break
            if not text:
                # 最終 fallback：用第一個可用的語言
                text = next(iter(item["texts"].values()), "")
            if text:
                feed_items.append({"timestamp": item["timestamp"], "text": text})

        visible_feed_items, hidden = limit_visible_items(feed_items, MAX_VISIBLE_FEED_ITEMS)

        # 使用與主畫面完全相同的 Reading Flow 面板
        status_metadata = {
            "label": "Live Viewer",
            "description": "正在接收另一台裝置的即時翻譯",
            "css_class": "status-recording",
            "icon_html": "<span class='status-icon'>📡</span>"
        }

        hero_col1, hero_col2 = st.columns([5, 1])
        with hero_col1:
            render_live_feed_panel(
                visible_feed_items,
                viewer_flow_lang,
                status_metadata,
                meeting_name,
                meeting_topic,
                is_recording=True  # 讓面板顯示「錄音中」樣式
            )
            if hidden > 0:
                st.caption(
                    f"僅顯示最近 {len(visible_feed_items)} 段內容。完整記錄在逐字稿檔案中。"
                )

        with hero_col2:
            total_count = len(feed_items)
            started_at = current_marker.get("started_at", "")
            elapsed_str = ""
            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at)
                    elapsed = datetime.now() - start_dt
                    mins = int(elapsed.total_seconds() // 60)
                    secs = int(elapsed.total_seconds() % 60)
                    elapsed_str = f"{mins}:{secs:02d}"
                except ValueError:
                    pass

            st.markdown(
                f"""
                <div class='status-panel'>
                    <div class='status-panel-title'>Viewer Status</div>
                    <div class='status-badge status-recording'>
                        <span class='status-icon'>📡</span>
                        <span>Live Viewer</span>
                    </div>
                    <div class='status-panel-copy'>正在接收另一台裝置的即時翻譯</div>
                    <div class='status-grid'>
                        <div class='status-mini'>
                            <div class='status-mini-label'>Lines</div>
                            <div class='status-mini-value'>{total_count}</div>
                        </div>
                        <div class='status-mini'>
                            <div class='status-mini-label'>Elapsed</div>
                            <div class='status-mini-value'>{elapsed_str or '—'}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    _viewer_feed()


# ============================================================================
# 主程式
# ============================================================================

def main():
    """主程式"""
    init_session_state()

    # 啟動 transcript 分享 HTTP server（每台電腦都啟動，供其他機器讀取）
    _start_transcript_server()

    # ========================================================================
    # Viewer Mode：手動切換，檢視主電腦的即時翻譯
    # ========================================================================
    if st.session_state.viewer_mode and not st.session_state.is_recording:
        viewer_host = st.session_state.get('viewer_host', '')
        # 優先查遠端（有設定主電腦 IP 時），其次查本機
        if viewer_host:
            active_marker = _read_remote_marker(viewer_host)
        else:
            active_marker = _read_active_session_marker()
        if active_marker:
            _render_viewer_mode(active_marker)
            return
        else:
            st.session_state.viewer_mode = False

    # ========================================================================
    # 側邊欄
    # ========================================================================
    with st.sidebar:
        # 讀取會議配置
        meeting_config = config_manager.get_meeting_config()
        meeting_names = meeting_config.get('meeting_names', [])
        meeting_topics = meeting_config.get('meeting_topics', [])

        st.markdown("""
        <div class='sidebar-brand'>
            <div class='sidebar-kicker'>Meeting Context</div>
            <div class='sidebar-title'>會議名稱與主題</div>
        </div>
        """, unsafe_allow_html=True)

        # 會議名稱
        meeting_name_options = meeting_names + ["+ 新增會議名稱"]
        selected_meeting_name = st.selectbox(
            "會議名稱",
            meeting_name_options,
            disabled=st.session_state.is_recording,
            key='meeting_name_select'
        )

        if selected_meeting_name == "+ 新增會議名稱":
            new_meeting_name = st.text_input(
                "輸入新的會議名稱",
                disabled=st.session_state.is_recording,
                key='new_meeting_name_input'
            )
            if st.button("➕ 添加會議名稱", disabled=st.session_state.is_recording):
                if new_meeting_name:
                    if config_manager.add_meeting_name(new_meeting_name):
                        st.session_state.meeting_name = new_meeting_name
                        st.success(f"已添加：{new_meeting_name}")
                        st.rerun()
                    else:
                        st.error("添加失敗或已存在")
        else:
            st.session_state.meeting_name = selected_meeting_name

        # 會議主題/類型
        meeting_topic_options = meeting_topics + ["+ 新增會議主題"]
        selected_meeting_topic = st.selectbox(
            "會議主題/類型",
            meeting_topic_options,
            disabled=st.session_state.is_recording,
            key='meeting_topic_select'
        )

        if selected_meeting_topic == "+ 新增會議主題":
            new_meeting_topic = st.text_input(
                "輸入新的會議主題",
                disabled=st.session_state.is_recording,
                key='new_meeting_topic_input'
            )
            if st.button("➕ 添加會議主題", disabled=st.session_state.is_recording):
                if new_meeting_topic:
                    if config_manager.add_meeting_topic(new_meeting_topic):
                        st.session_state.meeting_topic = new_meeting_topic
                        st.success(f"已添加：{new_meeting_topic}")
                        st.rerun()
                    else:
                        st.error("添加失敗或已存在")
        else:
            st.session_state.meeting_topic = selected_meeting_topic

        st.markdown(
            """
            <div class='sidebar-note'>
                <div class='sidebar-block-title'>Audio Settings</div>
                <div class='sidebar-block-copy'>
                    在這裡設定輸入來源、切片長度與靜音門檻。建議維持 BlackHole 與 5 到 10 秒的 chunk 長度。
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 列出音訊裝置
        devices = AudioRecorder.list_audio_devices()
        device_names = [d['name'] for d in devices]

        # 預設選擇 BlackHole
        preferred_device = config_manager.get_setting('selected_device', "BlackHole 2ch")
        default_device = "BlackHole 2ch"
        default_index = 0
        for i, name in enumerate(device_names):
            if name == preferred_device:
                default_index = i
                default_device = name
                break
        else:
            for i, name in enumerate(device_names):
                if "blackhole" in name.lower():
                    default_index = i
                    default_device = name
                    break

        selected_device = st.selectbox(
            "音訊輸入裝置",
            device_names,
            index=default_index,
            disabled=st.session_state.is_recording,
            key='selected_device'
        )

        # 音訊片段長度
        chunk_duration = st.slider(
            "音訊片段長度（秒）",
            min_value=3,
            max_value=15,
            value=int(config_manager.get_setting('chunk_duration', 10)),
            disabled=st.session_state.is_recording,
            key='chunk_duration'
        )

        # 靜音閾值
        silence_threshold = st.slider(
            "靜音閾值",
            min_value=0.0,
            max_value=0.1,
            value=float(config_manager.get_setting('silence_threshold', 0.01)),
            step=0.001,
            format="%.3f",
            disabled=st.session_state.is_recording,
            help="低於此閾值的音訊片段將被跳過",
            key='silence_threshold'
        )

        # VAD 智能切割
        vad_enabled = st.checkbox(
            "Smart chunking (VAD)",
            value=config_manager.get_setting('vad_enabled', True),
            disabled=st.session_state.is_recording,
            help="偵測語句間的停頓自動切割，避免在句子中間斷開。關閉則使用固定長度切割。",
            key='vad_enabled'
        )

        # 自動儲存音訊設定（僅在非錄音狀態、且值真正改變時寫入）
        if not st.session_state.is_recording:
            _persist_setting_if_changed('selected_device', selected_device)
            _persist_setting_if_changed('chunk_duration', chunk_duration)
            _persist_setting_if_changed('silence_threshold', silence_threshold)
            _persist_setting_if_changed('vad_enabled', vad_enabled)

        st.divider()

        # ================================================================
        # API Provider 選擇與 API Key 管理
        # ================================================================
        st.markdown("<div class='section-label'>API Providers</div>", unsafe_allow_html=True)

        # --- STT Provider ---
        stt_options = list(STT_PROVIDERS.keys())
        current_stt = st.session_state.get('stt_provider', 'openai_whisper')
        stt_index = stt_options.index(current_stt) if current_stt in stt_options else 0
        selected_stt = st.selectbox(
            "Speech-to-Text",
            stt_options,
            index=stt_index,
            format_func=lambda x: STT_PROVIDERS[x]["name"],
            disabled=st.session_state.is_recording,
            help="語音辨識引擎。Groq 速度快 10-50 倍但免費額度有限。",
            key='stt_provider_widget'
        )
        if not st.session_state.is_recording and selected_stt != st.session_state.stt_provider:
            st.session_state.stt_provider = selected_stt
            _persist_setting_if_changed('stt_provider', selected_stt)

        # --- Translation Provider ---
        trans_options = list(TRANSLATION_PROVIDERS.keys())
        current_trans = st.session_state.get('translation_provider', 'openai_gpt')
        trans_index = trans_options.index(current_trans) if current_trans in trans_options else 0
        selected_trans = st.selectbox(
            "Translation",
            trans_options,
            index=trans_index,
            format_func=lambda x: TRANSLATION_PROVIDERS[x]["name"],
            disabled=st.session_state.is_recording,
            help="翻譯引擎。DeepL 日中品質最佳；Gemini Flash 免費額度大。",
            key='translation_provider_widget'
        )
        if not st.session_state.is_recording and selected_trans != st.session_state.translation_provider:
            st.session_state.translation_provider = selected_trans
            _persist_setting_if_changed('translation_provider', selected_trans)

        # --- 動態 API Key 區域 ---
        # 計算需要哪些 key group
        stt_group = PROVIDER_KEY_GROUPS.get(selected_stt, selected_stt)
        trans_group = PROVIDER_KEY_GROUPS.get(selected_trans, selected_trans)
        needed_groups = []
        seen = set()
        for grp in [stt_group, trans_group]:
            if grp not in seen:
                needed_groups.append(grp)
                seen.add(grp)

        st.markdown("<div class='section-label'>API Keys</div>", unsafe_allow_html=True)

        # 針對每個需要的 key group 顯示一個輸入欄位
        for grp in needed_groups:
            # 找到對應的 provider 名稱與 help URL
            # 從 STT 或 Translation providers 中找到第一個屬於此 group 的
            help_url = ""
            group_label = grp.capitalize()
            for pid, pcfg in {**STT_PROVIDERS, **TRANSLATION_PROVIDERS}.items():
                if PROVIDER_KEY_GROUPS.get(pid) == grp:
                    help_url = pcfg.get("key_help", "")
                    # 用 provider 的 group 名稱作為 label
                    group_label = grp.upper()
                    break

            saved_key = config_manager.get_provider_api_key(grp) or ""
            key_input = st.text_input(
                f"{group_label} API Key",
                value=saved_key,
                type="password",
                help=f"取得 Key：{help_url}" if help_url else None,
                disabled=st.session_state.is_recording,
                key=f'api_key_{grp}'
            )

            # 自動儲存（值有變更時）
            if not st.session_state.is_recording and key_input != saved_key:
                if key_input:
                    config_manager.save_provider_api_key(grp, key_input)
                    # 向後相容：如果是 openai group，同步更新 api_key
                    if grp == "openai":
                        st.session_state.api_key = key_input
                else:
                    config_manager.clear_provider_api_key(grp)
                    if grp == "openai":
                        st.session_state.api_key = ""

        st.divider()

        # ================================================================
        # 語言 / 模式選擇
        #
        # 【重要】Streamlit 的 st.rerun(scope="app") 從 fragment 內觸發時，
        # sidebar 的 widget key 可能遺失，selectbox/radio 會退回 index=0。
        #
        # 防護策略（belt-and-suspenders）：
        #   1. 權威值 = st.session_state.language / .target_language / .mode
        #   2. 每次 render 從權威值計算 index= 作為 fallback
        #   3. key= 仍保留（正常情況下 Streamlit 會優先使用 key 值）
        #   4. widget 返回值寫回權威值
        # ================================================================
        language_options = list(LANGUAGE_OPTIONS.keys())

        # --- 音源語言（錄音中鎖定）---
        current_language = st.session_state.get('language', 'ja')
        language_index = language_options.index(current_language) if current_language in language_options else 0
        selected_language = st.selectbox(
            "Audio Language",
            language_options,
            index=language_index,
            format_func=lambda x: LANGUAGE_OPTIONS.get(x, x),
            disabled=st.session_state.is_recording,
            help="🔒 Locked while recording." if st.session_state.is_recording
                 else "Select the language spoken in the meeting.",
            key='language_widget'
        )
        if not st.session_state.is_recording:
            if selected_language != st.session_state.language:
                _persist_setting_if_changed('language', selected_language)
            st.session_state.language = selected_language

        # --- 目標語言（錄音中也可切換）---
        current_target_language = st.session_state.get('target_language', 'zh')
        target_index = language_options.index(current_target_language) if current_target_language in language_options else 0
        selected_target_language = st.selectbox(
            "Native Language",
            language_options,
            index=target_index,
            format_func=lambda x: LANGUAGE_OPTIONS.get(x, x),
            help="✏️ Can be changed during recording." if st.session_state.is_recording
                 else "Choose the language you want as your personal translation output.",
            key='target_language_widget'
        )
        if selected_target_language != st.session_state.target_language:
            # 使用者主動切換 → 更新權威值並儲存
            _persist_setting_if_changed('target_language', selected_target_language)
            st.session_state.target_language = selected_target_language
            if st.session_state.is_recording and st.session_state.transcriber:
                st.session_state.transcriber.set_target_language(selected_target_language)
                add_debug_log(f"🌐 錄音中切換目標語言：{selected_target_language}")

        # --- 處理模式（錄音中也可切換）---
        mode_options = get_mode_options(st.session_state.language, st.session_state.target_language)
        mode_keys = list(mode_options.keys())
        default_mode = get_default_mode(st.session_state.language, st.session_state.target_language)
        current_mode = normalize_mode(st.session_state.get('mode', default_mode))
        if current_mode not in mode_keys:
            st.session_state.mode = default_mode if default_mode in mode_keys else mode_keys[0]
            current_mode = st.session_state.mode
        mode_index = mode_keys.index(current_mode) if current_mode in mode_keys else 0

        st.markdown("<div class='section-label'>Translation Mode</div>", unsafe_allow_html=True)

        mode = st.radio(
            "選擇模式",
            mode_keys,
            index=mode_index,
            format_func=lambda x: mode_options[x],
            key='mode_widget',
            help="✏️ Can be changed during recording." if st.session_state.is_recording else None
        )
        if mode != st.session_state.mode:
            # 使用者主動切換 → 更新權威值並儲存
            _persist_setting_if_changed('mode', mode)
            st.session_state.mode = mode
            if st.session_state.is_recording and st.session_state.transcriber:
                st.session_state.transcriber.set_mode(mode)
                add_debug_log(f"🔄 錄音中切換模式：{mode}")

        st.divider()

        # 顯示選項
        st.markdown("<div class='section-label'>Display Options</div>", unsafe_allow_html=True)

        show_bilingual = st.checkbox(
            "Show multilingual comparison",
            value=st.session_state.show_bilingual,
            help="Display source text and translated text side by side. Can be toggled during recording.",
            key='show_bilingual'
        )
        _persist_setting_if_changed('show_bilingual', show_bilingual)

        st.divider()

        # 錄音狀態資訊
        if st.session_state.is_recording and st.session_state.recorder:
            st.markdown("<div class='section-label'>Recording Status</div>", unsafe_allow_html=True)
            stats = st.session_state.recorder.get_recording_stats()

            st.metric("Duration", f"{stats['duration']:.1f}s")
            st.metric("File Size", f"{stats['file_size'] / 1024 / 1024:.2f} MB")
            st.metric("Captured Chunks", stats.get('chunks_captured', stats['chunks_processed']))
            st.metric("Sent to API", stats['chunks_processed'])
            st.metric("Silent Chunks", stats.get('chunks_skipped_silence', 0))
            st.metric("Last RMS", f"{stats.get('last_rms', 0.0):.6f}")

            if stats.get('chunks_captured', 0) > 0 and stats['chunks_processed'] == 0:
                st.warning(
                    "Audio is being captured, but every chunk is silent. "
                    "This usually means BlackHole is selected but your macOS or meeting app output is not routed into it."
                )

            if st.session_state.transcriber:
                api_stats = st.session_state.transcriber.get_stats()
                st.metric("API Calls", api_stats['total_calls'])
                if api_stats.get('translation_calls', 0) > 0:
                    st.metric("Translations", api_stats['translation_calls'])
                st.metric("Whisper Cost", f"${api_stats['estimated_cost']:.4f}")

                if st.session_state.worker:
                    queue_size = st.session_state.worker.get_queue_size()
                    worker_status = "Running" if st.session_state.worker.is_running else "Stopped"
                    st.metric("Queue", f"{queue_size} chunks")
                    st.metric("Worker", worker_status)

                    # Circuit breaker 狀態
                    cb_status = st.session_state.worker.get_circuit_breaker_status()
                    if cb_status['is_open']:
                        st.error(
                            f"⚡ Circuit Breaker OPEN — API 連續失敗 {cb_status['consecutive_failures']} 次，"
                            f"剩餘冷卻 {cb_status['remaining_seconds']}s",
                            icon="🔴"
                        )
                    elif cb_status['consecutive_failures'] > 0:
                        remaining_until_trip = TranscriberWorker.CB_FAILURE_THRESHOLD - cb_status['consecutive_failures']
                        st.warning(
                            f"API 連續失敗 {cb_status['consecutive_failures']} 次"
                            f"（再 {remaining_until_trip} 次觸發熔斷）"
                        )

            st.divider()

        # 錯誤訊息（從 controller 獲取）
        error_messages = st.session_state.error_messages.copy()
        if st.session_state.controller:
            error_messages.extend(st.session_state.controller.error_messages)

        if error_messages:
            st.markdown("<div class='section-label'>Errors</div>", unsafe_allow_html=True)
            error_container = st.container()
            with error_container:
                for error in error_messages[-5:]:  # 只顯示最近 5 條
                    st.error(error, icon="⚠")

        # 調試日誌（可展開）
        if st.session_state.debug_logs:
            with st.expander("Debug Logs", expanded=False):
                for log in st.session_state.debug_logs[-20:]:  # 只顯示最近 20 條
                    st.text(log)

        # 術語詞典管理（可展開）
        with st.expander("Terminology Dictionary", expanded=False):
            st.markdown("**Manage specialized terms and translations**")
            st.info("Recommended: Use key terms in the source language or English. Terms are applied to all translation modes.")

            # 顯示現有術語
            terminology = config_manager.get_terminology()
            if terminology:
                st.markdown("**已儲存的術語：**")
                for source, target in terminology.items():
                    col_term1, col_term2 = st.columns([3, 1])
                    with col_term1:
                        st.text(f"{source} → {target}")
                    with col_term2:
                        if st.button("🗑️", key=f"del_{source}", help=f"刪除 {source}"):
                            if config_manager.delete_term(source):
                                st.success(f"已刪除：{source}")
                                st.rerun()
                st.divider()

            # 添加新術語
            st.markdown("**添加新術語：**")
            col_new1, col_new2 = st.columns(2)
            with col_new1:
                new_source = st.text_input("原文（來源語言或英文）", key="new_term_source", placeholder="例如：wafer")
            with col_new2:
                new_target = st.text_input("Translation", key="new_term_target", placeholder="例如：晶圓")

            if st.button("➕ 添加術語"):
                if new_source and new_target:
                    if config_manager.add_term(new_source, new_target):
                        st.success(f"已添加：{new_source} → {new_target}")
                        st.rerun()
                    else:
                        st.error("添加失敗")
                else:
                    st.warning("請填寫原文和對應翻譯")

        # Live Viewer 設定（跨機器觀看主電腦的錄音）
        with st.expander("📡 Live Viewer 設定", expanded=False):
            st.markdown("**連線到主電腦觀看即時翻譯**")
            st.caption("輸入主電腦的 IP 位址後，本機即可觀看主電腦的 Reading Flow。留空表示只檢查本機。")
            viewer_host_input = st.text_input(
                "主電腦 IP",
                value=st.session_state.get('viewer_host', ''),
                placeholder="例如：192.168.31.64",
                key='viewer_host_input',
                disabled=st.session_state.is_recording
            )
            if viewer_host_input != st.session_state.get('viewer_host', ''):
                st.session_state.viewer_host = viewer_host_input.strip()
                config_manager.save_setting('viewer_host', viewer_host_input.strip())
            if st.session_state.get('viewer_host'):
                # 連線測試
                test_url = f"http://{st.session_state.viewer_host}:{TRANSCRIPT_SHARE_PORT}/"
                try:
                    with urllib.request.urlopen(test_url, timeout=2):
                        st.success(f"✅ 已連線到 {st.session_state.viewer_host}:{TRANSCRIPT_SHARE_PORT}")
                except (urllib.error.URLError, OSError):
                    st.warning(f"⚠️ 無法連線到 {st.session_state.viewer_host}:{TRANSCRIPT_SHARE_PORT}")

        if st.session_state.live_transcript_path and Path(st.session_state.live_transcript_path).exists():
            st.divider()
            st.markdown("<div class='section-label'>Live File</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='sidebar-file-note'>{html_module.escape(st.session_state.live_transcript_path)}</div>",
                unsafe_allow_html=True
            )

    # ========================================================================
    # Live Viewer 入口（獨立 fragment，每 5 秒自動偵測其他裝置的錄音）
    # ========================================================================
    _viewer_poll = timedelta(seconds=5) if not st.session_state.is_recording else None

    @st.fragment(run_every=_viewer_poll)
    def _check_remote_session():
        """自動偵測是否有其他裝置正在錄音（本機 + 遠端），顯示 Live Viewer 入口"""
        if st.session_state.is_recording:
            return
        # 優先查遠端（有設定主電腦 IP 時），其次查本機
        viewer_host = st.session_state.get('viewer_host', '')
        if viewer_host:
            marker = _read_remote_marker(viewer_host)
        else:
            marker = _read_active_session_marker()
        if marker:
            viewer_name = marker.get('meeting_name', '錄音')
            viewer_topic = marker.get('meeting_topic', '')
            started = marker.get('started_at', '')
            info_text = f"📡 **另一台裝置正在錄音中** — {viewer_name}"
            if viewer_topic:
                info_text += f" · {viewer_topic}"
            if started:
                try:
                    start_dt = datetime.fromisoformat(started)
                    elapsed = datetime.now() - start_dt
                    mins = int(elapsed.total_seconds() // 60)
                    info_text += f" · 已進行 {mins} 分鐘"
                except ValueError:
                    pass
            st.info(info_text, icon="📡")
            if st.button("📡 進入 Live Viewer 觀看即時翻譯",
                         use_container_width=True, type="secondary"):
                st.session_state.viewer_mode = True
                st.rerun(scope="app")

    _check_remote_session()

    # ========================================================================
    # ========================================================================
    # 主畫面（使用 st.fragment 減少錄音中的全頁閃爍）
    # ========================================================================
    _refresh_interval = timedelta(seconds=2) if st.session_state.is_recording else None

    @st.fragment(run_every=_refresh_interval)
    def _render_live_content():
        # 重新讀取最新資料（fragment 自動刷新時需要最新數據）
        transcripts = []
        if st.session_state.controller:
            transcripts = st.session_state.controller.transcripts

        recording_stats = st.session_state.recorder.get_recording_stats() if st.session_state.recorder else {}
        api_stats = st.session_state.transcriber.get_stats() if st.session_state.transcriber else {}
        status_metadata = get_status_metadata()
        status_badge_html = (
            f"<div class='status-badge {status_metadata['css_class']}'>"
            f"{status_metadata['icon_html']}"
            f"<span>{html_module.escape(status_metadata['label'])}</span>"
            "</div>"
        )

        current_mode = normalize_mode(st.session_state.get('mode', 'translate_target'))
        current_language = st.session_state.get('language', 'ja')
        current_target_language = st.session_state.get('target_language', 'zh')
        current_language_label = get_language_label(current_language)
        current_target_language_label = get_language_label(current_target_language)
        current_mode_options = get_mode_options(current_language, current_target_language)
        current_mode_label = current_mode_options.get(current_mode, current_mode)
        flow_language_options = get_flow_language_options(current_mode, current_language, current_target_language)
        default_flow_language = get_default_flow_language(current_mode, current_language, current_target_language)
        if st.session_state.reading_flow_language not in flow_language_options:
            st.session_state.reading_flow_language = default_flow_language
        selected_flow_language = st.session_state.reading_flow_language
        selected_flow_label = get_language_label(selected_flow_language)
        feed_items = get_feed_items(transcripts, selected_flow_language)
        visible_feed_items, hidden_feed_items = limit_visible_items(feed_items, MAX_VISIBLE_FEED_ITEMS)
        selected_device_label = st.session_state.get('selected_device', 'BlackHole 2ch')
        meeting_name_display = st.session_state.meeting_name or "Untitled meeting"
        meeting_topic_display = st.session_state.meeting_topic or "Topic not set"
        transcript_count = len(transcripts)
        reading_line_count = len(feed_items)
        latest_latency = f"{transcripts[-1]['latency']:.1f}s" if transcripts else "Waiting"
        duration_value = f"{recording_stats.get('duration', 0.0):.1f}s"
        cost_value = f"${api_stats.get('estimated_cost', 0.0):.4f}"
        queue_value = (
            f"{st.session_state.worker.get_queue_size()} queued"
            if st.session_state.worker
            else "Idle"
        )
        worker_value = (
            "Running"
            if st.session_state.worker and st.session_state.worker.is_running
            else "Standby"
        )

        flow_selector_col, flow_selector_spacer = st.columns([2.3, 3.7])
        with flow_selector_col:
            st.markdown("<div class='section-label'>Reading Flow Language</div>", unsafe_allow_html=True)
            flow_index = flow_language_options.index(selected_flow_language) if selected_flow_language in flow_language_options else 0
            selected_flow_language = st.selectbox(
                "Reading Flow Language",
                flow_language_options,
                index=flow_index,
                format_func=get_language_label,
                key='reading_flow_language_widget',
                label_visibility="collapsed"
            )
            st.session_state.reading_flow_language = selected_flow_language
            selected_flow_label = get_language_label(selected_flow_language)
            feed_items = get_feed_items(transcripts, selected_flow_language)
            visible_feed_items, hidden_feed_items = limit_visible_items(feed_items, MAX_VISIBLE_FEED_ITEMS)
            reading_line_count = len(feed_items)

        hero_col1, hero_col2 = st.columns([5, 1])

        with hero_col1:
            render_live_feed_panel(
                visible_feed_items,
                selected_flow_language,
                status_metadata,
                meeting_name_display,
                meeting_topic_display,
                st.session_state.is_recording
            )
            if hidden_feed_items > 0:
                st.caption(
                    f"Reading Flow 僅顯示最近 {len(visible_feed_items)} 段內容，以保持長時間錄音穩定。更早內容仍保留在逐字稿資料與匯出檔案中。"
                )

        with hero_col2:
            st.markdown(
                f"""
                <div class='status-panel'>
                    <div class='status-panel-title'>Session status</div>
                    {status_badge_html}
                    <div class='status-panel-value'>{html_module.escape(status_metadata['label'])}</div>
                    <div class='status-panel-copy'>{html_module.escape(status_metadata['description'])}</div>
                    <div class='status-grid'>
                        <div class='status-mini'>
                            <div class='status-mini-label'>Latency</div>
                            <div class='status-mini-value'>{html_module.escape(latest_latency)}</div>
                        </div>
                        <div class='status-mini'>
                            <div class='status-mini-label'>Reading Lines</div>
                            <div class='status-mini-value'>{html_module.escape(str(reading_line_count))}</div>
                        </div>
                        <div class='status-mini'>
                            <div class='status-mini-label'>Worker</div>
                            <div class='status-mini-value'>{html_module.escape(worker_value)}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div class='control-caption'>Quick Controls</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='control-note'>開始與停止按鍵已加重。開始時立刻建立新 session，停止時立即結束本輪錄音與翻譯。</div>",
            unsafe_allow_html=True
        )

        col1, col2, col3, col_spacer = st.columns([2.1, 1.15, 2.1, 2.65])

        with col1:
            if st.button(
                "▶ Start Recording Now" if not st.session_state.is_recording else "● Recording In Progress",
                disabled=st.session_state.is_recording,
                use_container_width=True,
                type="primary"
            ):
                start_recording()
                _force_sync_widget_keys()
                st.rerun(scope="app")

        with col2:
            if st.session_state.is_recording and not st.session_state.is_paused:
                if st.button("⏸ Pause", use_container_width=True):
                    pause_recording()
                    _force_sync_widget_keys()
                    st.rerun(scope="app")
            elif st.session_state.is_recording and st.session_state.is_paused:
                if st.button("▶ Resume", use_container_width=True):
                    resume_recording()
                    _force_sync_widget_keys()
                    st.rerun(scope="app")

        with col3:
            if st.button(
                "■ Stop Session",
                disabled=not st.session_state.is_recording,
                use_container_width=True,
                type="primary" if st.session_state.is_recording else "secondary"
            ):
                stop_recording()
                _force_sync_widget_keys()
                st.rerun(scope="app")

        st.markdown("<div class='control-caption'>Session Snapshot</div>", unsafe_allow_html=True)
        metric_cols = st.columns(4)
        with metric_cols[0]:
            render_metric_card("Mode", current_mode_label, get_mode_summary(current_mode, current_language, current_target_language), "accent-primary")
        with metric_cols[1]:
            render_metric_card(
                "Audio Input",
                selected_device_label,
                f"Monitoring {current_language_label} speech, native output {current_target_language_label}, queue {queue_value}",
                "accent-secondary"
            )
        with metric_cols[2]:
            render_metric_card("Transcript Lines", str(transcript_count), f"{selected_flow_label} reading flow has {reading_line_count} lines", "accent-warm")
        with metric_cols[3]:
            render_metric_card(
                "Whisper Cost",
                cost_value,
                f"{api_stats.get('total_calls', 0)} Whisper calls over {duration_value} · GPT {api_stats.get('translation_calls', 0)}x",
                "accent-neutral"
            )

        live_chip = "<div class='section-chip'>Newest detailed card stays at the top</div>"
        st.markdown(
            f"""
            <div class='section-head'>
                <div>
                    <div class='section-title'>Transcription Results</div>
                    <div class='section-copy'>
                        Detailed multilingual cards remain below. The reading panel above keeps the {html_module.escape(selected_flow_label)} flow in speaking order from top to bottom.
                    </div>
                </div>
                {live_chip}
            </div>
            """,
            unsafe_allow_html=True
        )

        if transcripts:
            visible_transcripts, hidden_transcripts = limit_visible_items(transcripts, MAX_VISIBLE_TRANSCRIPT_CARDS)
            if hidden_transcripts > 0:
                st.caption(
                    f"詳細卡片目前顯示最近 {len(visible_transcripts)} 筆結果。更早內容仍會保留在 session 與匯出檔案中。"
                )
            for item in visible_transcripts[::-1]:
                render_transcript_card(item, st.session_state.show_bilingual)
        else:
            st.markdown(
                """
                <div class='empty-state'>
                    <div class='empty-icon'>🎙</div>
                    <div class='empty-title'>No transcription yet</div>
                    <div class='empty-copy'>
                        Start recording when the meeting begins. Source text and any enabled translations will appear here with timestamps and latency.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


    _render_live_content()

    # 停止後顯示下載按鈕（重新讀取 transcripts，因為 fragment 內的變數不外流）
    transcripts = st.session_state.controller.transcripts if st.session_state.controller else []
    if not st.session_state.is_recording and transcripts:
        st.divider()
        st.markdown(
            """
            <div class='section-head'>
                <div>
                    <div class='section-title'>Exports</div>
                    <div class='section-copy'>
                        Save the cleaned transcript or download the recorded meeting audio after the session ends.
                    </div>
                </div>
                <div class='section-chip'>Ready to download</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 顯示即時逐字稿檔案位置
        if st.session_state.live_transcript_path and Path(st.session_state.live_transcript_path).exists():
            st.info(f"Live transcript saved automatically: `{st.session_state.live_transcript_path}`")

        col1, col2 = st.columns(2)

        with col1:
            # 下載逐字稿（支援語言選擇）
            st.markdown("<div class='section-label'>Download Transcript</div>", unsafe_allow_html=True)

            available_export_languages = []
            for item in transcripts:
                for language_code in get_transcript_language_order(item):
                    if language_code not in available_export_languages:
                        available_export_languages.append(language_code)

            language_summary = " + ".join(code.upper() for code in available_export_languages)
            language_options = {
                "all": f"All Available ({language_summary})"
            }
            for language_code in available_export_languages:
                language_options[language_code] = f"{get_language_label(language_code)} Only"

            selected_language = st.selectbox(
                "Select Language",
                list(language_options.keys()),
                format_func=lambda x: language_options[x],
                key='download_language_selection'
            )

            export_format = st.selectbox(
                "Format",
                ["TXT", "SRT", "VTT"],
                key='export_format_selection'
            )

            if st.button("Generate File", use_container_width=True, type="primary"):
                meeting_name_val = st.session_state.meeting_name
                meeting_topic_val = st.session_state.meeting_topic

                if export_format == "SRT":
                    file_path = save_transcript_to_srt(
                        transcripts,
                        language_selection=selected_language,
                        meeting_name=meeting_name_val,
                        meeting_topic=meeting_topic_val
                    )
                    mime_type = "application/x-subrip"
                elif export_format == "VTT":
                    file_path = save_transcript_to_vtt(
                        transcripts,
                        language_selection=selected_language,
                        meeting_name=meeting_name_val,
                        meeting_topic=meeting_topic_val
                    )
                    mime_type = "text/vtt"
                else:
                    file_path = save_transcript_to_file(
                        transcripts,
                        meeting_name=meeting_name_val,
                        meeting_topic=meeting_topic_val,
                        language_selection=selected_language
                    )
                    mime_type = "text/plain"

                with open(file_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                st.download_button(
                    label=f"Download {export_format}",
                    data=transcript_content,
                    file_name=Path(file_path).name,
                    mime=mime_type,
                    use_container_width=True
                )
                st.success(f"File generated: {Path(file_path).name}")

        with col2:
            # 下載錄音
            st.markdown("<div class='section-label'>Download Audio</div>", unsafe_allow_html=True)
            if st.session_state.recorder:
                stats = st.session_state.recorder.get_recording_stats()
                recording_file = stats.get('file_path')
                if recording_file and Path(recording_file).exists():
                    file_size_mb = Path(recording_file).stat().st_size / 1024 / 1024
                    st.caption(f"File size: {file_size_mb:.2f} MB")
                    # 讀取 WAV 檔案內容（with 確保 handle 釋放）
                    with open(recording_file, 'rb') as wav_f:
                        wav_data = wav_f.read()
                    st.download_button(
                        label="Download WAV",
                        data=wav_data,
                        file_name=Path(recording_file).name,
                        mime="audio/wav",
                        use_container_width=True
                    )
                else:
                    st.info("No audio file available")
            else:
                st.info("No audio file available")

    # ========================================================================
    # 歷史記錄
    # ========================================================================
    if not st.session_state.is_recording:
        transcripts_dir = Path("transcripts")
        if transcripts_dir.exists():
            history_files = sorted(transcripts_dir.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
            # 排除目前 session 的 live transcript
            live_path = st.session_state.get('live_transcript_path')
            if live_path:
                history_files = [f for f in history_files if str(f) != live_path]

            if history_files:
                st.divider()
                st.markdown(
                    """
                    <div class='section-head'>
                        <div>
                            <div class='section-title'>Session History</div>
                            <div class='section-copy'>
                                Past transcript files saved in the transcripts/ folder. Click to preview.
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # 顯示最近 20 個檔案
                for hist_file in history_files[:20]:
                    file_size_kb = hist_file.stat().st_size / 1024
                    mod_time = datetime.fromtimestamp(hist_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    label = f"📄 {hist_file.name}  ({file_size_kb:.1f} KB · {mod_time})"

                    with st.expander(label, expanded=False):
                        preview = None
                        try:
                            preview = hist_file.read_text(encoding='utf-8')
                            # 只顯示前 3000 字元作為預覽
                            if len(preview) > 3000:
                                st.text(preview[:3000] + "\n\n... (truncated)")
                            else:
                                st.text(preview)
                        except Exception as e:
                            st.error(f"Cannot read file: {e}")

                        if preview is not None:
                            st.download_button(
                                label="Download",
                                data=preview,
                                file_name=hist_file.name,
                                mime="text/plain",
                                key=f"hist_dl_{hist_file.name}"
                            )

    # 鍵盤快捷鍵
    render_keyboard_shortcuts()

    # 自動重新整理由 st.fragment(run_every=2s) 處理，不再需要全頁 sleep+rerun


if __name__ == "__main__":
    main()
