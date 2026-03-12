#!/bin/bash
# -*- coding: utf-8 -*-
# 會議翻譯 App - 首次安裝腳本

set -e  # 遇到錯誤立即停止

# 取得腳本所在目錄
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "======================================"
echo "  會議翻譯 App - 安裝程式"
echo "======================================"
echo ""

# ============================================================================
# 1. 檢查 Homebrew
# ============================================================================
echo "【1/7】檢查 Homebrew..."
if ! command -v brew &> /dev/null; then
    echo ""
    echo "❌ 錯誤：找不到 Homebrew"
    echo ""
    echo "請先安裝 Homebrew，在 Terminal 中執行以下指令："
    echo ""
    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    exit 1
fi
echo "✅ Homebrew 已安裝"
echo ""

# ============================================================================
# 2. 檢查 Python 3
# ============================================================================
echo "【2/7】檢查 Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 未安裝，正在安裝..."
    brew install python@3.9
    echo "✅ Python 3 已安裝"
else
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
    echo "✅ Python 已安裝（版本：$PYTHON_VERSION）"
fi
echo ""

# ============================================================================
# 3. 檢查 portaudio
# ============================================================================
echo "【3/7】檢查 portaudio（sounddevice 需要）..."
if ! brew list portaudio &> /dev/null; then
    echo "portaudio 未安裝，正在安裝..."
    brew install portaudio
    echo "✅ portaudio 已安裝"
else
    echo "✅ portaudio 已安裝"
fi
echo ""

# ============================================================================
# 4. 建立虛擬環境
# ============================================================================
echo "【4/7】建立 Python 虛擬環境..."
if [ ! -d ".venv" ]; then
    echo "正在建立虛擬環境..."
    python3 -m venv .venv
    echo "✅ 虛擬環境已建立"
else
    echo "✅ 虛擬環境已存在"
fi
echo ""

# ============================================================================
# 5. 升級 pip
# ============================================================================
echo "【5/7】升級 pip..."
.venv/bin/pip install --upgrade pip
echo "✅ pip 已升級"
echo ""

# ============================================================================
# 6. 安裝依賴套件
# ============================================================================
echo "【6/7】安裝 Python 依賴套件..."
echo "這可能需要幾分鐘，請稍候..."
.venv/bin/pip install -r requirements.txt
echo "✅ 依賴套件已安裝"
echo ""

# ============================================================================
# 7. 建立必要目錄
# ============================================================================
echo "【7/7】建立必要目錄..."
mkdir -p recordings
mkdir -p transcripts
echo "✅ 目錄已建立"
echo ""

# ============================================================================
# 設定執行權限
# ============================================================================
if [ -f "run_meeting_translator.command" ]; then
    chmod +x run_meeting_translator.command
    echo "✅ 啟動腳本權限已設定"
    echo ""
fi

# ============================================================================
# 完成
# ============================================================================
echo ""
echo "=========================================="
echo "  ✅ 安裝完成！"
echo "=========================================="
echo ""
echo "接下來請："
echo ""
echo "1. 確認已安裝 BlackHole 2ch 虛擬音訊裝置"
echo "   下載：https://existential.audio/blackhole/"
echo ""
echo "2. 設定系統音訊為「多重輸出裝置」"
echo "   （內建輸出 + BlackHole 2ch）"
echo ""
echo "3. 取得 OpenAI API Key"
echo "   網址：https://platform.openai.com/api-keys"
echo ""
echo "4. 雙擊 run_meeting_translator.command 啟動 App"
echo "   或在 Terminal 中執行："
echo "   .venv/bin/streamlit run app.py"
echo ""
echo "=========================================="
