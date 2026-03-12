#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
即時會議翻譯 App - Streamlit 主程式
"""

import streamlit as st
import time
from datetime import datetime
from pathlib import Path
import threading
import html as html_module

from config_manager import config_manager
from audio_recorder import AudioRecorder
from transcriber import Transcriber, TranscriberWorker


# 設定頁面配置
st.set_page_config(
    page_title="Meeting Translator — Real-time AI Translation",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 企業級 CSS 設計系統
st.markdown("""
<style>
    /* ============================================
       全域設定 - macOS 質感基礎
       ============================================ */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        /* 配色系統 - macOS Big Sur 風格 */
        --color-bg-primary: #ffffff;
        --color-bg-secondary: #f5f5f7;
        --color-bg-tertiary: #e8e8ed;
        --color-surface: #ffffff;
        --color-surface-raised: #ffffff;

        /* 文字色彩 */
        --color-text-primary: #1d1d1f;
        --color-text-secondary: #6e6e73;
        --color-text-tertiary: #86868b;

        /* 品牌色彩 - 專業且克制 */
        --color-accent-blue: #007aff;
        --color-accent-green: #34c759;
        --color-accent-orange: #ff9500;
        --color-accent-red: #ff3b30;

        /* 語言色彩 - 柔和且易辨識 */
        --color-lang-ja: #e8f4fd;
        --color-lang-ja-border: #b3d9f2;
        --color-lang-en: #e8f8f0;
        --color-lang-en-border: #b3e6d4;
        --color-lang-zh: #fff4e8;
        --color-lang-zh-border: #ffd9a3;

        /* 陰影 - 微妙且有層次 */
        --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.04);
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.08);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.12);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.16);

        /* 圓角 */
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;

        /* 間距 */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;
        --space-2xl: 48px;
    }

    /* ============================================
       Streamlit 元素覆寫
       ============================================ */

    /* 主容器 */
    .main {
        background-color: var(--color-bg-secondary);
        padding: var(--space-xl) var(--space-2xl);
    }

    /* 隱藏 Streamlit 品牌元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 側邊欄樣式 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f9f9fb 100%);
        border-right: 1px solid rgba(0, 0, 0, 0.06);
        padding: var(--space-lg) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: var(--space-xl);
    }

    /* 標題樣式 */
    h1 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 700;
        font-size: 2rem;
        letter-spacing: -0.02em;
        color: var(--color-text-primary);
        margin-bottom: var(--space-lg);
        line-height: 1.2;
    }

    h2 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 600;
        font-size: 1.25rem;
        letter-spacing: -0.01em;
        color: var(--color-text-primary);
        margin-top: var(--space-xl);
        margin-bottom: var(--space-md);
    }

    h3 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 600;
        font-size: 1rem;
        letter-spacing: -0.005em;
        color: var(--color-text-secondary);
        margin-top: var(--space-lg);
        margin-bottom: var(--space-sm);
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }

    /* 段落和文字 */
    p, .stMarkdown {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 400;
        font-size: 0.9375rem;
        line-height: 1.6;
        color: var(--color-text-secondary);
    }

    /* ============================================
       按鈕系統
       ============================================ */

    .stButton > button {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 500;
        font-size: 0.9375rem;
        border-radius: var(--radius-md);
        padding: 0.625rem 1.25rem;
        border: none;
        background: var(--color-accent-blue);
        color: white;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        letter-spacing: -0.01em;
    }

    .stButton > button:hover {
        background: #0051d5;
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0);
        box-shadow: var(--shadow-sm);
    }

    /* ============================================
       輸入元素
       ============================================ */

    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 0.9375rem;
        border: 1px solid var(--color-bg-tertiary);
        border-radius: var(--radius-sm);
        background: var(--color-surface);
        padding: 0.625rem 0.875rem;
        transition: all 0.2s ease;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--color-accent-blue);
        box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        outline: none;
    }

    /* Slider 樣式 */
    .stSlider > div > div > div > div {
        background-color: var(--color-accent-blue);
    }

    /* Radio 樣式 */
    .stRadio > div {
        gap: var(--space-sm);
    }

    .stRadio > div > label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 0.9375rem;
        background: var(--color-surface);
        padding: var(--space-sm) var(--space-md);
        border-radius: var(--radius-sm);
        border: 1px solid var(--color-bg-tertiary);
        transition: all 0.2s ease;
    }

    .stRadio > div > label:hover {
        border-color: var(--color-accent-blue);
        background: var(--color-bg-secondary);
    }

    /* ============================================
       卡片系統 - 翻譯結果顯示
       ============================================ */

    .transcript-card {
        background: var(--color-surface-raised);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        margin-bottom: var(--space-md);
        box-shadow: var(--shadow-sm);
        border: 1px solid rgba(0, 0, 0, 0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .transcript-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    /* 時間戳記 */
    .timestamp {
        font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--color-text-tertiary);
        letter-spacing: 0.02em;
        margin-bottom: var(--space-sm);
        display: inline-block;
    }

    /* 延遲時間 */
    .latency {
        font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
        font-size: 0.6875rem;
        color: var(--color-text-tertiary);
        margin-left: var(--space-sm);
        opacity: 0.7;
    }

    /* 語言標籤 */
    .language-label {
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: var(--space-xs);
        display: flex;
        align-items: center;
        gap: var(--space-xs);
    }

    /* 日語文字塊 */
    .japanese-text {
        background: linear-gradient(135deg, var(--color-lang-ja) 0%, #f0f8ff 100%);
        border-left: 3px solid var(--color-lang-ja-border);
        padding: var(--space-md);
        border-radius: var(--radius-sm);
        margin: var(--space-sm) 0;
        font-size: 0.9375rem;
        line-height: 1.7;
        color: var(--color-text-primary);
    }

    /* 英語文字塊 */
    .english-text {
        background: linear-gradient(135deg, var(--color-lang-en) 0%, #f0fff8 100%);
        border-left: 3px solid var(--color-lang-en-border);
        padding: var(--space-md);
        border-radius: var(--radius-sm);
        margin: var(--space-sm) 0;
        font-size: 0.9375rem;
        line-height: 1.7;
        color: var(--color-text-primary);
    }

    /* 中文文字塊 */
    .chinese-text {
        background: linear-gradient(135deg, var(--color-lang-zh) 0%, #fffaf0 100%);
        border-left: 3px solid var(--color-lang-zh-border);
        padding: var(--space-md);
        border-radius: var(--radius-sm);
        margin: var(--space-sm) 0;
        font-size: 0.9375rem;
        line-height: 1.7;
        color: var(--color-text-primary);
    }

    /* ============================================
       狀態指示器
       ============================================ */

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: var(--space-xs);
        padding: var(--space-xs) var(--space-md);
        border-radius: var(--radius-xl);
        font-size: 0.8125rem;
        font-weight: 500;
        letter-spacing: -0.01em;
    }

    .status-recording {
        background: rgba(255, 59, 48, 0.1);
        color: var(--color-accent-red);
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }

    .status-paused {
        background: rgba(255, 149, 0, 0.1);
        color: var(--color-accent-orange);
    }

    .status-stopped {
        background: rgba(142, 142, 147, 0.1);
        color: var(--color-text-tertiary);
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* 錄音指示燈 */
    .recording-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--color-accent-red);
        animation: blink 1.5s ease-in-out infinite;
        display: inline-block;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px var(--color-accent-red); }
        50% { opacity: 0.3; box-shadow: none; }
    }

    /* ============================================
       資訊卡片
       ============================================ */

    .stAlert {
        background: var(--color-surface);
        border-radius: var(--radius-md);
        border: 1px solid var(--color-bg-tertiary);
        padding: var(--space-md);
        font-size: 0.875rem;
    }

    /* Metric 卡片 */
    [data-testid="stMetricValue"] {
        font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--color-text-primary);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.8125rem;
        color: var(--color-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }

    /* ============================================
       分隔線
       ============================================ */

    hr {
        margin: var(--space-xl) 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg,
            transparent 0%,
            var(--color-bg-tertiary) 50%,
            transparent 100%);
    }

    /* ============================================
       容器和佈局
       ============================================ */

    .block-container {
        padding-top: var(--space-xl);
        padding-bottom: var(--space-2xl);
        max-width: 1400px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 500;
        font-size: 0.9375rem;
        background: var(--color-surface);
        border-radius: var(--radius-sm);
        border: 1px solid var(--color-bg-tertiary);
        padding: var(--space-md);
    }

    /* ============================================
       滾動條
       ============================================ */

    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: var(--color-bg-tertiary);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--color-text-tertiary);
    }

    /* ============================================
       響應式設計
       ============================================ */

    @media (max-width: 768px) {
        .main {
            padding: var(--space-md);
        }

        h1 {
            font-size: 1.5rem;
        }

        .transcript-card {
            padding: var(--space-md);
        }
    }
</style>
""", unsafe_allow_html=True)


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
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    if 'error_messages' not in st.session_state:
        st.session_state.error_messages = []
    if 'show_bilingual' not in st.session_state:
        st.session_state.show_bilingual = True  # 預設顯示雙語
    if 'meeting_name' not in st.session_state:
        st.session_state.meeting_name = ""
    if 'meeting_topic' not in st.session_state:
        st.session_state.meeting_topic = ""
    if 'live_transcript_path' not in st.session_state:
        st.session_state.live_transcript_path = None


def add_debug_log(message: str):
    """添加調試日誌"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.debug_logs.append(log_entry)
    # 只保留最近 50 條日誌
    if len(st.session_state.debug_logs) > 50:
        st.session_state.debug_logs = st.session_state.debug_logs[-50:]
    print(log_entry)  # 同時輸出到 Terminal


def add_error_message(message: str):
    """添加錯誤訊息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    error_entry = f"[{timestamp}] ❌ {message}"
    st.session_state.error_messages.append(error_entry)
    if len(st.session_state.error_messages) > 10:
        st.session_state.error_messages = st.session_state.error_messages[-10:]
    print(f"ERROR: {error_entry}")  # 輸出到 Terminal


def create_live_transcript_file(meeting_name: str = "", meeting_topic: str = "") -> str:
    """
    創建即時逐字稿檔案（錄音開始時調用）

    Args:
        meeting_name: 會議名稱
        meeting_topic: 會議主題

    Returns:
        檔案路徑
    """
    transcripts_dir = Path("transcripts")
    transcripts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 構建檔案名稱
    filename_parts = ["live_transcript"]
    if meeting_name:
        safe_meeting_name = meeting_name.replace("/", "-").replace("\\", "-").replace(":", "-")
        filename_parts.append(safe_meeting_name)
    if meeting_topic:
        safe_meeting_topic = meeting_topic.replace("/", "-").replace("\\", "-").replace(":", "-")
        filename_parts.append(safe_meeting_topic)
    filename_parts.append(timestamp)

    filename = "_".join(filename_parts) + ".txt"
    file_path = transcripts_dir / filename

    # 寫入標題
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("即時會議逐字稿\n")
        if meeting_name:
            f.write(f"會議名稱：{meeting_name}\n")
        if meeting_topic:
            f.write(f"會議主題：{meeting_topic}\n")
        f.write(f"開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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

        texts = item.get('texts', {})

        # 總是寫入全部語言（即時記錄）
        if texts.get('ja'):
            f.write(f"📝 日語：{texts['ja']}\n")
        if texts.get('en'):
            f.write(f"🌐 英文：{texts['en']}\n")
        if texts.get('zh'):
            f.write(f"🈯 中文：{texts['zh']}\n")
        # 如果沒有 texts，使用 text
        if not texts:
            f.write(f"{item['text']}\n")

        f.write("-" * 60 + "\n\n")


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
        safe_meeting_name = meeting_name.replace("/", "-").replace("\\", "-").replace(":", "-")
        filename_parts.append(safe_meeting_name)
    if meeting_topic:
        safe_meeting_topic = meeting_topic.replace("/", "-").replace("\\", "-").replace(":", "-")
        filename_parts.append(safe_meeting_topic)
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

            texts = item.get('texts', {})

            if language_selection == "all":
                # 全部語言
                if texts.get('ja'):
                    f.write(f"📝 日語：{texts['ja']}\n")
                if texts.get('en'):
                    f.write(f"🌐 英文：{texts['en']}\n")
                if texts.get('zh'):
                    f.write(f"🈯 中文：{texts['zh']}\n")
                # 如果沒有 texts，使用 text
                if not texts:
                    f.write(f"{item['text']}\n")
            elif language_selection == "ja":
                # 只有日文
                text_to_write = texts.get('ja') or (item['text'] if item.get('mode') == 'transcribe' else '')
                if text_to_write:
                    f.write(f"{text_to_write}\n")
            elif language_selection == "en":
                # 只有英文
                text_to_write = texts.get('en') or (item['text'] if item.get('mode') == 'translate' else '')
                if text_to_write:
                    f.write(f"{text_to_write}\n")
            elif language_selection == "zh":
                # 只有中文
                text_to_write = texts.get('zh') or (item['text'] if item.get('mode') == 'translate_zh' else '')
                if text_to_write:
                    f.write(f"{text_to_write}\n")

            f.write("-" * 60 + "\n\n")

    return str(file_path)


class ProcessingController:
    """處理控制器（避免在子執行緒中訪問 st.session_state）"""

    def __init__(self, recorder, worker):
        self.recorder = recorder
        self.worker = worker
        self.stop_flag = False
        self.is_paused = False
        self.transcripts = []
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
        print("✅ ProcessingController 執行緒已啟動")

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
        print("=" * 60)
        print("🔄 處理迴圈已啟動")
        print(f"   Recorder: {self.recorder}")
        print(f"   Worker: {self.worker}")
        print(f"   Worker is_running: {self.worker.is_running}")
        print("=" * 60)

        while not self.stop_flag:
            try:
                if not self.is_paused:
                    # 從錄音器取得音訊片段
                    chunk = self.recorder.get_next_chunk(timeout=0.5)
                    if chunk:
                        print(f"🎵 收到音訊片段（{chunk['duration']}秒）")
                        # 提交給 Transcriber Worker
                        self.worker.add_audio_chunk(chunk)
                        print(f"📤 音訊片段已提交給 API 處理佇列（佇列大小：{self.worker.get_queue_size()}）")

                    # 從 Worker 取得處理結果
                    result = self.worker.get_result(timeout=0.1)
                    if result:
                        if result.get('success', True):
                            # 添加到逐字稿列表
                            self.transcripts.append(result)
                            print(f"✅ 辨識完成：{result['text'][:50]}...")

                            # 即時追加到檔案
                            if self.live_transcript_path:
                                append_to_live_transcript(self.live_transcript_path, result)
                                print(f"📝 已追加到即時逐字稿：{self.live_transcript_path}")
                        else:
                            # 處理失敗
                            error_msg = result.get('error', '未知錯誤')
                            print(f"❌ API 呼叫失敗：{error_msg}")
                            self.error_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] API 失敗：{error_msg}")
                else:
                    time.sleep(0.1)

            except Exception as e:
                error_msg = f"處理迴圈錯誤：{str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                time.sleep(1)

        print("⏹️ 處理迴圈已停止")


def start_recording():
    """開始錄音"""
    if not st.session_state.api_key:
        st.error("請先輸入 OpenAI API Key")
        add_error_message("缺少 API Key")
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
            st.warning(f"找不到裝置 '{device_name}'，使用預設裝置")
            add_error_message(f"找不到裝置 '{device_name}'，使用預設裝置")
            st.session_state.recorder.set_device(device_index=None)

        st.session_state.recorder.set_chunk_duration(st.session_state.chunk_duration)
        st.session_state.recorder.set_silence_threshold(st.session_state.silence_threshold)
        add_debug_log(f"⚙️ 音訊片段長度：{st.session_state.chunk_duration}秒，靜音閾值：{st.session_state.silence_threshold}")

        # 初始化 Transcriber（每次都重新初始化以確保使用最新的 API Key）
        add_debug_log("🤖 正在初始化 Whisper API...")
        st.session_state.transcriber = Transcriber(st.session_state.api_key)
        add_debug_log(f"✅ Whisper API 已初始化（API Key: {st.session_state.api_key[:10]}...）")

        st.session_state.transcriber.set_mode(st.session_state.mode)
        st.session_state.transcriber.set_language(st.session_state.language)
        add_debug_log(f"🌐 模式：{st.session_state.mode}，語言：{st.session_state.language}")

        # 設定會議上下文（提高翻譯準確性）
        if st.session_state.mode == "translate_zh":
            terminology = config_manager.get_terminology()
            st.session_state.transcriber.set_meeting_context(
                meeting_topic=st.session_state.meeting_topic,
                terminology=terminology
            )
            add_debug_log(f"📚 已載入會議上下文：主題={st.session_state.meeting_topic}，術語數={len(terminology)}")

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

        # 創建即時逐字稿檔案
        add_debug_log("📝 正在創建即時逐字稿檔案...")
        live_transcript_path = create_live_transcript_file(
            meeting_name=st.session_state.meeting_name,
            meeting_topic=st.session_state.meeting_topic
        )
        st.session_state.controller.set_live_transcript_path(live_transcript_path)
        st.session_state.live_transcript_path = live_transcript_path
        add_debug_log(f"✅ 即時逐字稿檔案已創建：{live_transcript_path}")

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

        st.success("錄音已停止")


# ============================================================================
# 主程式
# ============================================================================

def main():
    """主程式"""
    init_session_state()

    # ========================================================================
    # 側邊欄
    # ========================================================================
    with st.sidebar:
        # 應用標題
        st.markdown("""
        <div style='margin-bottom: 2rem;'>
            <h1 style='font-size: 1.5rem; font-weight: 700; margin: 0; letter-spacing: -0.02em;'>
                Meeting Translator
            </h1>
            <p style='font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0.25rem 0 0 0;'>
                Real-time AI Translation powered by OpenAI
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # API Key 輸入
        st.markdown("<h3>OpenAI API KEY</h3>", unsafe_allow_html=True)
        api_key_input = st.text_input(
            "API Key",
            value=st.session_state.api_key,
            type="password",
            help="請到 https://platform.openai.com/api-keys 取得",
            disabled=st.session_state.is_recording
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 儲存", disabled=st.session_state.is_recording):
                if api_key_input:
                    config_manager.save_api_key(api_key_input)
                    st.session_state.api_key = api_key_input
                    st.success("API Key 已儲存")
                else:
                    st.error("請輸入 API Key")

        with col2:
            if st.button("🗑️ 清除", disabled=st.session_state.is_recording):
                config_manager.clear_api_key()
                st.session_state.api_key = ""
                st.success("API Key 已清除")
                st.rerun()

        st.divider()

        # 會議資訊
        st.markdown("<h3>MEETING INFORMATION</h3>", unsafe_allow_html=True)

        # 讀取會議配置
        meeting_config = config_manager.get_meeting_config()
        meeting_names = meeting_config.get('meeting_names', [])
        meeting_topics = meeting_config.get('meeting_topics', [])

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

        st.divider()

        # 音訊設定
        st.markdown("<h3>AUDIO SETTINGS</h3>", unsafe_allow_html=True)

        # 列出音訊裝置
        devices = AudioRecorder.list_audio_devices()
        device_names = [d['name'] for d in devices]

        # 預設選擇 BlackHole
        default_device = "BlackHole 2ch"
        default_index = 0
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
            value=10,
            disabled=st.session_state.is_recording,
            key='chunk_duration'
        )

        # 靜音閾值
        silence_threshold = st.slider(
            "靜音閾值",
            min_value=0.0,
            max_value=0.1,
            value=0.01,
            step=0.001,
            format="%.3f",
            disabled=st.session_state.is_recording,
            help="低於此閾值的音訊片段將被跳過",
            key='silence_threshold'
        )

        st.divider()

        # 處理模式
        st.markdown("<h3>TRANSLATION MODE</h3>", unsafe_allow_html=True)

        mode_options = {
            "transcribe": "Transcribe (Japanese → Japanese)",
            "translate": "Translate (Japanese → English)",
            "translate_zh": "Translate (Japanese → Chinese)"
        }

        mode = st.radio(
            "選擇模式",
            list(mode_options.keys()),
            format_func=lambda x: mode_options[x],
            index=2,  # 預設為 translate_zh（日語→中文）
            disabled=st.session_state.is_recording,
            key='mode'
        )

        # 語言選擇
        language = st.selectbox(
            "Audio Language",
            ["ja", "en", "zh", "ko", "es", "fr", "de"],
            format_func=lambda x: {
                "ja": "Japanese", "en": "English", "zh": "Chinese",
                "ko": "Korean", "es": "Spanish", "fr": "French", "de": "German"
            }.get(x, x),
            disabled=st.session_state.is_recording or st.session_state.mode in ["translate", "translate_zh"],
            help="This option is disabled in translation mode",
            key='language'
        )

        st.divider()

        # 顯示選項
        st.markdown("<h3>DISPLAY OPTIONS</h3>", unsafe_allow_html=True)

        show_bilingual = st.checkbox(
            "Show multilingual comparison",
            value=st.session_state.show_bilingual,
            disabled=st.session_state.is_recording,
            help="Display original text + translations side by side",
            key='show_bilingual'
        )

        st.divider()

        # 錄音狀態資訊
        if st.session_state.is_recording and st.session_state.recorder:
            st.markdown("<h3>RECORDING STATUS</h3>", unsafe_allow_html=True)
            stats = st.session_state.recorder.get_recording_stats()

            st.metric("Duration", f"{stats['duration']:.1f}s")
            st.metric("File Size", f"{stats['file_size'] / 1024 / 1024:.2f} MB")
            st.metric("Processed Chunks", stats['chunks_processed'])

            if st.session_state.transcriber:
                api_stats = st.session_state.transcriber.get_stats()
                st.metric("API Calls", api_stats['total_calls'])
                if api_stats.get('translation_calls', 0) > 0:
                    st.metric("Translations", api_stats['translation_calls'])
                st.metric("Estimated Cost", f"${api_stats['estimated_cost']:.4f}")

                if st.session_state.worker:
                    queue_size = st.session_state.worker.get_queue_size()
                    worker_status = "Running" if st.session_state.worker.is_running else "Stopped"
                    st.metric("Queue", f"{queue_size} chunks")
                    st.metric("Worker", worker_status)

            st.divider()

        # 錯誤訊息（從 controller 獲取）
        error_messages = st.session_state.error_messages.copy()
        if st.session_state.controller:
            error_messages.extend(st.session_state.controller.error_messages)

        if error_messages:
            st.markdown("<h3>ERRORS</h3>", unsafe_allow_html=True)
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
            st.info("Recommended: Use **English → Chinese** pairs (translation flow: JA→EN→ZH)")

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
                new_source = st.text_input("原文（英文或日文）", key="new_term_source", placeholder="例如：wafer")
            with col_new2:
                new_target = st.text_input("中文翻譯", key="new_term_target", placeholder="例如：晶圓")

            if st.button("➕ 添加術語"):
                if new_source and new_target:
                    if config_manager.add_term(new_source, new_target):
                        st.success(f"已添加：{new_source} → {new_target}")
                        st.rerun()
                    else:
                        st.error("添加失敗")
                else:
                    st.warning("請填寫原文和中文翻譯")

    # ========================================================================
    # 主畫面
    # ========================================================================

    # 頁首 - 狀態指示器和控制面板
    header_col1, header_col2 = st.columns([2, 1])

    with header_col1:
        # 主標題
        st.markdown("""
        <div style='margin-bottom: 0.5rem;'>
            <h1 style='font-size: 2rem; font-weight: 700; margin: 0; letter-spacing: -0.02em;'>
                Live Transcription
            </h1>
        </div>
        """, unsafe_allow_html=True)

    with header_col2:
        # 狀態指示器
        if st.session_state.is_recording:
            if st.session_state.is_paused:
                st.markdown("""
                <div class='status-badge status-paused' style='float: right;'>
                    <span style='font-size: 0.75rem;'>⏸</span>
                    <span>Paused</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='status-badge status-recording' style='float: right;'>
                    <span class='recording-indicator'></span>
                    <span>Recording</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='status-badge status-stopped' style='float: right;'>
                <span style='font-size: 0.75rem;'>⏹</span>
                <span>Stopped</span>
            </div>
            """, unsafe_allow_html=True)

    # 控制按鈕
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    col1, col2, col3, col_spacer = st.columns([1.2, 1, 1, 4])

    with col1:
        start_button_type = "secondary" if st.session_state.is_recording else "primary"
        if st.button(
            "▶ Start Recording" if not st.session_state.is_recording else "● Recording...",
            disabled=st.session_state.is_recording,
            use_container_width=True,
            type="primary"
        ):
            start_recording()
            st.rerun()

    with col2:
        if st.session_state.is_recording and not st.session_state.is_paused:
            if st.button("⏸ Pause", use_container_width=True):
                pause_recording()
                st.rerun()
        elif st.session_state.is_recording and st.session_state.is_paused:
            if st.button("▶ Resume", use_container_width=True):
                resume_recording()
                st.rerun()

    with col3:
        if st.button("⏹ Stop", disabled=not st.session_state.is_recording, use_container_width=True, type="secondary"):
            stop_recording()
            st.rerun()

    st.markdown("<div style='height: 2rem; border-bottom: 1px solid var(--color-bg-tertiary);'></div>", unsafe_allow_html=True)

    # 顯示逐字稿
    st.markdown("""
    <div style='margin: 2rem 0 1rem 0;'>
        <h2 style='font-size: 1.25rem; font-weight: 600; margin: 0;'>
            Transcription Results
        </h2>
        <p style='font-size: 0.875rem; color: var(--color-text-secondary); margin: 0.25rem 0 0 0;'>
            Real-time translation powered by Whisper AI and GPT
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 從 controller 獲取逐字稿（如果正在錄音）
    transcripts = []
    if st.session_state.controller:
        transcripts = st.session_state.controller.transcripts

    if transcripts:
        # 創建一個容器來顯示逐字稿（最新的在最上面）
        for item in transcripts[::-1]:
            timestamp_str = item['timestamp'].strftime('%H:%M:%S')
            text = item['text']
            texts = item.get('texts', {})
            latency = item['latency']
            mode = item['mode']
            language = item.get('language', 'ja')

            # 雙語/多語言顯示
            if st.session_state.show_bilingual and texts:
                # 構建多語言顯示卡片
                card_header = f"""
                <div class='transcript-card'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;'>
                        <span class='timestamp'>{timestamp_str}</span>
                        <span class='latency'>{latency}s</span>
                    </div>
                """

                card_body = ""

                if mode == "transcribe":
                    # 單語模式
                    original_text = texts.get('original', text)
                    original_text_escaped = html_module.escape(original_text)
                    card_body += f"""
                    <div style='margin-bottom: 0.75rem;'>
                        <div class='language-label' style='color: var(--color-text-tertiary);'>
                            <span>●</span> ORIGINAL
                        </div>
                        <div style='color: var(--color-text-primary); line-height: 1.7;'>
                            {original_text_escaped}
                        </div>
                    </div>
                    """

                elif mode == "translate":
                    # 雙語：日語 + 英文
                    ja_text = texts.get('ja', '')
                    en_text = texts.get('en', text)

                    if ja_text:
                        ja_text_escaped = html_module.escape(ja_text)
                        card_body += f"""
                        <div class='japanese-text' style='margin-bottom: 0.75rem;'>
                            <div class='language-label' style='color: #007aff;'>
                                <span>●</span> JAPANESE
                            </div>
                            <div>{ja_text_escaped}</div>
                        </div>
                        """

                    if en_text:
                        en_text_escaped = html_module.escape(en_text)
                        card_body += f"""
                        <div class='english-text'>
                            <div class='language-label' style='color: #34c759;'>
                                <span>●</span> ENGLISH
                            </div>
                            <div>{en_text_escaped}</div>
                        </div>
                        """

                elif mode == "translate_zh":
                    # 三語：日語 + 英文 + 中文
                    ja_text = texts.get('ja', '')
                    en_text = texts.get('en', '')
                    zh_text = texts.get('zh', text)

                    if ja_text:
                        ja_text_escaped = html_module.escape(ja_text)
                        card_body += f"""
                        <div class='japanese-text' style='margin-bottom: 0.75rem;'>
                            <div class='language-label' style='color: #007aff;'>
                                <span>●</span> JAPANESE
                            </div>
                            <div>{ja_text_escaped}</div>
                        </div>
                        """

                    if en_text:
                        en_text_escaped = html_module.escape(en_text)
                        card_body += f"""
                        <div class='english-text' style='margin-bottom: 0.75rem;'>
                            <div class='language-label' style='color: #34c759;'>
                                <span>●</span> ENGLISH
                            </div>
                            <div>{en_text_escaped}</div>
                        </div>
                        """

                    if zh_text:
                        zh_text_escaped = html_module.escape(zh_text)
                        card_body += f"""
                        <div class='chinese-text'>
                            <div class='language-label' style='color: #ff9500;'>
                                <span>●</span> CHINESE
                            </div>
                            <div>{zh_text_escaped}</div>
                        </div>
                        """

                card_footer = "</div>"

                st.markdown(card_header + card_body + card_footer, unsafe_allow_html=True)

            else:
                # 單語顯示
                # 根據語言選擇樣式
                if language == "zh":
                    lang_label = "CHINESE"
                    lang_color = "#ff9500"
                elif language == "en":
                    lang_label = "ENGLISH"
                    lang_color = "#34c759"
                else:
                    lang_label = "JAPANESE"
                    lang_color = "#007aff"

                # Escape HTML 特殊字符
                text_escaped = html_module.escape(text)

                st.markdown(
                    f"""
                    <div class='transcript-card'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;'>
                            <span class='timestamp'>{timestamp_str}</span>
                            <span class='latency'>{latency}s</span>
                        </div>
                        <div class='language-label' style='color: {lang_color};'>
                            <span>●</span> {lang_label}
                        </div>
                        <div style='color: var(--color-text-primary); line-height: 1.7; margin-top: 0.5rem;'>
                            {text_escaped}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    else:
        st.markdown("""
        <div style='text-align: center; padding: 4rem 2rem; color: var(--color-text-tertiary);'>
            <div style='font-size: 3rem; margin-bottom: 1rem; opacity: 0.3;'>🎙</div>
            <div style='font-size: 1rem; font-weight: 500;'>No transcription yet</div>
            <div style='font-size: 0.875rem; margin-top: 0.5rem;'>Click "Start Recording" to begin</div>
        </div>
        """, unsafe_allow_html=True)

    # 停止後顯示下載按鈕
    if not st.session_state.is_recording and transcripts:
        st.divider()

        # 顯示即時逐字稿檔案位置
        if st.session_state.live_transcript_path and Path(st.session_state.live_transcript_path).exists():
            st.info(f"Live transcript saved automatically: `{st.session_state.live_transcript_path}`")

        col1, col2 = st.columns(2)

        with col1:
            # 下載逐字稿（支援語言選擇）
            st.markdown("<h3>DOWNLOAD TRANSCRIPT</h3>", unsafe_allow_html=True)

            language_options = {
                "all": "All Languages (JA + EN + ZH)",
                "ja": "Japanese Only",
                "en": "English Only",
                "zh": "Chinese Only"
            }

            selected_language = st.selectbox(
                "Select Language",
                list(language_options.keys()),
                format_func=lambda x: language_options[x],
                key='download_language_selection'
            )

            if st.button("Generate File", use_container_width=True, type="primary"):
                file_path = save_transcript_to_file(
                    transcripts,
                    meeting_name=st.session_state.meeting_name,
                    meeting_topic=st.session_state.meeting_topic,
                    language_selection=selected_language
                )
                with open(file_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                st.download_button(
                    label="Download TXT",
                    data=transcript_content,
                    file_name=Path(file_path).name,
                    mime="text/plain",
                    use_container_width=True
                )
                st.success(f"File generated: {Path(file_path).name}")

        with col2:
            # 下載錄音
            st.markdown("<h3>DOWNLOAD AUDIO</h3>", unsafe_allow_html=True)
            if st.session_state.recorder:
                stats = st.session_state.recorder.get_recording_stats()
                recording_file = stats.get('file_path')
                if recording_file and Path(recording_file).exists():
                    file_size_mb = Path(recording_file).stat().st_size / 1024 / 1024
                    st.caption(f"File size: {file_size_mb:.2f} MB")
                    with open(recording_file, 'rb') as f:
                        audio_data = f.read()
                    st.download_button(
                        label="Download WAV",
                        data=audio_data,
                        file_name=Path(recording_file).name,
                        mime="audio/wav",
                        use_container_width=True
                    )
                else:
                    st.info("No audio file available")
            else:
                st.info("No audio file available")

    # 自動重新整理（錄音中時）
    if st.session_state.is_recording:
        time.sleep(1)
        st.rerun()


if __name__ == "__main__":
    main()
