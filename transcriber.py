#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
語音轉文字模組 - 負責呼叫 OpenAI Whisper API 進行語音辨識和翻譯
"""

import time
from io import BytesIO
from typing import Optional, Dict, Literal
from openai import OpenAI
import threading
import queue


class Transcriber:
    """語音轉文字處理器類別"""

    # Whisper API 費用（每分鐘）
    API_COST_PER_MINUTE = 0.006  # $0.006 / minute

    def __init__(self, api_key: str):
        """
        初始化語音轉文字處理器

        Args:
            api_key: OpenAI API Key
        """
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.mode = "transcribe"  # 預設模式：transcribe, translate, translate_zh
        self.language = "ja"  # 預設語言：日語

        # 重試設定
        self.max_retries = 3
        self.retry_delay = 1  # 秒

        # 統計資訊
        self.total_api_calls = 0
        self.total_audio_duration = 0  # 總音訊時長（秒）
        self.failed_calls = 0
        self.total_translation_calls = 0  # GPT 翻譯呼叫次數

        # 翻譯優化
        self.meeting_topic = ""  # 會議主題
        self.terminology = {}  # 術語詞典 {日語: 中文}
        self.previous_texts = []  # 上下文（最近的翻譯）

    def set_mode(self, mode: Literal["transcribe", "translate", "translate_zh"]):
        """
        設定處理模式

        Args:
            mode: "transcribe" 表示轉錄為原語言文字
                  "translate" 表示翻譯為英文
                  "translate_zh" 表示翻譯為中文
        """
        if mode not in ["transcribe", "translate", "translate_zh"]:
            raise ValueError("模式必須為 'transcribe'、'translate' 或 'translate_zh'")
        self.mode = mode

    def set_language(self, language: str):
        """
        設定音訊語言（僅在 transcribe 模式下有效）

        Args:
            language: 語言代碼（例如 'ja', 'en', 'zh' 等）
        """
        self.language = language

    def set_meeting_context(self, meeting_topic: str = "", terminology: dict = None):
        """
        設定會議上下文（用於提高翻譯準確性）

        Args:
            meeting_topic: 會議主題/類型
            terminology: 術語詞典 {日語: 中文}
        """
        self.meeting_topic = meeting_topic
        self.terminology = terminology or {}
        print(f"📚 會議主題：{meeting_topic}")
        if self.terminology:
            print(f"📖 載入術語詞典：{len(self.terminology)} 個術語")

    def translate_to_chinese(self, japanese_text: str, english_text: str = "") -> str:
        """
        使用 GPT API 將日語翻譯為繁體中文

        Args:
            japanese_text: 日語文字
            english_text: 英文翻譯（可選，用於輔助理解）

        Returns:
            繁體中文翻譯
        """
        try:
            # 構建 system prompt
            system_prompt = "你是專業的翻譯專家，請將文字翻譯成自然流暢的繁體中文。只返回翻譯結果，不要添加任何解釋或註解。"

            # 如果有會議主題，加入上下文
            if self.meeting_topic:
                system_prompt += f"\n\n這是一場關於「{self.meeting_topic}」的會議，請使用相關的專業術語。"

            # 如果有術語詞典，加入翻譯指引（英文→中文）
            if self.terminology:
                terms_list = "\n".join([f"- {en} → {zh}" for en, zh in self.terminology.items()])
                system_prompt += f"\n\n請特別注意以下專有名詞的翻譯（優先使用這些翻譯）：\n{terms_list}"

            # 構建 user prompt（同時提供日文和英文）
            if english_text:
                user_prompt = f"日語原文：{japanese_text}\n英文翻譯：{english_text}\n\n請翻譯成繁體中文："
            else:
                user_prompt = f"請翻譯：{japanese_text}"

            # 如果有上下文，加入前幾句話作為參考
            if self.previous_texts:
                context = "\n".join(self.previous_texts[-3:])  # 最近 3 句
                user_prompt = f"前文參考：\n{context}\n\n{user_prompt}"

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )

            self.total_translation_calls += 1
            translated_text = response.choices[0].message.content.strip()

            # 儲存到上下文
            self.previous_texts.append(f"日：{japanese_text}\n中：{translated_text}")
            if len(self.previous_texts) > 10:  # 只保留最近 10 句
                self.previous_texts = self.previous_texts[-10:]

            print(f"🈯 翻譯完成：{japanese_text[:30]}... → {translated_text[:30]}...")
            return translated_text

        except Exception as e:
            print(f"❌ GPT 翻譯失敗：{e}")
            return f"[翻譯錯誤] {japanese_text}"

    def transcribe_audio(self, audio_file: BytesIO, duration: float) -> Optional[Dict]:
        """
        轉錄音訊為文字

        Args:
            audio_file: 音訊檔案（BytesIO 物件）
            duration: 音訊時長（秒）

        Returns:
            結果字典，包含 text、mode、language、duration、latency 等資訊
            多語言模式下會包含 texts 字典（包含所有語言版本）
            如果失敗返回 None
        """
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                # 重設 BytesIO 的讀取位置
                audio_file.seek(0)

                # 儲存所有語言版本的文字
                texts = {}

                # 呼叫 Whisper API
                if self.mode == "transcribe":
                    # 轉錄模式（保留原語言）
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=("audio.wav", audio_file, "audio/wav"),
                        language=self.language,
                        response_format="text"
                    )
                    text = response.strip() if isinstance(response, str) else response.get('text', '').strip()
                    texts['original'] = text

                elif self.mode == "translate":
                    # 先取得日語原文
                    audio_file.seek(0)
                    response_ja = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=("audio.wav", audio_file, "audio/wav"),
                        language=self.language,
                        response_format="text"
                    )
                    japanese_text = response_ja.strip() if isinstance(response_ja, str) else response_ja.get('text', '').strip()
                    texts['ja'] = japanese_text

                    # 再翻譯為英文
                    audio_file.seek(0)
                    response_en = self.client.audio.translations.create(
                        model="whisper-1",
                        file=("audio.wav", audio_file, "audio/wav"),
                        response_format="text"
                    )
                    text = response_en.strip() if isinstance(response_en, str) else response_en.get('text', '').strip()
                    texts['en'] = text

                else:  # translate_zh
                    # 先轉錄日語
                    response_ja = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=("audio.wav", audio_file, "audio/wav"),
                        language=self.language,
                        response_format="text"
                    )
                    japanese_text = response_ja.strip() if isinstance(response_ja, str) else response_ja.get('text', '').strip()
                    texts['ja'] = japanese_text

                    # 再翻譯為英文
                    audio_file.seek(0)
                    response_en = self.client.audio.translations.create(
                        model="whisper-1",
                        file=("audio.wav", audio_file, "audio/wav"),
                        response_format="text"
                    )
                    english_text = response_en.strip() if isinstance(response_en, str) else response_en.get('text', '').strip()
                    texts['en'] = english_text

                    # 最後翻譯成中文（同時傳入日文和英文）
                    chinese_text = self.translate_to_chinese(japanese_text, english_text)
                    texts['zh'] = chinese_text
                    text = chinese_text

                # 計算延遲時間
                latency = time.time() - start_time

                # 更新統計資訊（translate 和 translate_zh 模式呼叫了2次 Whisper）
                if self.mode in ["translate", "translate_zh"]:
                    self.total_api_calls += 2
                else:
                    self.total_api_calls += 1
                self.total_audio_duration += duration

                # 如果文字為空，視為無效結果
                if not text:
                    return None

                # 判斷輸出語言
                if self.mode == "transcribe":
                    output_language = self.language
                elif self.mode == "translate":
                    output_language = "en"
                else:  # translate_zh
                    output_language = "zh"

                return {
                    'text': text,
                    'texts': texts,  # 所有語言版本
                    'mode': self.mode,
                    'language': output_language,
                    'duration': duration,
                    'latency': round(latency, 2),
                    'success': True
                }

            except Exception as e:
                error_message = str(e)
                print(f"API 呼叫失敗（第 {attempt + 1}/{self.max_retries} 次嘗試）：{error_message}")

                if attempt < self.max_retries - 1:
                    # 等待後重試
                    time.sleep(self.retry_delay)
                else:
                    # 最後一次嘗試失敗
                    self.failed_calls += 1
                    return {
                        'text': f"[錯誤] {error_message}",
                        'mode': self.mode,
                        'language': self.language,
                        'duration': duration,
                        'latency': round(time.time() - start_time, 2),
                        'success': False,
                        'error': error_message
                    }

        return None

    def get_api_cost_estimate(self) -> float:
        """
        取得 API 費用估算

        Returns:
            預估費用（美元）
        """
        return (self.total_audio_duration / 60) * self.API_COST_PER_MINUTE

    def get_stats(self) -> Dict:
        """
        取得統計資訊

        Returns:
            統計資訊字典
        """
        return {
            'total_calls': self.total_api_calls,
            'translation_calls': self.total_translation_calls,
            'failed_calls': self.failed_calls,
            'total_duration': round(self.total_audio_duration, 1),
            'estimated_cost': round(self.get_api_cost_estimate(), 4),
            'mode': self.mode,
            'language': self.language
        }


class TranscriberWorker:
    """語音轉文字背景工作器（在獨立執行緒中執行）"""

    def __init__(self, transcriber: Transcriber):
        """
        初始化背景工作器

        Args:
            transcriber: Transcriber 實例
        """
        self.transcriber = transcriber
        self.is_running = False
        self.worker_thread = None

        # 輸入和輸出佇列
        self.input_queue = queue.Queue()  # 待處理的音訊片段
        self.output_queue = queue.Queue()  # 處理完成的結果

    def start(self):
        """啟動背景工作器"""
        if self.is_running:
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """停止背景工作器"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
            self.worker_thread = None

    def _worker_loop(self):
        """工作器主迴圈"""
        print("🚀 Worker 執行緒已啟動")

        while self.is_running:
            try:
                # 從輸入佇列取得音訊片段（超時 0.5 秒）
                chunk = self.input_queue.get(timeout=0.5)

                print(f"📥 Worker 收到音訊片段，準備呼叫 API...")

                # 呼叫 Whisper API
                result = self.transcriber.transcribe_audio(
                    chunk['audio'],
                    chunk['duration']
                )

                if result:
                    print(f"✅ API 呼叫成功：{result.get('text', '')[:50]}")
                    # 添加時間戳記
                    result['timestamp'] = chunk['timestamp']
                    # 放入輸出佇列
                    self.output_queue.put(result)
                else:
                    print("⚠️ API 返回空結果")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 工作器錯誤：{e}")
                import traceback
                traceback.print_exc()

        print("⏹️ Worker 執行緒已停止")

    def add_audio_chunk(self, audio_chunk: Dict):
        """
        添加音訊片段到處理佇列

        Args:
            audio_chunk: 音訊片段字典（包含 audio、timestamp、duration）
        """
        self.input_queue.put(audio_chunk)

    def get_result(self, timeout: Optional[float] = None) -> Optional[Dict]:
        """
        取得處理結果

        Args:
            timeout: 超時時間（秒），None 表示不等待

        Returns:
            處理結果字典，如果佇列為空返回 None
        """
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_queue_size(self) -> int:
        """
        取得待處理佇列大小

        Returns:
            待處理的音訊片段數量
        """
        return self.input_queue.qsize()
