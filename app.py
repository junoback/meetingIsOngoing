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

from config_manager import config_manager
from audio_recorder import AudioRecorder
from transcriber import Transcriber, TranscriberWorker


# 設定頁面配置
st.set_page_config(
    page_title="即時會議翻譯 App",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂 CSS 樣式
st.markdown("""
<style>
    .japanese-text {
        background-color: #E3F2FD;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .english-text {
        background-color: #E8F5E9;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .chinese-text {
        background-color: #FFF3E0;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .timestamp {
        color: #666;
        font-size: 0.9em;
        font-weight: bold;
    }
    .latency {
        color: #999;
        font-size: 0.8em;
        font-style: italic;
    }
    .status-recording {
        color: #ff0000;
        animation: blink 1s infinite;
    }
    .status-paused {
        color: #ff9800;
    }
    .status-stopped {
        color: #999;
    }
    @keyframes blink {
        0%, 50%, 100% { opacity: 1; }
        25%, 75% { opacity: 0.5; }
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


def save_transcript_to_file(transcripts: list, meeting_name: str = "", meeting_topic: str = "") -> str:
    """
    將逐字稿儲存為文字檔

    Args:
        transcripts: 逐字稿列表
        meeting_name: 會議名稱
        meeting_topic: 會議主題

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
        f.write(f"產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for item in reversed(transcripts):
            f.write(f"[{item['timestamp'].strftime('%H:%M:%S')}]\n")
            f.write(f"{item['text']}\n")
            f.write(f"(延遲：{item['latency']}秒，模式：{item['mode']})\n")
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
        st.title("🎙️ 會議翻譯 App")
        st.markdown("使用 OpenAI Whisper API 即時翻譯日語會議")
        st.divider()

        # API Key 輸入
        st.subheader("OpenAI API Key")
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
        st.subheader("📋 會議資訊")

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
        st.subheader("音訊設定")

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
            value=5,
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
        st.subheader("處理模式")

        mode_options = {
            "transcribe": "📝 Transcribe（日語→日語）",
            "translate": "🌐 Translate（日語→英文）",
            "translate_zh": "🈯 翻譯（日語→中文）"
        }

        mode = st.radio(
            "選擇模式",
            list(mode_options.keys()),
            format_func=lambda x: mode_options[x],
            disabled=st.session_state.is_recording,
            key='mode'
        )

        # 語言選擇
        language = st.selectbox(
            "音訊語言",
            ["ja", "en", "zh", "ko", "es", "fr", "de"],
            format_func=lambda x: {
                "ja": "日語", "en": "英語", "zh": "中文",
                "ko": "韓語", "es": "西班牙語", "fr": "法語", "de": "德語"
            }.get(x, x),
            disabled=st.session_state.is_recording or st.session_state.mode in ["translate", "translate_zh"],
            help="翻譯模式下此選項無效",
            key='language'
        )

        st.divider()

        # 顯示選項
        st.subheader("顯示設定")

        show_bilingual = st.checkbox(
            "顯示多語言對照",
            value=st.session_state.show_bilingual,
            disabled=st.session_state.is_recording,
            help="翻譯模式下顯示原文+譯文對照",
            key='show_bilingual'
        )

        st.divider()

        # 錄音狀態資訊
        if st.session_state.is_recording and st.session_state.recorder:
            st.subheader("📊 錄音狀態")
            stats = st.session_state.recorder.get_recording_stats()

            st.metric("錄音時長", f"{stats['duration']:.1f} 秒")
            st.metric("檔案大小", f"{stats['file_size'] / 1024 / 1024:.2f} MB")
            st.metric("已處理片段", stats['chunks_processed'])

            if st.session_state.transcriber:
                api_stats = st.session_state.transcriber.get_stats()
                st.metric("Whisper API 呼叫次數", api_stats['total_calls'])
                if api_stats.get('translation_calls', 0) > 0:
                    st.metric("GPT 翻譯次數", api_stats['translation_calls'])
                st.metric("API 費用估算", f"${api_stats['estimated_cost']:.4f} USD")

                if st.session_state.worker:
                    queue_size = st.session_state.worker.get_queue_size()
                    worker_status = "✅ 運行中" if st.session_state.worker.is_running else "❌ 已停止"
                    st.metric("待處理佇列", f"{queue_size} 個片段")
                    st.metric("Worker 狀態", worker_status)

            st.divider()

        # 錯誤訊息（從 controller 獲取）
        error_messages = st.session_state.error_messages.copy()
        if st.session_state.controller:
            error_messages.extend(st.session_state.controller.error_messages)

        if error_messages:
            st.subheader("⚠️ 錯誤訊息")
            error_container = st.container()
            with error_container:
                for error in error_messages[-5:]:  # 只顯示最近 5 條
                    st.error(error, icon="⚠️")

        # 調試日誌（可展開）
        if st.session_state.debug_logs:
            with st.expander("🔍 調試日誌", expanded=False):
                for log in st.session_state.debug_logs[-20:]:  # 只顯示最近 20 條
                    st.text(log)

        # 術語詞典管理（可展開）
        with st.expander("📖 術語詞典管理", expanded=False):
            st.markdown("**管理專有名詞翻譯**")
            st.info("💡 建議使用 **英文 → 中文** 對照（因為翻譯流程：日語→英文→中文）")

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

    st.title("🎙️ 即時會議翻譯")

    # 控制按鈕
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

    with col1:
        if st.button("🎙️ 開始錄音", disabled=st.session_state.is_recording, use_container_width=True):
            start_recording()
            st.rerun()

    with col2:
        if st.session_state.is_recording and not st.session_state.is_paused:
            if st.button("⏸️ 暫停", use_container_width=True):
                pause_recording()
                st.rerun()
        elif st.session_state.is_recording and st.session_state.is_paused:
            if st.button("▶️ 繼續", use_container_width=True):
                resume_recording()
                st.rerun()

    with col3:
        if st.button("⏹️ 停止", disabled=not st.session_state.is_recording, use_container_width=True):
            stop_recording()
            st.rerun()

    # 狀態指示
    st.divider()

    if st.session_state.is_recording:
        if st.session_state.is_paused:
            st.markdown("### <span class='status-paused'>⏸️ 已暫停</span>", unsafe_allow_html=True)
        else:
            st.markdown("### <span class='status-recording'>🔴 錄音中</span>", unsafe_allow_html=True)
    else:
        st.markdown("### <span class='status-stopped'>⚫ 已停止</span>", unsafe_allow_html=True)

    st.divider()

    # 顯示逐字稿
    st.subheader("即時辨識結果")

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

            # 根據語言選擇樣式
            if language == "zh":
                bg_class = "chinese-text"
                lang_label = "🈯 中文"
            elif language == "en":
                bg_class = "english-text"
                lang_label = "🌐 英文"
            else:
                bg_class = "japanese-text"
                lang_label = "📝 日語"

            # 雙語/多語言顯示
            if st.session_state.show_bilingual and texts:
                # 構建多語言顯示內容
                display_content = f"<span class='timestamp'>[{timestamp_str}]</span> <span class='latency'>(延遲：{latency}秒)</span><br>"

                if mode == "transcribe":
                    # 單語模式，只顯示原文
                    display_content += f"<strong>📝 原文：</strong>{texts.get('original', text)}"

                elif mode == "translate":
                    # 雙語：日語 + 英文
                    display_content += f"<strong>📝 日語：</strong>{texts.get('ja', '')}<br>"
                    display_content += f"<strong>🌐 英文：</strong>{texts.get('en', text)}"

                elif mode == "translate_zh":
                    # 三語：日語 + 英文 + 中文
                    display_content += f"<strong>📝 日語：</strong>{texts.get('ja', '')}<br>"
                    display_content += f"<strong>🌐 英文：</strong>{texts.get('en', '')}<br>"
                    display_content += f"<strong>🈯 中文：</strong>{texts.get('zh', text)}"

                st.markdown(
                    f"""
                    <div class='{bg_class}'>
                        {display_content}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                # 單語顯示（原有邏輯）
                st.markdown(
                    f"""
                    <div class='{bg_class}'>
                        <span class='timestamp'>[{timestamp_str}]</span>
                        <span class='latency'>({lang_label} · 延遲：{latency}秒)</span><br>
                        {text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    else:
        st.info("尚無辨識結果，請開始錄音")

    # 停止後顯示下載按鈕
    if not st.session_state.is_recording and transcripts:
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            # 下載逐字稿
            if st.button("📥 下載逐字稿", use_container_width=True):
                file_path = save_transcript_to_file(
                    transcripts,
                    meeting_name=st.session_state.meeting_name,
                    meeting_topic=st.session_state.meeting_topic
                )
                with open(file_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                st.download_button(
                    label="💾 儲存 TXT 檔案",
                    data=transcript_content,
                    file_name=Path(file_path).name,
                    mime="text/plain",
                    use_container_width=True
                )
                st.success(f"逐字稿已產生：{file_path}")

        with col2:
            # 下載錄音
            if st.session_state.recorder:
                stats = st.session_state.recorder.get_recording_stats()
                recording_file = stats.get('file_path')
                if recording_file and Path(recording_file).exists():
                    with open(recording_file, 'rb') as f:
                        audio_data = f.read()
                    st.download_button(
                        label="📥 下載錄音",
                        data=audio_data,
                        file_name=Path(recording_file).name,
                        mime="audio/wav",
                        use_container_width=True
                    )

    # 自動重新整理（錄音中時）
    if st.session_state.is_recording:
        time.sleep(1)
        st.rerun()


if __name__ == "__main__":
    main()
