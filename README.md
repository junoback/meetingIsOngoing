# 🎙️ 即時會議翻譯 App

使用 OpenAI Whisper API 即時將會議中的日語翻譯為英文或轉錄為日語文字。

---

## 📋 目錄

- [專案簡介](#專案簡介)
- [系統需求](#系統需求)
- [快速安裝](#快速安裝)
- [移植到其他 Mac](#移植到其他-mac)
- [音訊路由設定](#音訊路由設定)
- [OpenAI API Key 取得](#openai-api-key-取得)
- [使用方式](#使用方式)
- [費用估算](#費用估算)
- [常見問題 FAQ](#常見問題-faq)
- [專案結構](#專案結構)

---

## 專案簡介

這是一個基於 Python + Streamlit 的即時會議翻譯應用程式，專為 macOS 設計。透過虛擬音訊裝置（BlackHole 2ch）擷取系統音訊，使用 OpenAI Whisper API 進行即時語音辨識和翻譯。

### 主要功能

- ✅ 即時擷取會議音訊（支援 Zoom、Google Meet、Teams 等）
- ✅ 三種模式：
  - **📝 Transcribe**（日語→日語逐字稿）
  - **🌐 Translate**（日語→英文翻譯）
  - **🈯 翻譯**（日語→中文翻譯）
- ✅ 即時顯示辨識結果（最新的在最上方）
- ✅ 自動錄音備份（WAV 格式）
- ✅ 逐字稿匯出（TXT 格式）
- ✅ 靜音偵測（節省 API 費用）
- ✅ 多執行緒架構（不阻塞 UI）
- ✅ 虛擬環境隔離（可攜性高）

---

## 系統需求

### 硬體需求
- macOS 10.15 (Catalina) 或更新版本
- Intel 或 Apple Silicon Mac

### 軟體需求
- **Homebrew**（macOS 套件管理器）
- **Python 3.9** 或以上版本
- **portaudio**（音訊處理函式庫）
- **BlackHole 2ch**（虛擬音訊裝置）
- **OpenAI API Key**

---

## 快速安裝

### 方法一：全自動安裝（推薦）

1. 下載或複製專案資料夾到你的 Mac
2. 雙擊 `run_meeting_translator.command`
3. 首次執行會自動：
   - 建立 Python 虛擬環境（`.venv/`）
   - 安裝所有依賴套件
   - 啟動 Streamlit App
4. 瀏覽器會自動開啟 App 頁面

### 方法二：手動安裝

```bash
# 1. 開啟 Terminal，進入專案目錄
cd ~/meeting-translator

# 2. 執行安裝腳本
bash setup.sh

# 3. 啟動 App
.venv/bin/streamlit run app.py
```

### 前置準備

在使用之前，請確認已安裝以下軟體：

#### 1. 安裝 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. 安裝 Python 3 和 portaudio

```bash
brew install python@3.9
brew install portaudio
```

#### 3. 安裝 BlackHole 2ch

下載並安裝：[https://existential.audio/blackhole/](https://existential.audio/blackhole/)

選擇 **BlackHole 2ch** 版本（最輕量）

---

## 移植到其他 Mac

本專案使用 Python 虛擬環境，移植非常簡單：

### 步驟

```bash
# 在原始 Mac 上（複製時排除虛擬環境和產出檔案）
rsync -av --exclude='.venv' --exclude='recordings/*' --exclude='transcripts/*' \
  ~/meeting-translator/ /Volumes/USB/meeting-translator/

# 或直接壓縮（手動排除 .venv、recordings、transcripts）
zip -r meeting-translator.zip meeting-translator/ -x "*.venv/*" "*/recordings/*" "*/transcripts/*"
```

### 在目標 Mac 上

1. 複製專案資料夾到目標 Mac
2. 確認目標 Mac 已安裝：
   - Homebrew
   - Python 3.9+
   - portaudio（`brew install portaudio`）
   - BlackHole 2ch
3. 雙擊 `run_meeting_translator.command`
4. 首次執行會自動建立虛擬環境並安裝依賴（約 1-2 分鐘）
5. 完成！

---

## 音訊路由設定

為了讓 App 能擷取會議音訊，需要設定「多重輸出裝置」。

### 步驟圖解

#### 1. 安裝 BlackHole 2ch

下載並安裝：[https://existential.audio/blackhole/](https://existential.audio/blackhole/)

#### 2. 開啟「音訊 MIDI 設定」

方法一：Spotlight 搜尋「Audio MIDI Setup」
方法二：`應用程式 > 工具程式 > 音訊 MIDI 設定`

#### 3. 建立多重輸出裝置

1. 點擊左下角的 `+` 號
2. 選擇「建立多重輸出裝置」
3. 勾選：
   - ✅ **內建輸出**（或你的喇叭）
   - ✅ **BlackHole 2ch**
4. 重新命名為「會議輸出」（可選）

#### 4. 設定系統音訊輸出

1. 開啟「系統偏好設定 > 聲音 > 輸出」
2. 選擇剛才建立的「會議輸出」（或「多重輸出裝置」）

### 音訊流程圖

```
會議軟體（Zoom/Meet）
    ↓
系統音訊輸出（多重輸出裝置）
    ↓
    ├─→ 內建輸出（喇叭） → 你聽到聲音
    └─→ BlackHole 2ch → App 擷取 → Whisper API → 翻譯文字
                                  → 錄音備份（WAV）
```

---

## OpenAI API Key 取得

### 步驟

1. 前往 OpenAI 官網：[https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. 登入你的 OpenAI 帳號（需要先註冊）
3. 點擊「Create new secret key」
4. 複製 API Key（格式：`sk-proj-...`）
5. 在 App 側邊欄輸入 API Key 並點擊「💾 儲存」

### 注意事項

- API Key 會儲存在 `~/.meeting-translator/config.json`
- 下次啟動 App 會自動載入
- 請妥善保管你的 API Key，不要分享給他人
- 首次使用需綁定信用卡並儲值（最低 $5 USD）

---

## 使用方式

### 1. 啟動 App

雙擊 `run_meeting_translator.command` 或執行：

```bash
.venv/bin/streamlit run app.py
```

瀏覽器會自動開啟 `http://localhost:8501`

### 2. 設定參數（側邊欄）

#### OpenAI API Key
- 首次使用時輸入 API Key
- 點擊「💾 儲存」

#### 音訊設定
- **音訊輸入裝置**：選擇「BlackHole 2ch」
- **音訊片段長度**：建議 5 秒（可調整 3-15 秒）
- **靜音閾值**：預設 0.010（音量低於此值會跳過）

#### 處理模式
- **📝 Transcribe**：日語 → 日語逐字稿
- **🌐 Translate**：日語 → 英文翻譯（Whisper API 內建）
- **🈯 翻譯**：日語 → 中文翻譯（Whisper + GPT-4o-mini）

#### 音訊語言
- 預設選擇「日語」
- 也支援其他語言（英語、中文、韓語等）
- 注意：翻譯模式下語言選項無效

### 3. 開始錄音

1. 開啟你的會議軟體（Zoom、Google Meet 等）
2. 確認系統音訊輸出為「多重輸出裝置」
3. 點擊 App 中的「🎙️ 開始錄音」
4. 即時辨識結果會顯示在主畫面

### 4. 控制錄音

- **⏸️ 暫停**：暫停錄音和辨識（音訊不會寫入檔案）
- **▶️ 繼續**：恢復錄音
- **⏹️ 停止**：停止錄音並顯示下載按鈕

### 5. 下載結果

停止錄音後，可以下載：

- **📥 下載逐字稿**：TXT 格式，包含時間戳記和延遲資訊
- **📥 下載錄音**：WAV 格式，完整的會議音訊

---

## 費用估算

### API 費用說明

#### Whisper API（語音辨識）
- **價格**：$0.006 USD / 分鐘（約 NT$0.19 / 分鐘）
- 適用於所有模式

#### GPT-4o-mini API（中文翻譯）
- **價格**：$0.15 / 1M input tokens，$0.6 / 1M output tokens
- 僅在「🈯 翻譯（日語→中文）」模式下使用
- 預估：每分鐘約 $0.001 USD（非常便宜）

### 費用估算表

| 會議時長 | Transcribe/Translate | 中文翻譯模式 |
|---------|---------------------|-------------|
| 15 分鐘 | $0.09               | ~$0.11      |
| 30 分鐘 | $0.18               | ~$0.21      |
| 1 小時  | $0.36               | ~$0.42      |
| 2 小時  | $0.72               | ~$0.84      |
| 4 小時  | $1.44               | ~$1.68      |

*中文翻譯模式多出的費用主要來自 GPT 翻譯（每分鐘約 $0.001）*

### 省錢小技巧

1. **啟用靜音偵測**：App 會自動跳過無聲片段（預設已啟用）
2. **調整音訊片段長度**：較長的片段（10-15 秒）可減少 API 呼叫次數
3. **會議結束後立即停止**：避免錄製多餘的靜音時段
4. **根據需求選擇模式**：如果不需要中文翻譯，使用 Transcribe 或 Translate 模式更便宜

實際費用通常會比預估值低 20-30%（因為靜音偵測）

---

## 常見問題 FAQ

### Q1：App 打不開怎麼辦？

**A：** 請檢查以下項目：

1. 確認已安裝 Python 3.9+：
   ```bash
   python3 --version
   ```

2. 確認已安裝 portaudio：
   ```bash
   brew list portaudio
   ```

3. 手動執行安裝腳本：
   ```bash
   cd ~/meeting-translator
   bash setup.sh
   ```

4. 查看錯誤訊息並回報

---

### Q2：沒有聲音怎麼辦？

**A：** 請檢查音訊設定：

1. **系統音訊輸出**是否設為「多重輸出裝置」？
   - 系統偏好設定 > 聲音 > 輸出

2. **BlackHole 2ch** 是否正確安裝？
   - 開啟「音訊 MIDI 設定」查看

3. App 中的**音訊輸入裝置**是否選擇「BlackHole 2ch」？

4. 會議軟體的音訊輸出是否正常？
   - 播放測試音訊確認

---

### Q3：辨識太慢怎麼辦？

**A：** 可能原因和解決方法：

1. **網路速度慢**
   - Whisper API 需要穩定的網路連線
   - 建議使用有線網路或 5GHz Wi-Fi

2. **音訊片段太短**
   - 增加音訊片段長度（側邊欄調整為 10-15 秒）

3. **API 伺服器負載高**
   - OpenAI API 有時會較慢，屬正常現象
   - 可嘗試稍後再試

---

### Q4：如何切換音訊裝置？

**A：** 在 App 側邊欄的「音訊輸入裝置」下拉選單中選擇：

- **BlackHole 2ch**：擷取系統音訊（會議軟體）
- **內建麥克風**：擷取實體麥克風（測試用）
- **其他裝置**：外接音訊介面等

**注意**：必須在停止錄音狀態下才能切換裝置

---

### Q5：API Key 會被儲存在哪裡？

**A：** API Key 會加密儲存在：

```
~/.meeting-translator/config.json
```

這是你的 Home 目錄下的隱藏資料夾，只有你的使用者帳號能存取。

---

### Q6：辨識結果不準確怎麼辦？

**A：** 可能的改善方法：

1. **確認語言設定正確**
   - 側邊欄選擇正確的音訊語言

2. **調整靜音閾值**
   - 如果音量太小，可能被誤判為靜音
   - 降低靜音閾值（例如 0.005）

3. **改善音訊品質**
   - 確保會議軟體的音訊設定正確
   - 避免背景噪音

4. **使用 Transcribe 模式**
   - Translate 模式可能會損失部分資訊
   - 建議先用 Transcribe 取得逐字稿，再自行翻譯

---

### Q7：可以同時翻譯多種語言嗎？

**A：** 目前一次只能設定一種語言，但你可以：

1. 停止目前的錄音
2. 切換語言設定
3. 重新開始錄音

或者分別錄製不同語言的會議，再分別處理。

---

### Q8：錄音檔案會佔用很多空間嗎？

**A：** WAV 檔案大小約為：

- **1 小時會議**：約 100-120 MB
- **2 小時會議**：約 200-240 MB

建議定期清理 `recordings/` 資料夾中不需要的錄音檔案。

---

### Q9：可以在 Windows 或 Linux 上使用嗎？

**A：** 目前僅支援 macOS，但理論上可以移植到其他平台：

- **Windows**：需要改用 VB-Audio Virtual Cable
- **Linux**：需要改用 PulseAudio 或 ALSA

但啟動腳本（`.command`）和音訊路由設定需要重新調整。

---

### Q10：如何更新專案？

**A：** 如果有新版本：

1. 備份你的 `recordings/` 和 `transcripts/` 資料夾
2. 下載新版本並覆蓋專案資料夾（保留 `.venv/`）
3. 執行更新：
   ```bash
   .venv/bin/pip install -r requirements.txt --upgrade
   ```
4. 重新啟動 App

---

## 專案結構

```
meeting-translator/
├── .venv/                          # Python 虛擬環境（自動建立）
├── recordings/                     # 會議錄音存放目錄
│   └── meeting_20240115_143022.wav
├── transcripts/                    # 逐字稿存放目錄
│   └── transcript_20240115_143022.txt
├── app.py                          # Streamlit 主程式
├── audio_recorder.py               # 音訊錄製模組
├── transcriber.py                  # Whisper API 呼叫模組
├── config_manager.py               # 配置管理模組
├── requirements.txt                # Python 依賴清單
├── setup.sh                        # 首次安裝腳本
├── run_meeting_translator.command  # macOS 雙擊啟動腳本
├── .gitignore                      # Git 忽略清單
└── README.md                       # 專案說明文件（本文件）
```

---

## 授權

本專案僅供個人學習和研究使用。

---

## 聯絡與回報問題

如有問題或建議，歡迎透過以下方式聯絡：

- 📧 Email: your-email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/meeting-translator/issues)

---

## 更新日誌

### v1.1.0 (2026-03-11)
- ✅ 新增日語→中文翻譯模式
- ✅ 整合 GPT-4o-mini 進行中文翻譯
- ✅ 優化 UI 顯示不同語言的背景色
- ✅ 修復多執行緒處理問題
- ✅ 添加完整的調試日誌功能

### v1.0.0 (2026-03-11)
- ✅ 初始版本發布
- ✅ 支援 Transcribe 和 Translate 模式
- ✅ 即時辨識和翻譯
- ✅ 錄音備份和逐字稿匯出
- ✅ 虛擬環境隔離
- ✅ macOS 雙擊啟動

---

**🎉 開始使用即時會議翻譯 App，讓語言不再是障礙！**
