#!/bin/bash
# -*- coding: utf-8 -*-
# 會議翻譯 App - 啟動腳本（雙擊執行）

# 取得腳本所在目錄（支援從任何位置雙擊執行）
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "======================================"
echo "  會議翻譯 App"
echo "======================================"
echo ""

# ============================================================================
# 檢查 Python 3
# ============================================================================
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：找不到 python3"
    echo ""
    echo "請先安裝 Python 3："
    echo "  brew install python@3.9"
    echo ""
    read -p "按 Enter 關閉..."
    exit 1
fi

# ============================================================================
# 首次啟動：建立虛擬環境
# ============================================================================
if [ ! -d ".venv" ]; then
    echo "【首次啟動】正在建立虛擬環境..."
    echo ""

    # 偵測系統環境
    echo "偵測系統環境..."
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    OS_VERSION=$(sw_vers -productVersion)
    OS_MAJOR=$(echo $OS_VERSION | cut -d. -f1)
    OS_MINOR=$(echo $OS_VERSION | cut -d. -f2)

    echo "  Python 版本：$PYTHON_VERSION"
    echo "  macOS 版本：$OS_VERSION"
    echo ""

    # 決定安裝策略
    INSTALL_STRATEGY="standard"
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
        INSTALL_STRATEGY="python313"
        echo "⚠️  偵測到 Python 3.13+，將使用兼容性安裝"
    elif [ "$OS_MAJOR" -eq 10 ] && [ "$OS_MINOR" -eq 15 ]; then
        INSTALL_STRATEGY="catalina"
        echo "⚠️  偵測到 macOS 10.15，將使用兼容性安裝"
    fi
    echo ""

    # 檢查 portaudio
    if ! brew list portaudio &> /dev/null 2>&1; then
        echo "正在安裝 portaudio（sounddevice 需要）..."
        brew install portaudio
    fi

    # 建立虛擬環境
    python3 -m venv .venv

    # 升級 pip
    echo "正在升級 pip 和建置工具..."
    .venv/bin/pip install --upgrade pip setuptools wheel

    # 根據策略安裝依賴
    echo "正在安裝依賴套件（約需 1-2 分鐘）..."
    echo ""

    case $INSTALL_STRATEGY in
        "python313")
            echo "使用 Python 3.13 兼容性安裝..."
            .venv/bin/pip install setuptools
            .venv/bin/pip install pyarrow --only-binary :all: 2>/dev/null || \
            .venv/bin/pip install "pyarrow<15.0.0" || \
            echo "⚠️  pyarrow 安裝失敗，將繼續"
            .venv/bin/pip install -r requirements.txt
            ;;
        "catalina")
            echo "使用 macOS 10.15 兼容性安裝..."
            .venv/bin/pip install "pyarrow>=10.0.0,<15.0.0" || echo "⚠️  pyarrow 安裝失敗"
            .venv/bin/pip install -r requirements.txt
            ;;
        *)
            .venv/bin/pip install -r requirements.txt
            ;;
    esac

    echo ""
    echo "✅ 虛擬環境建立完成！"
    echo ""
fi

# ============================================================================
# 檢查套件更新
# ============================================================================
if [ -f "requirements.txt" ] && [ -f ".venv/pyvenv.cfg" ]; then
    # 檢查 requirements.txt 是否比虛擬環境更新
    if [ "requirements.txt" -nt ".venv/pyvenv.cfg" ]; then
        echo "偵測到套件更新，正在同步..."
        .venv/bin/pip install -r requirements.txt
        echo "✅ 套件已更新"
        echo ""
    fi
fi

# ============================================================================
# 建立必要目錄
# ============================================================================
mkdir -p recordings
mkdir -p transcripts

# ============================================================================
# 啟動 Streamlit App
# ============================================================================
echo ""
echo "======================================"
echo "  🎙️ 會議翻譯 App 啟動中..."
echo "  瀏覽器將自動開啟"
echo "  按 Ctrl+C 停止服務"
echo "======================================"
echo ""

# 使用虛擬環境的 streamlit 啟動
exec .venv/bin/streamlit run app.py --server.headless true --server.port 8501
