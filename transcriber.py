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


LANGUAGE_LABELS_ZH = {
    "ja": "日語",
    "en": "英文",
    "zh": "中文",
    "ko": "韓文",
    "es": "西班牙文",
    "fr": "法文",
    "de": "德文"
}


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
        self.mode = "transcribe"  # 預設模式：transcribe, translate_en, translate_target
        self.language = "ja"  # 預設語言：日語
        self.target_language = "zh"  # 預設目標語言：中文

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
        self.terminology = {}  # 術語詞典 {原文: 翻譯}
        self.previous_texts = []  # 上下文（最近的翻譯）

    def set_mode(self, mode: Literal["transcribe", "translate_en", "translate_target", "translate_zh", "translate"]):
        """
        設定處理模式

        Args:
            mode: "transcribe" 表示轉錄為原語言文字
                  "translate_en" 表示翻譯為英文
                  "translate_target" 表示翻譯為目標語言
        """
        if mode == "translate":
            mode = "translate_en"
        if mode == "translate_zh":
            mode = "translate_target"
        if mode not in ["transcribe", "translate_en", "translate_target"]:
            raise ValueError("模式必須為 'transcribe'、'translate_en' 或 'translate_target'")
        self.mode = mode

    def set_language(self, language: str):
        """
        設定音訊語言

        Args:
            language: 語言代碼（例如 'ja', 'en', 'zh' 等）
        """
        self.language = language

    def set_target_language(self, language: str):
        """
        設定目標語言

        Args:
            language: 目標語言代碼（例如 'zh', 'en', 'ja' 等）
        """
        self.target_language = language

    def set_meeting_context(self, meeting_topic: str = "", terminology: dict = None):
        """
        設定會議上下文（用於提高翻譯準確性）

        Args:
            meeting_topic: 會議主題/類型
            terminology: 術語詞典 {原文: 翻譯}
        """
        self.meeting_topic = meeting_topic
        self.terminology = terminology or {}
        print(f"📚 會議主題：{meeting_topic}")
        if self.terminology:
            print(f"📖 載入術語詞典：{len(self.terminology)} 個術語")

    def _extract_text(self, response) -> str:
        """將不同型態的 API 回應轉成字串"""
        if isinstance(response, str):
            return response.strip()
        if hasattr(response, "text"):
            return response.text.strip()
        if isinstance(response, dict):
            return response.get("text", "").strip()
        return str(response).strip()

    def _get_source_language_label(self, language: str) -> str:
        """回傳語言的中文名稱"""
        return LANGUAGE_LABELS_ZH.get(language, language.upper())

    def _transcribe_source_text(self, audio_file: BytesIO) -> str:
        """以來源語言做逐字稿"""
        response = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", audio_file, "audio/wav"),
            language=self.language,
            response_format="text"
        )
        return self._extract_text(response)

    def _translate_audio_to_english(self, audio_file: BytesIO) -> str:
        """將音訊翻譯為英文"""
        response = self.client.audio.translations.create(
            model="whisper-1",
            file=("audio.wav", audio_file, "audio/wav"),
            response_format="text"
        )
        return self._extract_text(response)

    def translate_to_target_language(
        self,
        source_text: str,
        source_language: str,
        target_language: str,
        english_text: str = ""
    ) -> str:
        """
        使用 GPT API 將原文翻譯為指定語言

        Args:
            source_text: 原文文字
            source_language: 原文語言代碼
            target_language: 目標語言代碼
            english_text: 英文參考（可選，用於輔助理解）

        Returns:
            目標語言翻譯
        """
        try:
            source_label = self._get_source_language_label(source_language)
            target_label = self._get_source_language_label(target_language)

            # 構建 system prompt
            system_prompt = f"你是專業的翻譯專家，請將文字翻譯成自然流暢的{target_label}。只返回翻譯結果，不要添加任何解釋或註解。"

            # 如果有會議主題，加入上下文
            if self.meeting_topic:
                system_prompt += f"\n\n這是一場關於「{self.meeting_topic}」的會議，請使用相關的專業術語。"

            # 如果有術語詞典，加入翻譯指引（適用所有目標語言）
            if self.terminology:
                terms_list = "\n".join([f"- {src} → {tgt}" for src, tgt in self.terminology.items()])
                system_prompt += f"\n\nIMPORTANT — Use these exact translations for the following terms:\n{terms_list}"

            # 構建 user prompt
            if english_text and source_language != "en":
                user_prompt = f"{source_label}原文：{source_text}\n英文參考：{english_text}\n\n請翻譯成{target_label}："
            else:
                user_prompt = f"{source_label}原文：{source_text}\n\n請翻譯成{target_label}："

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
            self.previous_texts.append(f"{source_label}：{source_text}\n{target_label}：{translated_text}")
            if len(self.previous_texts) > 10:  # 只保留最近 10 句
                self.previous_texts = self.previous_texts[-10:]

            print(f"🈯 翻譯完成：{source_text[:30]}... → {translated_text[:30]}...")
            return translated_text

        except Exception as e:
            print(f"❌ GPT 翻譯失敗：{e}")
            return f"[翻譯錯誤] {source_text}"

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

                # 先取得來源語言逐字稿，後續模式都以此為基礎
                source_text = self._transcribe_source_text(audio_file)
                texts = {self.language: source_text}
                text = source_text
                whisper_calls = 1
                source_language = self.language

                if self.mode == "translate_en":
                    if source_language == "en":
                        english_text = source_text
                    else:
                        audio_file.seek(0)
                        english_text = self._translate_audio_to_english(audio_file)
                        whisper_calls += 1

                    texts['en'] = english_text
                    text = english_text

                elif self.mode == "translate_target":
                    english_text = ""

                    if source_language != "en":
                        audio_file.seek(0)
                        english_text = self._translate_audio_to_english(audio_file)
                        texts['en'] = english_text
                        whisper_calls += 1
                    else:
                        texts['en'] = source_text
                        english_text = source_text

                    if self.target_language == source_language:
                        target_text = source_text
                    elif self.target_language == "en":
                        target_text = english_text or source_text
                    else:
                        target_text = self.translate_to_target_language(
                            source_text,
                            source_language,
                            self.target_language,
                            english_text
                        )

                    texts[self.target_language] = target_text
                    text = target_text

                # 計算延遲時間
                latency = time.time() - start_time

                # 更新統計資訊
                self.total_api_calls += whisper_calls
                self.total_audio_duration += duration

                # 如果文字為空，視為無效結果
                if not text:
                    return None

                # 判斷輸出語言
                if self.mode == "transcribe":
                    output_language = source_language
                elif self.mode == "translate_en":
                    output_language = "en"
                else:  # translate_target
                    output_language = self.target_language

                return {
                    'text': text,
                    'texts': texts,  # 所有語言版本，以語言代碼為 key
                    'mode': self.mode,
                    'source_language': source_language,
                    'target_language': self.target_language,
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
            'language': self.language,
            'target_language': self.target_language
        }


class TranscriberWorker:
    """語音轉文字背景工作器（在獨立執行緒中執行）"""

    # Circuit breaker 設定
    CB_FAILURE_THRESHOLD = 3       # 連續失敗幾次後觸發
    CB_INITIAL_BACKOFF = 10        # 初始冷卻秒數
    CB_MAX_BACKOFF = 300           # 最大冷卻秒數（5 分鐘）
    CB_BACKOFF_MULTIPLIER = 2      # 指數退避倍率

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

        # Circuit breaker 狀態
        self._consecutive_failures = 0
        self._circuit_open = False          # True = 熔斷中，暫停 API 呼叫
        self._circuit_reopen_at = 0.0       # 熔斷結束的 time.time()
        self._current_backoff = self.CB_INITIAL_BACKOFF

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

    def _record_success(self):
        """API 呼叫成功時重置 circuit breaker"""
        self._consecutive_failures = 0
        if self._circuit_open:
            print("🟢 Circuit breaker 已恢復（API 重新正常）")
            self._circuit_open = False
            self._current_backoff = self.CB_INITIAL_BACKOFF

    def _record_failure(self):
        """API 呼叫失敗時更新 circuit breaker 計數"""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.CB_FAILURE_THRESHOLD and not self._circuit_open:
            self._circuit_open = True
            self._circuit_reopen_at = time.time() + self._current_backoff
            print(
                f"🔴 Circuit breaker 觸發！連續 {self._consecutive_failures} 次失敗，"
                f"暫停 API 呼叫 {self._current_backoff}s"
            )
            # 發送熔斷事件到輸出佇列，讓 UI 顯示
            self.output_queue.put({
                'success': False,
                'error': f"Circuit breaker: API 連續失敗 {self._consecutive_failures} 次，暫停 {self._current_backoff}s 後自動重試",
                'circuit_breaker': True
            })
            # 下次觸發時退避時間加倍
            self._current_backoff = min(
                self._current_backoff * self.CB_BACKOFF_MULTIPLIER,
                self.CB_MAX_BACKOFF
            )

    def _is_circuit_open(self) -> bool:
        """檢查 circuit breaker 是否仍處於熔斷狀態"""
        if not self._circuit_open:
            return False
        if time.time() >= self._circuit_reopen_at:
            # 冷卻結束，進入 half-open 狀態（允許嘗試一次）
            print("🟡 Circuit breaker 冷卻結束，嘗試半開放狀態...")
            self._circuit_open = False
            return False
        return True

    def get_circuit_breaker_status(self) -> dict:
        """回傳 circuit breaker 狀態（供 UI 查詢）"""
        remaining = max(0, self._circuit_reopen_at - time.time()) if self._circuit_open else 0
        return {
            'is_open': self._circuit_open,
            'consecutive_failures': self._consecutive_failures,
            'remaining_seconds': round(remaining, 1),
            'current_backoff': self._current_backoff
        }

    def _worker_loop(self):
        """工作器主迴圈"""
        print("🚀 Worker 執行緒已啟動")

        while self.is_running:
            try:
                # Circuit breaker 熔斷中 — 跳過 API 呼叫，丟棄 chunk
                if self._is_circuit_open():
                    try:
                        self.input_queue.get(timeout=0.5)
                        # 丟棄此 chunk，等冷卻結束再恢復
                    except queue.Empty:
                        pass
                    continue

                # 從輸入佇列取得音訊片段（超時 0.5 秒）
                chunk = self.input_queue.get(timeout=0.5)

                print(f"📥 Worker 收到音訊片段，準備呼叫 API...")

                # 呼叫 Whisper API
                result = self.transcriber.transcribe_audio(
                    chunk['audio'],
                    chunk['duration']
                )

                if result:
                    if result.get('success', True):
                        print(f"✅ API 呼叫成功：{result.get('text', '')[:50]}")
                        self._record_success()
                    else:
                        print(f"⚠️ API 呼叫失敗：{result.get('error', '')}")
                        self._record_failure()
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
                self._record_failure()
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
