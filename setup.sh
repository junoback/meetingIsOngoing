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
# 函數定義
# ============================================================================

# 尋找相容的 Python 版本（3.9+）
find_compatible_python() {
    for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$candidate" > /dev/null 2>&1; then
            local version
            version=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            case "$version" in
                3.9|3.10|3.11|3.12|3.13|3.14)
                    PYTHON_CMD="$candidate"
                    PYTHON_VERSION="$version"
                    return 0
                    ;;
            esac
        fi
    done
    return 1
}

# 準備編譯環境（設定 portaudio 路徑）
prepare_build_env() {
    if command -v brew &> /dev/null && brew list portaudio &> /dev/null; then
        PORTAUDIO_PREFIX=$(brew --prefix portaudio)
        export CFLAGS="-I${PORTAUDIO_PREFIX}/include ${CFLAGS:-}"
        export LDFLAGS="-L${PORTAUDIO_PREFIX}/lib ${LDFLAGS:-}"
        export PKG_CONFIG_PATH="${PORTAUDIO_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    fi
}

# ============================================================================
# 1. 檢查 Homebrew
# ============================================================================
echo "【1/8】檢查 Homebrew..."
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
echo "【2/8】檢查 Python 3..."
PYTHON_CMD=""
PYTHON_VERSION=""

if ! find_compatible_python; then
    echo "找不到相容的 Python（需要 3.9+），正在安裝 Python 3.12..."
    brew install python@3.12

    if ! find_compatible_python; then
        echo "❌ 安裝 Python 後仍找不到可用版本，請重新開啟 Terminal 後再試一次"
        exit 1
    fi
    echo "✅ Python 已安裝（使用：$PYTHON_CMD，版本：$PYTHON_VERSION）"
else
    echo "✅ Python 已安裝（使用：$PYTHON_CMD，版本：$PYTHON_VERSION）"
fi
echo ""

# ============================================================================
# 3. 檢查 portaudio
# ============================================================================
echo "【3/8】檢查 portaudio（sounddevice 需要）..."
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

echo "  macOS 版本：$OS_VERSION"
echo "  處理器架構：$ARCH"
echo "  Python 版本：$PYTHON_VERSION (使用 $PYTHON_CMD)"
echo ""

# 決定安裝策略
INSTALL_STRATEGY="standard"

# macOS 10.15 (Catalina) 使用兼容性策略
if [ "$OS_MAJOR" -eq 10 ] && [ "$OS_MINOR" -eq 15 ]; then
    echo "⚠️  偵測到 macOS 10.15 (Catalina)，將使用兼容性安裝策略"
    INSTALL_STRATEGY="catalina"
fi

# Apple Silicon 特別提示
if [ "$ARCH" = "arm64" ]; then
    echo "✅ Apple Silicon (M1/M2/M3) - 原生支援"
fi

echo "📦 安裝策略：$INSTALL_STRATEGY"
echo ""

# ============================================================================
# 5. 建立虛擬環境
# ============================================================================
echo "【5/8】建立 Python 虛擬環境..."
if [ ! -d ".venv" ]; then
    echo "正在建立虛擬環境..."
    "$PYTHON_CMD" -m venv .venv
    echo "✅ 虛擬環境已建立"
else
    echo "✅ 虛擬環境已存在"
fi
echo ""

# ============================================================================
# 6. 升級 pip 和建置工具
# ============================================================================
echo "【6/8】升級 pip 和建置工具..."
prepare_build_env

.venv/bin/pip install --upgrade setuptools wheel
.venv/bin/pip install --upgrade pip
echo "✅ pip 已升級"
echo ""

# ============================================================================
# 7. 安裝依賴套件（根據系統環境自動適配）
# ============================================================================
echo "【7/8】安裝 Python 依賴套件..."
echo "這可能需要幾分鐘，請稍候..."
echo ""

case $INSTALL_STRATEGY in
    "catalina")
        echo "📦 使用 macOS 10.15 (Catalina) 兼容性安裝策略..."
        echo ""

        # Catalina 有時需要額外的編譯環境設定
        prepare_build_env

        if ! .venv/bin/pip install -r requirements.txt; then
            echo ""
            echo "❌ 依賴安裝失敗"
            echo "請確認 Python 版本：$PYTHON_VERSION"
            echo "建議使用 Python 3.11 或 3.12"
            echo ""
            echo "可手動執行以下命令查看完整錯誤："
            echo "  .venv/bin/pip install -r requirements.txt -v"
            exit 1
        fi
        ;;

    *)
        echo "📦 使用標準安裝策略..."

        if ! .venv/bin/pip install -r requirements.txt; then
            echo ""
            echo "❌ 依賴安裝失敗"
            echo "Python 版本：$PYTHON_VERSION"
            echo ""
            echo "可手動執行以下命令查看完整錯誤："
            echo "  .venv/bin/pip install -r requirements.txt -v"
            exit 1
        fi
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

if [ -f "check_system.sh" ]; then
    chmod +x check_system.sh
    echo "✅ 系統檢查腳本權限已設定"
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
echo "【系統資訊】"
echo "  macOS：$OS_VERSION ($ARCH)"
echo "  Python：$PYTHON_VERSION ($PYTHON_CMD)"
echo "  策略：$INSTALL_STRATEGY"
echo ""
echo "【接下來請】"
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
