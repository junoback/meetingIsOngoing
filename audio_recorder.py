#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音訊錄製模組 - 負責從音訊裝置擷取即時音訊並儲存
"""

import sounddevice as sd
import numpy as np
import wave
import threading
import queue
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO
from typing import Optional, List, Dict, Callable


class AudioRecorder:
    """音訊錄製器類別"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        初始化音訊錄製器

        Args:
            sample_rate: 取樣率（Hz），預設 16000（Whisper API 最佳）
            channels: 聲道數，預設 1（單聲道）
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = 5  # 預設每 5 秒為一個片段
        self.silence_threshold = 0.01  # 靜音閾值
        self.device_index = None  # 音訊裝置索引
        self.device_name = None  # 音訊裝置名稱

        # 錄音狀態
        self.is_recording = False
        self.is_paused = False
        self.stream = None
        self.recording_thread = None

        # 音訊緩衝區
        self.audio_buffer = []
        self.audio_queue = queue.Queue()  # 儲存待處理的音訊片段

        # WAV 檔案錄音
        self.wav_file = None
        self.wav_writer = None
        self.recording_file_path = None

        # 統計資訊
        self.total_duration = 0  # 總錄音時長（秒）
        self.chunks_processed = 0  # 已處理片段數
        self.recording_start_time = None

    @staticmethod
    def list_audio_devices() -> List[Dict]:
        """
        列出所有可用的音訊輸入裝置

        Returns:
            裝置列表，每個元素包含 index、name、channels 等資訊
        """
        devices = []
        device_list = sd.query_devices()

        for i, device in enumerate(device_list):
            # 只列出輸入裝置
            if device['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })

        return devices

    @staticmethod
    def find_device_by_name(name: str) -> Optional[int]:
        """
        根據裝置名稱尋找裝置索引

        Args:
            name: 裝置名稱（支援部分匹配）

        Returns:
            裝置索引，如果找不到則返回 None
        """
        devices = AudioRecorder.list_audio_devices()
        for device in devices:
            if name.lower() in device['name'].lower():
                return device['index']
        return None

    def set_device(self, device_index: Optional[int] = None, device_name: Optional[str] = None):
        """
        設定音訊輸入裝置

        Args:
            device_index: 裝置索引
            device_name: 裝置名稱（如果提供，會覆蓋 device_index）
        """
        if device_name:
            device_index = self.find_device_by_name(device_name)
            if device_index is None:
                raise ValueError(f"找不到裝置：{device_name}")

        self.device_index = device_index
        if device_index is not None:
            devices = self.list_audio_devices()
            for device in devices:
                if device['index'] == device_index:
                    self.device_name = device['name']
                    break

    def set_chunk_duration(self, duration: float):
        """
        設定音訊片段長度

        Args:
            duration: 片段長度（秒）
        """
        self.chunk_duration = max(1, min(duration, 30))  # 限制在 1-30 秒之間

    def set_silence_threshold(self, threshold: float):
        """
        設定靜音閾值

        Args:
            threshold: 閾值（0-1 之間）
        """
        self.silence_threshold = max(0, min(threshold, 1))

    def _is_silent(self, audio_data: np.ndarray) -> bool:
        """
        檢測音訊片段是否為靜音

        Args:
            audio_data: 音訊資料（NumPy 陣列）

        Returns:
            True 表示靜音，False 表示有聲音
        """
        # 計算 RMS（均方根）音量
        rms = np.sqrt(np.mean(audio_data ** 2))
        return rms < self.silence_threshold

    def _audio_callback(self, indata, frames, time_info, status):
        """
        音訊串流回調函數（sounddevice 使用）

        Args:
            indata: 輸入的音訊資料
            frames: 幀數
            time_info: 時間資訊
            status: 狀態資訊
        """
        if status:
            print(f"音訊串流狀態：{status}")

        if not self.is_paused:
            # 將音訊資料添加到緩衝區
            self.audio_buffer.append(indata.copy())

    def _recording_loop(self):
        """錄音主迴圈（在獨立執行緒中執行）"""
        samples_per_chunk = int(self.sample_rate * self.chunk_duration)

        while self.is_recording:
            if self.is_paused:
                time.sleep(0.1)
                continue

            # 計算目前緩衝區的總樣本數
            total_samples = sum(len(chunk) for chunk in self.audio_buffer)

            if total_samples >= samples_per_chunk:
                # 取出足夠的音訊資料
                chunk_data = []
                remaining_samples = samples_per_chunk

                while remaining_samples > 0 and self.audio_buffer:
                    data = self.audio_buffer.pop(0)
                    if len(data) <= remaining_samples:
                        chunk_data.append(data)
                        remaining_samples -= len(data)
                    else:
                        # 分割資料
                        chunk_data.append(data[:remaining_samples])
                        self.audio_buffer.insert(0, data[remaining_samples:])
                        remaining_samples = 0

                # 合併音訊資料
                audio_chunk = np.concatenate(chunk_data, axis=0)

                # 寫入 WAV 檔案
                if self.wav_writer:
                    self.wav_writer.writeframes((audio_chunk * 32767).astype(np.int16).tobytes())

                # 檢測是否為靜音
                rms = np.sqrt(np.mean(audio_chunk ** 2))
                is_silent = self._is_silent(audio_chunk)

                print(f"🔊 音訊片段 RMS: {rms:.6f}, 靜音閾值: {self.silence_threshold:.6f}, 靜音: {is_silent}")

                if not is_silent:
                    # 將音訊片段放入佇列（轉為 BytesIO）
                    audio_bytes = self._numpy_to_wav_bytes(audio_chunk)
                    self.audio_queue.put({
                        'audio': audio_bytes,
                        'timestamp': datetime.now(),
                        'duration': self.chunk_duration
                    })
                    self.chunks_processed += 1
                    print(f"✅ 音訊片段已加入佇列（總計：{self.chunks_processed}）")
                else:
                    print(f"⏭️ 音訊片段因靜音被跳過")

                # 更新總時長
                self.total_duration += self.chunk_duration

            else:
                time.sleep(0.1)

    def _numpy_to_wav_bytes(self, audio_data: np.ndarray) -> BytesIO:
        """
        將 NumPy 陣列轉換為 WAV 格式的 BytesIO

        Args:
            audio_data: 音訊資料（NumPy 陣列）

        Returns:
            WAV 格式的 BytesIO 物件
        """
        audio_bytes = BytesIO()
        with wave.open(audio_bytes, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
        audio_bytes.seek(0)
        return audio_bytes

    def start_recording(self, output_dir: str = "recordings", meeting_name: str = "", meeting_topic: str = "") -> str:
        """
        開始錄音

        Args:
            output_dir: 錄音檔案輸出目錄
            meeting_name: 會議名稱
            meeting_topic: 會議主題

        Returns:
            錄音檔案路徑
        """
        if self.is_recording:
            raise RuntimeError("錄音已在進行中")

        # 建立輸出目錄
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 產生錄音檔案名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 構建檔案名稱
        filename_parts = []
        if meeting_name:
            # 清理檔案名稱中的特殊字元
            safe_meeting_name = meeting_name.replace("/", "-").replace("\\", "-").replace(":", "-")
            filename_parts.append(safe_meeting_name)
        if meeting_topic:
            safe_meeting_topic = meeting_topic.replace("/", "-").replace("\\", "-").replace(":", "-")
            filename_parts.append(safe_meeting_topic)
        filename_parts.append(timestamp)

        filename = "_".join(filename_parts) + ".wav"
        self.recording_file_path = output_path / filename

        # 開啟 WAV 檔案
        self.wav_file = wave.open(str(self.recording_file_path), 'wb')
        self.wav_file.setnchannels(self.channels)
        self.wav_file.setsampwidth(2)  # 16-bit
        self.wav_file.setframerate(self.sample_rate)
        self.wav_writer = self.wav_file

        # 重置統計資訊
        self.total_duration = 0
        self.chunks_processed = 0
        self.recording_start_time = time.time()
        self.audio_buffer.clear()

        # 清空佇列
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # 開始音訊串流
        self.is_recording = True
        self.is_paused = False
        self.stream = sd.InputStream(
            device=self.device_index,
            channels=self.channels,
            samplerate=self.sample_rate,
            callback=self._audio_callback
        )
        self.stream.start()

        # 啟動錄音執行緒
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()

        return str(self.recording_file_path)

    def pause_recording(self):
        """暫停錄音"""
        if not self.is_recording:
            raise RuntimeError("錄音未在進行中")
        self.is_paused = True

    def resume_recording(self):
        """恢復錄音"""
        if not self.is_recording:
            raise RuntimeError("錄音未在進行中")
        self.is_paused = False

    def stop_recording(self):
        """停止錄音"""
        if not self.is_recording:
            return

        self.is_recording = False

        # 停止音訊串流
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        # 等待錄音執行緒結束
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
            self.recording_thread = None

        # 關閉 WAV 檔案
        if self.wav_writer:
            self.wav_writer.close()
            self.wav_writer = None
        if self.wav_file:
            self.wav_file = None

    def get_next_chunk(self, timeout: Optional[float] = None) -> Optional[Dict]:
        """
        取得下一個音訊片段

        Args:
            timeout: 超時時間（秒），None 表示不等待

        Returns:
            音訊片段字典，包含 audio（BytesIO）、timestamp、duration
            如果佇列為空且 timeout 為 None，返回 None
        """
        try:
            queue_size = self.audio_queue.qsize()
            if queue_size > 0:
                print(f"📦 get_next_chunk() 被呼叫，佇列中有 {queue_size} 個音訊片段")
            chunk = self.audio_queue.get(timeout=timeout)
            print(f"✅ get_next_chunk() 成功取得音訊片段")
            return chunk
        except queue.Empty:
            return None

    def get_recording_stats(self) -> Dict:
        """
        取得錄音統計資訊

        Returns:
            統計資訊字典
        """
        file_size = 0
        if self.recording_file_path and Path(self.recording_file_path).exists():
            file_size = Path(self.recording_file_path).stat().st_size

        return {
            'duration': self.total_duration,
            'file_size': file_size,
            'chunks_processed': self.chunks_processed,
            'is_recording': self.is_recording,
            'is_paused': self.is_paused,
            'file_path': str(self.recording_file_path) if self.recording_file_path else None
        }
