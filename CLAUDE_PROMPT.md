# Claude Code 開發提示詞：即時會議翻譯 App

> **用途：** 使用此提示詞在 Claude Code 中一次性完整開發本專案
> **版本：** v1.2.0
> **最後更新：** 2026-03-12

---

## 📋 專案概述

開發一個 **Python + Streamlit** 的即時會議翻譯應用程式，專為 macOS 設計，支援從虛擬音訊裝置擷取會議音訊，使用 OpenAI Whisper API 進行語音辨識，並支援多語言翻譯（日語→日語、日語→英文、日語→中文）。

### 核心業務場景

- **使用者：** eFlash IP 設計及半導體製程開發公司
- **需求：** 即時翻譯日語會議為中文，並保留完整錄音和逐字稿
- **特色：** 支援半導體專業術語、會議資訊管理、多語言對照顯示

---

## 🛠 技術棧

### 後端 / 核心

- **Python：** 3.9+（支援 macOS 10.15+ 到最新版本）
- **虛擬環境：** Python venv（必須使用，確保可攜性）
- **主要套件：**
  - `streamlit` >= 1.28.0（UI 框架）
  - `openai` >= 1.3.0（Whisper API + GPT API）
  - `sounddevice` >= 0.4.6（音訊擷取）
  - `numpy` >= 1.24.0（音訊處理）
  - `scipy` >= 1.10.0（信號處理）

### 音訊處理

- **輸入：** BlackHole 2ch 虛擬音訊裝置（或麥克風）
- **格式：** 16kHz, 16bit, mono（Whisper 最佳格式）
- **錄音：** 同步儲存為 WAV 檔案

### AI 服務

- **Whisper API：** 語音辨識（日語→日語、日語→英文）
- **GPT-4o-mini：** 翻譯優化（英文→中文，帶術語詞典和上下文）

---

## 📂 完整檔案結構

```
meeting-translator/
├── .venv/                      # Python 虛擬環境（不納入版控）
├── .gitignore                  # Git 忽略清單
├── README.md                   # 繁體中文完整說明文件
├── CLAUDE_PROMPT.md            # Claude Code 開發提示詞（本文件）
├── requirements.txt            # Python 依賴清單
├── setup.sh                    # 首次安裝腳本（可執行）
├── run_meeting_translator.command  # macOS 雙擊啟動腳本（可執行）
├── check_system.sh             # 系統兼容性檢查腳本（可執行）
├── app.py                      # Streamlit 主程式
├── audio_recorder.py           # 音訊錄製模組
├── transcriber.py              # Whisper API 呼叫模組
├── config_manager.py           # 配置管理模組
├── recordings/                 # 會議錄音存放目錄
│   └── .gitkeep               # 保留目錄結構
└── transcripts/                # 逐字稿存放目錄
    └── .gitkeep               # 保留目錄結構
```

---

## 🎯 完整功能需求

### 1. 音訊擷取

- **來源：** BlackHole 2ch 虛擬音訊裝置（預設）或麥克風
- **自動列舉裝置：** 啟動時列出所有可用音訊輸入裝置
- **切換裝置：** UI 中提供下拉選單切換
- **音訊格式：** 16kHz, 16bit, mono
- **片段長度：** 可調整 3-15 秒（預設 5 秒）
- **靜音偵測：**
  - 使用 RMS（均方根）計算音量
  - 可調整靜音閾值（0-0.1，預設 0.01）
  - 低於閾值的片段跳過，節省 API 費用

### 2. 語音辨識與翻譯

#### 模式一：📝 Transcribe（日語→日語）
- Whisper API transcriptions.create()
- language="ja"
- 返回日語逐字稿

#### 模式二：🌐 Translate（日語→英文）
- **雙語輸出：**
  1. Whisper transcriptions（日語原文）
  2. Whisper translations（英文翻譯）
- 支援多語言對照顯示

#### 模式三：🈯 翻譯（日語→中文）
- **三語輸出：**
  1. Whisper transcriptions（日語原文）
  2. Whisper translations（英文翻譯）
  3. GPT-4o-mini（中文翻譯，帶優化）
- **翻譯優化：**
  - 會議主題上下文
  - 術語詞典強制應用
  - 前文參考（最近 3 句）

### 3. API Key 管理

- **首次輸入：** 側邊欄密碼輸入框
- **本地儲存：** `~/.meeting-translator/config.json`
- **自動載入：** 下次啟動無需重新輸入
- **清除功能：** 側邊欄提供「清除 API Key」按鈕

### 4. 會議資訊管理

#### 會議名稱
- **預設選項：**
  ```json
  [
    "eFlash IP 設計及半導體製程開發公司，每週例會",
    "eFlash IP 設計及半導體製程開發公司，專案進度會議",
    "eFlash IP 設計及半導體製程開發公司，技術討論會"
  ]
  ```
- **新增功能：** 下拉選單 "+ 新增會議名稱" → 輸入框 → 添加按鈕
- **自動儲存：** `~/.meeting-translator/meeting_config.json`

#### 會議主題/類型
- **預設選項：**
  ```json
  [
    "專案管理",
    "技術開發",
    "半導體製程開發、IC設計、故障分析"
  ]
  ```
- **新增功能：** 同上
- **用途：** 提供給 GPT 作為翻譯上下文

### 5. 術語詞典（專有名詞管理）

#### 資料結構
```json
{
  "terms": {
    "wafer": "晶圓",
    "yield": "良率",
    "defect": "缺陷",
    "failure analysis": "故障分析",
    "eFlash": "嵌入式快閃記憶體",
    "IP": "智慧財產權",
    "tape-out": "定案送廠",
    "foundry": "晶圓代工廠"
  }
}
```

#### 預設術語（30+ 個半導體相關）
```
wafer, process, yield, defect, failure analysis, semiconductor,
eFlash, IP, design, fabrication, foundry, tape-out, mask,
lithography, etching, deposition, doping, annealing, die,
package, testing, reliability, qualification, specification,
milestone, schedule, deliverable, root cause, action item, follow-up
```

#### UI 管理
- **位置：** 側邊欄展開式面板「📖 術語詞典管理」
- **顯示：** 列表顯示所有術語，每行附「🗑️ 刪除」按鈕
- **新增：** 兩欄輸入框（原文｜中文），「➕ 添加術語」按鈕
- **說明：** 提示使用「英文→中文」對照（因翻譯流程：日語→英文→中文）

#### 應用方式
- 在 GPT prompt 中加入術語對照表
- 強制 GPT 使用指定翻譯
- 確保專業術語翻譯一致性

### 6. 翻譯準確性優化

#### A. 會議主題上下文
```python
system_prompt += f"\n這是一場關於「{meeting_topic}」的會議，請使用相關的專業術語。"
```

#### B. 術語詞典強制應用
```python
terms_list = "\n".join([f"- {en} → {zh}" for en, zh in terminology.items()])
system_prompt += f"\n請特別注意以下專有名詞的翻譯：\n{terms_list}"
```

#### C. 上下文記憶
```python
# 保留最近 10 句翻譯
previous_texts = ["日：...  中：...", ...]
# 在 prompt 中提供前 3 句作為參考
context = "\n".join(previous_texts[-3:])
```

#### D. 同時提供日文和英文
```python
user_prompt = f"日語原文：{japanese_text}\n英文翻譯：{english_text}\n\n請翻譯成繁體中文："
```

### 7. 多語言對照顯示

#### UI 控制
- **位置：** 側邊欄「顯示設定」
- **選項：** Checkbox「顯示多語言對照」（預設勾選）

#### 顯示格式

**Transcribe 模式：**
```
[18:30:45] (延遲：1.8秒)
📝 原文：皆さん、こんにちは
```

**Translate 模式：**
```
[18:30:45] (延遲：2.1秒)
📝 日語：皆さん、こんにちは
🌐 英文：Hello everyone
```

**翻譯（中文）模式：**
```
[18:30:45] (延遲：3.2秒)
📝 日語：皆さん、こんにちは
🌐 英文：Hello everyone
🈯 中文：大家好
```

### 8. 檔案命名規則

#### 錄音檔案
```
格式：{會議名稱}_{會議主題}_{時間戳}.wav
範例：eFlash IP 設計及半導體製程開發公司，每週例會_專案管理_20260312_143022.wav
```

#### 逐字稿檔案
```
格式：transcript_{會議名稱}_{會議主題}_{時間戳}.txt
範例：transcript_eFlash IP 設計及半導體製程開發公司，每週例會_專案管理_20260312_143022.txt
```

### 9. 即時顯示

- **主畫面：** 最新的辨識結果在最上方（倒序顯示）
- **時間戳記：** `[HH:MM:SS]`
- **延遲顯示：** 每段顯示處理延遲時間
- **背景色區分：**
  - 日語：淡藍色 `#E3F2FD`
  - 英文：淡綠色 `#E8F5E9`
  - 中文：淡橙色 `#FFF3E0`

### 10. 會議錄音備份

- **自動儲存：** 錄音開始時同步寫入 WAV 檔
- **路徑：** `recordings/`
- **格式：** WAV, 16kHz, 16bit, mono
- **停止儲存：** 點擊「停止」時自動關閉檔案
- **下載：** 停止後提供下載按鈕

### 11. 逐字稿匯出

- **格式：** TXT 純文字
- **內容：**
  ```
  ============================================================
  會議逐字稿
  產生時間：2026-03-12 14:30:22
  ============================================================

  [14:30:45]
  皆さん、こんにちは
  (延遲：1.8秒，模式：transcribe)
  ------------------------------------------------------------
  ```
- **下載：** Streamlit download_button

### 12. UI 設計

#### 側邊欄（由上到下）
```
📋 會議資訊
  - 會議名稱（下拉選單）
  - 會議主題/類型（下拉選單）

🔑 OpenAI API Key
  - 輸入框（密碼模式）
  - [💾 儲存] [🗑️ 清除]

🔊 音訊設定
  - 音訊輸入裝置（下拉選單）
  - 音訊片段長度（滑桿 3-15秒）
  - 靜音閾值（滑桿 0-0.1）

🎨 處理模式
  - [📝 Transcribe] [🌐 Translate] [🈯 翻譯]（單選）
  - 音訊語言（下拉選單，翻譯模式下禁用）

📺 顯示設定
  - [✓] 顯示多語言對照

📊 錄音狀態（錄音中顯示）
  - 錄音時長
  - 檔案大小
  - 已處理片段
  - Whisper API 呼叫次數
  - GPT 翻譯次數（中文模式）
  - API 費用估算
  - 待處理佇列
  - Worker 狀態

⚠️ 錯誤訊息（有錯誤時顯示）

🔍 調試日誌（可展開）

📖 術語詞典管理（可展開）
```

#### 主畫面（由上到下）
```
標題：🎙️ 即時會議翻譯

控制按鈕：
  [🎙️ 開始錄音] [⏸️ 暫停/▶️ 繼續] [⏹️ 停止]

狀態指示：
  🔴 錄音中 / ⏸️ 已暫停 / ⚫ 已停止

即時辨識結果：
  （最新的在最上方，卡片式顯示）

下載按鈕（停止後顯示）：
  [📥 下載逐字稿] [📥 下載錄音]
```

### 13. 多執行緒架構

#### ProcessingController 類別
```python
class ProcessingController:
    def __init__(self, recorder, worker):
        self.recorder = recorder        # AudioRecorder 實例
        self.worker = worker            # TranscriberWorker 實例
        self.transcripts = []           # 辨識結果列表
        self.error_messages = []        # 錯誤訊息列表

    def _processing_loop(self):
        # 在獨立執行緒中執行
        while not self.stop_flag:
            # 從 recorder 取得音訊片段
            chunk = self.recorder.get_next_chunk()
            # 提交給 worker
            self.worker.add_audio_chunk(chunk)
            # 從 worker 取得結果
            result = self.worker.get_result()
            # 添加到 transcripts
            self.transcripts.append(result)
```

#### 執行緒安全
- **避免直接訪問 st.session_state**（子執行緒中會失敗）
- **使用獨立的資料結構**（transcripts, error_messages）
- **主執行緒讀取**（UI 從 controller.transcripts 讀取）

### 14. 錯誤處理

- **API Key 無效：** 友善錯誤訊息
- **音訊裝置無法開啟：** 提示檢查 BlackHole
- **API 呼叫失敗：** 自動重試 3 次，失敗後跳過片段
- **網路斷線：** 暫停 API 呼叫，持續錄音
- **所有錯誤：** 顯示在側邊欄「⚠️ 錯誤訊息」區域

---

## 📝 詳細模組規格

### 1. config_manager.py

#### 功能
- 管理 OpenAI API Key
- 管理會議配置（meeting_config.json）
- 管理術語詞典（terminology.json）

#### 關鍵方法
```python
class ConfigManager:
    def get_api_key() -> Optional[str]
    def save_api_key(api_key: str) -> bool
    def clear_api_key() -> bool

    def get_meeting_config() -> Dict
    def add_meeting_name(name: str) -> bool
    def add_meeting_topic(topic: str) -> bool

    def get_terminology() -> Dict[str, str]
    def add_term(source: str, target: str) -> bool
    def delete_term(source: str) -> bool
```

#### 配置檔案位置
```
~/.meeting-translator/
├── config.json           # {"openai_api_key": "sk-..."}
├── meeting_config.json   # {"meeting_names": [...], "meeting_topics": [...]}
└── terminology.json      # {"terms": {"wafer": "晶圓", ...}}
```

### 2. audio_recorder.py

#### 功能
- 從音訊裝置擷取即時音訊
- 儲存為 WAV 檔案
- 分段處理（預設 5 秒）
- 靜音偵測

#### 關鍵方法
```python
class AudioRecorder:
    @staticmethod
    def list_audio_devices() -> List[Dict]  # 列出所有輸入裝置

    def set_device(device_index=None, device_name=None)
    def set_chunk_duration(duration: float)
    def set_silence_threshold(threshold: float)

    def start_recording(output_dir="recordings",
                       meeting_name="",
                       meeting_topic="") -> str  # 返回檔案路徑

    def pause_recording()
    def resume_recording()
    def stop_recording()

    def get_next_chunk(timeout=None) -> Optional[Dict]  # 返回音訊片段
    def get_recording_stats() -> Dict  # 統計資訊
```

#### 音訊佇列
```python
self.audio_queue = queue.Queue()  # 儲存待處理的音訊片段

# 音訊片段格式
{
    'audio': BytesIO,        # WAV 格式音訊
    'timestamp': datetime,   # 時間戳記
    'duration': float        # 時長（秒）
}
```

### 3. transcriber.py

#### 功能
- 呼叫 Whisper API 進行語音辨識
- 呼叫 GPT API 進行翻譯優化
- 管理術語詞典和上下文

#### 關鍵類別

##### Transcriber
```python
class Transcriber:
    def set_mode(mode: Literal["transcribe", "translate", "translate_zh"])
    def set_language(language: str)
    def set_meeting_context(meeting_topic="", terminology={})

    def transcribe_audio(audio_file: BytesIO,
                        duration: float) -> Optional[Dict]
        # 返回格式：
        {
            'text': str,              # 主要文字
            'texts': {                # 所有語言版本
                'ja': str,           # 日語原文
                'en': str,           # 英文翻譯
                'zh': str            # 中文翻譯
            },
            'mode': str,
            'language': str,
            'duration': float,
            'latency': float,
            'success': bool
        }

    def translate_to_chinese(japanese_text: str,
                            english_text="") -> str
        # 帶術語詞典、上下文、會議主題的優化翻譯

    def get_stats() -> Dict
```

##### TranscriberWorker
```python
class TranscriberWorker:
    def start()  # 啟動背景工作器
    def stop()   # 停止背景工作器

    def add_audio_chunk(chunk: Dict)  # 添加到處理佇列
    def get_result(timeout=None) -> Optional[Dict]  # 取得結果
    def get_queue_size() -> int  # 待處理數量
```

### 4. app.py

#### 主要架構
```python
# ProcessingController 類別（避免執行緒安全問題）
class ProcessingController:
    def __init__(recorder, worker)
    def start()
    def stop()
    def pause()
    def resume()
    def _processing_loop()  # 背景執行緒主迴圈

# Streamlit 主程式
def init_session_state()  # 初始化 session state
def start_recording()     # 開始錄音
def pause_recording()     # 暫停錄音
def resume_recording()    # 恢復錄音
def stop_recording()      # 停止錄音
def save_transcript_to_file(transcripts, meeting_name, meeting_topic) -> str
def main()                # 主程式
```

---

## 🔧 安裝腳本規格

### setup.sh

```bash
#!/bin/bash
set -e

# 1. 檢查 Homebrew（未安裝則顯示安裝指令）
# 2. 檢查 Python 3（未安裝則 brew install python@3.9）
# 3. 檢查 portaudio（未安裝則 brew install portaudio）
# 4. 建立虛擬環境（.venv）
# 5. 升級 pip
# 6. 安裝依賴（pip install -r requirements.txt）
# 7. 建立目錄（recordings/, transcripts/）
# 8. 設定執行權限（chmod +x run_meeting_translator.command）
# 9. 顯示完成訊息和下一步指引
```

### run_meeting_translator.command

```bash
#!/bin/bash

# 取得腳本所在目錄
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# 檢查 Python 3
# 如果 .venv 不存在，自動建立並安裝依賴
# 如果 requirements.txt 更新，自動同步
# 建立必要目錄
# 啟動：exec .venv/bin/streamlit run app.py --server.headless true --server.port 8501
```

### check_system.sh

```bash
#!/bin/bash
set -e

# 顯示系統資訊（macOS 版本、處理器架構）
# 檢測晶片類型（Intel / Apple Silicon）
# 檢查系統版本（>= 10.15）
# 檢查 Homebrew
# 檢查 Python 3.9+
# 檢查 portaudio
# 檢查 BlackHole（警告，非必需）
# 檢查虛擬環境和依賴
# Apple Silicon 特殊提示
# 顯示下一步建議
```

---

## 🌐 跨平台兼容性要求

### 支援的系統

1. **macOS 10.15.8 (Catalina) - Intel**
   - Python 3.9+
   - 完整測試通過

2. **macOS 12.7.6 (Monterey) - Intel**
   - Python 3.9+
   - 完整測試通過

3. **macOS 14/15 (Sonoma/Sequoia) - Apple Silicon (M1/M2/M3)**
   - Python 3.9+（原生 ARM64）
   - 所有套件原生支援，無需 Rosetta 2

### 兼容性策略

- **最低系統：** macOS 10.15 (Catalina)
- **Python 版本：** 3.9-3.12（避免使用 3.13+ 的新特性）
- **架構支援：** x86_64（Intel）和 arm64（Apple Silicon）原生支援
- **依賴安裝：** 所有套件均有 macOS wheel 檔案，無需編譯
- **測試：** 提供 check_system.sh 在所有平台自動檢測

---

## 📦 requirements.txt

```txt
streamlit>=1.28.0
openai>=1.3.0
sounddevice>=0.4.6
numpy>=1.24.0
scipy>=1.10.0
```

---

## 🎨 CSS 樣式

```css
.japanese-text {
    background-color: #E3F2FD;  /* 淡藍色 */
}
.english-text {
    background-color: #E8F5E9;  /* 淡綠色 */
}
.chinese-text {
    background-color: #FFF3E0;  /* 淡橙色 */
}
.status-recording {
    color: #ff0000;
    animation: blink 1s infinite;  /* 閃爍效果 */
}
.status-paused {
    color: #ff9800;
}
.status-stopped {
    color: #999;
}
```

---

## 💰 費用估算

### Whisper API
- $0.006 / 分鐘

### GPT-4o-mini
- Input: $0.15 / 1M tokens
- Output: $0.6 / 1M tokens
- 預估：每分鐘約 $0.001

### 總計
| 模式 | 30分鐘 | 1小時 | 2小時 |
|-----|--------|-------|-------|
| Transcribe / Translate | $0.18 | $0.36 | $0.72 |
| 翻譯（中文） | $0.21 | $0.42 | $0.84 |

---

## 🔍 調試功能

### Debug Logs
- 記錄所有關鍵操作
- 側邊欄可展開查看
- 輸出到 Terminal 和 UI

### 關鍵日誌點
```
🎬 開始初始化錄音...
✅ 錄音器已初始化
🔊 設定音訊裝置：BlackHole 2ch
🤖 正在初始化 Whisper API...
📚 會議主題：半導體製程開發、IC設計、故障分析
📖 載入術語詞典：30 個術語
🔄 處理迴圈已啟動
🎵 收到音訊片段（5秒）
📥 Worker 收到音訊片段，準備呼叫 API...
🈯 翻譯完成：ウェーハの良率... → 晶圓的良率...
✅ 辨識完成：晶圓的良率已達到 95%
```

---

## 📚 README.md 要求

必須包含以下章節（繁體中文）：

1. 專案簡介
2. 系統需求（詳細列出三台 Mac 的兼容性）
3. 快速安裝（方法一：自動、方法二：手動）
4. 移植到其他 Mac 的完整步驟
5. 音訊路由設定（圖文說明 BlackHole 設定）
6. OpenAI API Key 取得方式
7. 使用方式（詳細操作說明）
8. 功能特色（雙語顯示、會議管理、術語詞典）
9. 費用估算表
10. 常見問題 FAQ（至少 10 個）
11. 專案結構說明
12. 更新日誌

---

## 🚀 開發檢查清單

### 必須實現的功能

- [ ] 三種翻譯模式（Transcribe / Translate / 翻譯中文）
- [ ] 多語言對照顯示（可開關）
- [ ] 會議名稱和主題管理（預設半導體公司）
- [ ] 術語詞典（預設 30+ 半導體術語）
- [ ] 翻譯優化（上下文、主題、術語）
- [ ] 檔案命名（包含會議名稱、主題、時間）
- [ ] 多執行緒架構（ProcessingController）
- [ ] 錯誤處理和調試日誌
- [ ] 跨平台兼容性（Intel + Apple Silicon）
- [ ] 虛擬環境隔離
- [ ] 自動安裝腳本
- [ ] 系統檢查腳本
- [ ] 完整繁體中文 README
- [ ] .gitignore（排除 .venv、錄音、逐字稿）

### 必須創建的檔案

- [ ] app.py
- [ ] audio_recorder.py
- [ ] transcriber.py
- [ ] config_manager.py
- [ ] requirements.txt
- [ ] setup.sh（可執行）
- [ ] run_meeting_translator.command（可執行）
- [ ] check_system.sh（可執行）
- [ ] .gitignore
- [ ] README.md（繁體中文）
- [ ] CLAUDE_PROMPT.md（本文件）
- [ ] recordings/.gitkeep
- [ ] transcripts/.gitkeep

---

## 🎯 一次到位的關鍵點

### 1. 不要遺漏的功能

✅ **雙語/多語言對照顯示**（這是核心特色）
✅ **術語詞典**（英文→中文，預設半導體術語）
✅ **會議管理**（名稱、主題、自動檔名）
✅ **翻譯優化**（上下文、主題、術語強制）
✅ **ProcessingController**（避免執行緒安全問題）

### 2. 配置檔案位置

```
~/.meeting-translator/
├── config.json           # API Key
├── meeting_config.json   # 會議配置
└── terminology.json      # 術語詞典
```

### 3. 預設值

**會議名稱：**
```
eFlash IP 設計及半導體製程開發公司，每週例會
eFlash IP 設計及半導體製程開發公司，專案進度會議
eFlash IP 設計及半導體製程開發公司，技術討論會
```

**會議主題：**
```
專案管理
技術開發
半導體製程開發、IC設計、故障分析
```

**術語詞典：** 30+ 半導體相關術語（見上文）

### 4. 繁體中文

- 所有 UI 文字
- 所有程式碼註解
- README.md
- 錯誤訊息
- 調試日誌

---

## 📄 授權

MIT License（或根據專案需求調整）

---

## 🔗 相關資源

- OpenAI Whisper API: https://platform.openai.com/docs/guides/speech-to-text
- OpenAI GPT API: https://platform.openai.com/docs/guides/text-generation
- Streamlit 文檔: https://docs.streamlit.io/
- BlackHole 下載: https://existential.audio/blackhole/

---

**✨ 使用此提示詞，Claude Code 應該能夠一次性完整開發出與當前專案完全相同的應用程式。**
