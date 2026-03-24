#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
語音轉文字模組 - 支援多個 STT / 翻譯 Provider

STT:  OpenAI Whisper, Groq Whisper
翻譯: GPT-4o-mini, DeepL, Gemini Flash, Claude Haiku
"""

import time
import json
import logging
from io import BytesIO
from typing import Optional, Dict, Literal
from openai import OpenAI
import threading
import queue
import urllib.request
import urllib.error

logger = logging.getLogger("meeting-translator")


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
    """語音轉文字處理器類別（支援多 Provider）"""

    # Whisper API 費用（每分鐘）
    API_COST_PER_MINUTE = 0.006  # $0.006 / minute

    def __init__(
        self,
        stt_api_key: str,
        stt_provider: str = "openai_whisper",
        translation_api_key: str = "",
        translation_provider: str = "openai_gpt",
    ):
        """
        初始化語音轉文字處理器

        Args:
            stt_api_key: STT provider 的 API Key
            stt_provider: STT provider 名稱（openai_whisper / groq_whisper）
            translation_api_key: 翻譯 provider 的 API Key（空字串時與 STT 共用）
            translation_provider: 翻譯 provider 名稱
        """
        # 延遲 import，避免 circular dependency
        from templates import STT_PROVIDERS, TRANSLATION_PROVIDERS

        self.stt_provider = stt_provider
        self.translation_provider = translation_provider
        self.stt_api_key = stt_api_key
        self.translation_api_key = translation_api_key or stt_api_key

        # 取得 provider 設定
        stt_cfg = STT_PROVIDERS.get(stt_provider, STT_PROVIDERS["openai_whisper"])
        trans_cfg = TRANSLATION_PROVIDERS.get(translation_provider, TRANSLATION_PROVIDERS["openai_gpt"])

        # 建立 STT client（OpenAI SDK，Groq 也相容）
        stt_kwargs = {"api_key": self.stt_api_key}
        if stt_cfg.get("base_url"):
            stt_kwargs["base_url"] = stt_cfg["base_url"]
        self.stt_client = OpenAI(**stt_kwargs)
        self.stt_model = stt_cfg.get("model", "whisper-1")

        # 建立翻譯 client
        self.translation_type = trans_cfg.get("type", "openai_compatible")
        self.translation_model = trans_cfg.get("model", "gpt-4o-mini")
        self.translation_base_url = trans_cfg.get("base_url")

        if self.translation_type == "openai_compatible":
            trans_kwargs = {"api_key": self.translation_api_key}
            if self.translation_base_url:
                trans_kwargs["base_url"] = self.translation_base_url
            self.translation_client = OpenAI(**trans_kwargs)
        else:
            # DeepL / Anthropic — 用 urllib 直接呼叫 REST API
            self.translation_client = None

        self.mode = "transcribe"
        self.language = "ja"
        self.target_language = "zh"

        # 重試設定
        self.max_retries = 3
        self.retry_delay = 1

        # 統計資訊
        self.total_api_calls = 0
        self.total_audio_duration = 0
        self.failed_calls = 0
        self.total_translation_calls = 0

        # 翻譯優化
        self.meeting_topic = ""
        self.terminology = {}
        self.previous_texts = []

        logger.info(
            "🔧 Transcriber 初始化：STT=%s (%s), 翻譯=%s (%s)",
            stt_provider, self.stt_model,
            translation_provider, self.translation_model or "REST"
        )

    # === 向後相容：舊的單一 api_key 建構方式 ===
    @classmethod
    def from_single_key(cls, api_key: str) -> "Transcriber":
        """舊介面相容：只傳一把 OpenAI key，STT 和翻譯都用 OpenAI"""
        return cls(
            stt_api_key=api_key,
            stt_provider="openai_whisper",
            translation_api_key=api_key,
            translation_provider="openai_gpt",
        )

    # ================================================================
    # 設定方法
    # ================================================================

    def set_mode(self, mode: Literal["transcribe", "translate_en", "translate_target", "translate_zh", "translate"]):
        if mode == "translate":
            mode = "translate_en"
        if mode == "translate_zh":
            mode = "translate_target"
        if mode not in ["transcribe", "translate_en", "translate_target"]:
            raise ValueError("模式必須為 'transcribe'、'translate_en' 或 'translate_target'")
        self.mode = mode

    def set_language(self, language: str):
        self.language = language

    def set_target_language(self, language: str):
        self.target_language = language

    def set_meeting_context(self, meeting_topic: str = "", terminology: dict = None):
        self.meeting_topic = meeting_topic
        self.terminology = terminology or {}
        logger.info("📚 會議主題：%s", meeting_topic)
        if self.terminology:
            logger.info("📖 載入術語詞典：%d 個術語", len(self.terminology))

    # ================================================================
    # 文字提取
    # ================================================================

    def _extract_text(self, response) -> str:
        if isinstance(response, str):
            return response.strip()
        if hasattr(response, "text"):
            return response.text.strip()
        if isinstance(response, dict):
            return response.get("text", "").strip()
        return str(response).strip()

    def _get_source_language_label(self, language: str) -> str:
        return LANGUAGE_LABELS_ZH.get(language, language.upper())

    # ================================================================
    # STT 方法（OpenAI / Groq — 都用 OpenAI SDK）
    # ================================================================

    def _transcribe_source_text(self, audio_file: BytesIO) -> str:
        """以來源語言做逐字稿"""
        response = self.stt_client.audio.transcriptions.create(
            model=self.stt_model,
            file=("audio.wav", audio_file, "audio/wav"),
            language=self.language,
            response_format="text"
        )
        return self._extract_text(response)

    def _translate_audio_to_english(self, audio_file: BytesIO) -> str:
        """將音訊翻譯為英文（Whisper translations endpoint）"""
        response = self.stt_client.audio.translations.create(
            model=self.stt_model,
            file=("audio.wav", audio_file, "audio/wav"),
            response_format="text"
        )
        return self._extract_text(response)

    # ================================================================
    # 翻譯方法（多 Provider）
    # ================================================================

    def _build_translation_prompts(
        self, source_text: str, source_language: str,
        target_language: str, english_text: str = ""
    ) -> tuple[str, str]:
        """構建翻譯 system / user prompt（供 LLM 類 provider 共用）"""
        source_label = self._get_source_language_label(source_language)
        target_label = self._get_source_language_label(target_language)

        system_prompt = f"你是專業的翻譯專家，請將文字翻譯成自然流暢的{target_label}。只返回翻譯結果，不要添加任何解釋或註解。"
        if self.meeting_topic:
            system_prompt += f"\n\n這是一場關於「{self.meeting_topic}」的會議，請使用相關的專業術語。"
        if self.terminology:
            terms_list = "\n".join([f"- {src} → {tgt}" for src, tgt in self.terminology.items()])
            system_prompt += f"\n\nIMPORTANT — Use these exact translations for the following terms:\n{terms_list}"

        if english_text and source_language != "en":
            user_prompt = f"{source_label}原文：{source_text}\n英文參考：{english_text}\n\n請翻譯成{target_label}："
        else:
            user_prompt = f"{source_label}原文：{source_text}\n\n請翻譯成{target_label}："

        if self.previous_texts:
            context = "\n".join(self.previous_texts[-3:])
            user_prompt = f"前文參考：\n{context}\n\n{user_prompt}"

        return system_prompt, user_prompt

    def _translate_with_openai_compatible(
        self, source_text: str, source_language: str,
        target_language: str, english_text: str = ""
    ) -> str:
        """使用 OpenAI 相容 API 翻譯（GPT / Gemini）"""
        system_prompt, user_prompt = self._build_translation_prompts(
            source_text, source_language, target_language, english_text
        )
        response = self.translation_client.chat.completions.create(
            model=self.translation_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    def _translate_with_deepl(
        self, source_text: str, source_language: str,
        target_language: str, **_kwargs
    ) -> str:
        """使用 DeepL REST API 翻譯"""
        from templates import DEEPL_LANGUAGE_MAP

        target_lang_code = DEEPL_LANGUAGE_MAP.get(target_language, target_language.upper())
        source_lang_code = DEEPL_LANGUAGE_MAP.get(source_language, source_language.upper())

        # 構建 request payload
        payload = json.dumps({
            "text": [source_text],
            "target_lang": target_lang_code,
            "source_lang": source_lang_code,
        }).encode("utf-8")

        # 判斷是 Free 還是 Pro（Free key 結尾是 :fx）
        if self.translation_api_key.endswith(":fx"):
            url = "https://api-free.deepl.com/v2/translate"
        else:
            url = "https://api.deepl.com/v2/translate"

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"DeepL-Auth-Key {self.translation_api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        translations = data.get("translations", [])
        if translations:
            return translations[0].get("text", "").strip()
        return ""

    def _translate_with_anthropic(
        self, source_text: str, source_language: str,
        target_language: str, english_text: str = ""
    ) -> str:
        """使用 Anthropic Messages REST API 翻譯"""
        system_prompt, user_prompt = self._build_translation_prompts(
            source_text, source_language, target_language, english_text
        )

        payload = json.dumps({
            "model": self.translation_model,
            "max_tokens": 500,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": self.translation_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content_blocks = data.get("content", [])
        if content_blocks:
            return content_blocks[0].get("text", "").strip()
        return ""

    def translate_to_target_language(
        self,
        source_text: str,
        source_language: str,
        target_language: str,
        english_text: str = ""
    ) -> str:
        """
        翻譯入口 — 依 translation_provider 派發到對應實作

        Args:
            source_text: 原文
            source_language: 原文語言代碼
            target_language: 目標語言代碼
            english_text: 英文參考（可選）

        Returns:
            翻譯結果文字
        """
        try:
            if self.translation_type == "deepl":
                translated = self._translate_with_deepl(
                    source_text, source_language, target_language
                )
            elif self.translation_type == "anthropic":
                translated = self._translate_with_anthropic(
                    source_text, source_language, target_language, english_text
                )
            else:
                # openai_compatible（GPT / Gemini）
                translated = self._translate_with_openai_compatible(
                    source_text, source_language, target_language, english_text
                )

            self.total_translation_calls += 1

            source_label = self._get_source_language_label(source_language)
            target_label = self._get_source_language_label(target_language)

            # 儲存到上下文（DeepL 也保留，給 LLM 切換時能接續）
            self.previous_texts.append(f"{source_label}：{source_text}\n{target_label}：{translated}")
            if len(self.previous_texts) > 10:
                self.previous_texts = self.previous_texts[-10:]

            logger.info("🈯 翻譯完成（%s）：%s → %s",
                        self.translation_provider, source_text[:30], translated[:30])
            return translated

        except Exception as e:
            logger.error("❌ 翻譯失敗（%s）：%s", self.translation_provider, e)
            return f"[翻譯錯誤] {source_text}"

    # ================================================================
    # 主要轉錄流程
    # ================================================================

    def transcribe_audio(self, audio_file: BytesIO, duration: float) -> Optional[Dict]:
        """
        轉錄音訊為文字

        Args:
            audio_file: 音訊檔案（BytesIO 物件）
            duration: 音訊時長（秒）

        Returns:
            結果字典，包含 text、mode、language、duration、latency 等資訊
        """
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                audio_file.seek(0)

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
                            source_text, source_language,
                            self.target_language, english_text
                        )
                    texts[self.target_language] = target_text
                    text = target_text

                latency = time.time() - start_time
                self.total_api_calls += whisper_calls
                self.total_audio_duration += duration

                if not text:
                    return None

                if self.mode == "transcribe":
                    output_language = source_language
                elif self.mode == "translate_en":
                    output_language = "en"
                else:
                    output_language = self.target_language

                return {
                    'text': text,
                    'texts': texts,
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
                logger.warning("API 呼叫失敗（第 %d/%d 次嘗試）：%s",
                               attempt + 1, self.max_retries, error_message)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
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

    # ================================================================
    # 統計
    # ================================================================

    def get_api_cost_estimate(self) -> float:
        return (self.total_audio_duration / 60) * self.API_COST_PER_MINUTE

    def get_stats(self) -> Dict:
        return {
            'total_calls': self.total_api_calls,
            'translation_calls': self.total_translation_calls,
            'failed_calls': self.failed_calls,
            'total_duration': round(self.total_audio_duration, 1),
            'estimated_cost': round(self.get_api_cost_estimate(), 4),
            'mode': self.mode,
            'language': self.language,
            'target_language': self.target_language,
            'stt_provider': self.stt_provider,
            'translation_provider': self.translation_provider,
        }


class TranscriberWorker:
    """語音轉文字背景工作器（在獨立執行緒中執行）"""

    # Circuit breaker 設定
    CB_FAILURE_THRESHOLD = 3
    CB_INITIAL_BACKOFF = 10
    CB_MAX_BACKOFF = 300
    CB_BACKOFF_MULTIPLIER = 2

    def __init__(self, transcriber: Transcriber):
        self.transcriber = transcriber
        self.is_running = False
        self.worker_thread = None
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        # Circuit breaker 狀態
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_reopen_at = 0.0
        self._current_backoff = self.CB_INITIAL_BACKOFF

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
            self.worker_thread = None

    def _record_success(self):
        """API 呼叫成功時重置 circuit breaker"""
        was_degraded = self._consecutive_failures > 0 or self._circuit_open
        self._consecutive_failures = 0
        if self._circuit_open:
            logger.info("🟢 Circuit breaker 已恢復（API 重新正常）")
            self._circuit_open = False
        if was_degraded:
            self._current_backoff = self.CB_INITIAL_BACKOFF

    def _record_failure(self):
        """API 呼叫失敗時更新 circuit breaker 計數"""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.CB_FAILURE_THRESHOLD and not self._circuit_open:
            self._circuit_open = True
            self._circuit_reopen_at = time.time() + self._current_backoff
            logger.warning(
                "🔴 Circuit breaker 觸發！連續 %d 次失敗，暫停 API 呼叫 %ds",
                self._consecutive_failures, self._current_backoff
            )
            self.output_queue.put({
                'success': False,
                'error': f"Circuit breaker: API 連續失敗 {self._consecutive_failures} 次，暫停 {self._current_backoff}s 後自動重試",
                'circuit_breaker': True
            })
            self._current_backoff = min(
                self._current_backoff * self.CB_BACKOFF_MULTIPLIER,
                self.CB_MAX_BACKOFF
            )

    def _is_circuit_open(self) -> bool:
        if not self._circuit_open:
            return False
        if time.time() >= self._circuit_reopen_at:
            logger.info("🟡 Circuit breaker 冷卻結束，嘗試半開放狀態...")
            self._circuit_open = False
            return False
        return True

    def get_circuit_breaker_status(self) -> dict:
        remaining = max(0, self._circuit_reopen_at - time.time()) if self._circuit_open else 0
        return {
            'is_open': self._circuit_open,
            'consecutive_failures': self._consecutive_failures,
            'remaining_seconds': round(remaining, 1),
            'current_backoff': self._current_backoff
        }

    def _worker_loop(self):
        logger.info("🚀 Worker 執行緒已啟動")
        while self.is_running:
            try:
                if self._is_circuit_open():
                    try:
                        self.input_queue.get(timeout=0.5)
                    except queue.Empty:
                        pass
                    continue

                chunk = self.input_queue.get(timeout=0.5)
                logger.debug("📥 Worker 收到音訊片段，準備呼叫 API...")

                result = self.transcriber.transcribe_audio(
                    chunk['audio'], chunk['duration']
                )

                if result:
                    if result.get('success', True):
                        logger.info("✅ API 呼叫成功：%s", result.get('text', '')[:50])
                        self._record_success()
                    else:
                        logger.warning("⚠️ API 呼叫失敗：%s", result.get('error', ''))
                        self._record_failure()
                    result['timestamp'] = chunk['timestamp']
                    self.output_queue.put(result)
                else:
                    logger.debug("⚠️ API 返回空結果")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error("❌ 工作器錯誤：%s", e, exc_info=True)
                self._record_failure()

        logger.info("⏹️ Worker 執行緒已停止")

    def add_audio_chunk(self, audio_chunk: Dict):
        self.input_queue.put(audio_chunk)

    def get_result(self, timeout: Optional[float] = None) -> Optional[Dict]:
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_queue_size(self) -> int:
        return self.input_queue.qsize()
