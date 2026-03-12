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
# 檢查 Python 3
# ============================================================================
PYTHON_CMD=""
if ! find_compatible_python; then
    echo "❌ 錯誤：找不到相容的 Python（需要 3.9+）"
    echo ""
    echo "請先安裝 Python："
    echo "  brew install python@3.12"
    echo ""
    echo "或者檢查您的 Python 安裝："
    echo "  python3 --version"
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
    "$PYTHON_CMD" -m venv .venv

    # 準備編譯環境
    prepare_build_env

    # 升級 pip 和建置工具
    echo "正在升級 pip 和建置工具..."
    .venv/bin/pip install --upgrade setuptools wheel
    .venv/bin/pip install --upgrade pip

    # 安裝依賴
    echo "正在安裝依賴套件（約需 1-2 分鐘）..."
    if ! .venv/bin/pip install -r requirements.txt; then
        echo ""
        echo "❌ 依賴安裝失敗"
        echo "請執行以下命令查看詳細錯誤："
        echo "  bash setup.sh"
        read -p "按 Enter 關閉..."
        exit 1
    fi

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
        prepare_build_env
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
