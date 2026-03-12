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
# 4. 偵測系統環境
# ============================================================================
echo "【4/8】偵測系統環境..."

# 取得 macOS 版本
OS_VERSION=$(sw_vers -productVersion)
OS_MAJOR=$(echo $OS_VERSION | cut -d. -f1)
OS_MINOR=$(echo $OS_VERSION | cut -d. -f2)

# 取得處理器架構
ARCH=$(uname -m)

# 取得 Python 版本
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "  macOS 版本：$OS_VERSION"
echo "  處理器架構：$ARCH"
echo "  Python 版本：$PYTHON_VERSION"
echo ""

# 決定安裝策略
INSTALL_STRATEGY="standard"

# Python 3.13+ 需要特殊處理
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
    echo "⚠️  偵測到 Python 3.13+，將使用兼容性安裝策略"
    INSTALL_STRATEGY="python313"
fi

# macOS 10.15 (Catalina) 需要特殊處理
if [ "$OS_MAJOR" -eq 10 ] && [ "$OS_MINOR" -eq 15 ]; then
    echo "⚠️  偵測到 macOS 10.15 (Catalina)，將使用兼容性安裝策略"
    INSTALL_STRATEGY="catalina"
fi

echo "✅ 安裝策略：$INSTALL_STRATEGY"
echo ""

# ============================================================================
# 5. 建立虛擬環境
# ============================================================================
echo "【5/8】建立 Python 虛擬環境..."
if [ ! -d ".venv" ]; then
    echo "正在建立虛擬環境..."
    python3 -m venv .venv
    echo "✅ 虛擬環境已建立"
else
    echo "✅ 虛擬環境已存在"
fi
echo ""

# ============================================================================
# 6. 升級 pip
# ============================================================================
echo "【6/8】升級 pip 和建置工具..."
.venv/bin/pip install --upgrade pip setuptools wheel
echo "✅ pip 已升級"
echo ""

# ============================================================================
# 7. 安裝依賴套件（根據系統環境自動適配）
# ============================================================================
echo "【7/8】安裝 Python 依賴套件..."
echo "這可能需要幾分鐘，請稍候..."
echo ""

case $INSTALL_STRATEGY in
    "python313")
        echo "📦 使用 Python 3.13 兼容性安裝策略..."
        echo ""

        # Python 3.13 需要先安裝兼容的 pyarrow
        echo "  步驟 1/3：安裝 setuptools (Python 3.13 需要)..."
        .venv/bin/pip install setuptools

        echo "  步驟 2/3：嘗試安裝 pyarrow 預編譯版本..."
        # 先嘗試安裝預編譯的 pyarrow
        if .venv/bin/pip install pyarrow --only-binary :all: 2>/dev/null; then
            echo "  ✅ pyarrow 預編譯版本安裝成功"
        else
            echo "  ⚠️  預編譯版本失敗，嘗試安裝較舊的穩定版本..."
            .venv/bin/pip install "pyarrow<15.0.0" || echo "  ⚠️  pyarrow 安裝失敗，將繼續安裝其他套件"
        fi

        echo "  步驟 3/3：安裝其他依賴套件..."
        .venv/bin/pip install -r requirements.txt
        ;;

    "catalina")
        echo "📦 使用 macOS 10.15 (Catalina) 兼容性安裝策略..."
        echo ""

        # Catalina 使用較舊但穩定的版本
        echo "  步驟 1/2：安裝兼容版本的 pyarrow..."
        .venv/bin/pip install "pyarrow>=10.0.0,<15.0.0" || echo "  ⚠️  pyarrow 安裝失敗，將繼續"

        echo "  步驟 2/2：安裝其他依賴套件..."
        .venv/bin/pip install -r requirements.txt
        ;;

    *)
        echo "📦 使用標準安裝策略..."
        .venv/bin/pip install -r requirements.txt
        ;;
esac

echo ""
echo "✅ 依賴套件安裝完成"
echo ""

# ============================================================================
# 8. 建立必要目錄
# ============================================================================
echo "【8/8】建立必要目錄..."
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
