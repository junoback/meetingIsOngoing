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

    # 檢查 portaudio
    if ! brew list portaudio &> /dev/null 2>&1; then
        echo "正在安裝 portaudio（sounddevice 需要）..."
        brew install portaudio
    fi

    # 建立虛擬環境
    python3 -m venv .venv

    # 升級 pip
    echo "正在升級 pip..."
    .venv/bin/pip install --upgrade pip

    # 安裝依賴
    echo "正在安裝依賴套件（約需 1-2 分鐘）..."
    .venv/bin/pip install -r requirements.txt

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
