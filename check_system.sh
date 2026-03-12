#!/bin/bash
# -*- coding: utf-8 -*-
# 系統兼容性檢查腳本

set -e

echo "========================================"
echo "  系統兼容性檢查"
echo "========================================"
echo ""

# 取得系統資訊
OS_VERSION=$(sw_vers -productVersion)
OS_BUILD=$(sw_vers -buildVersion)
ARCH=$(uname -m)

echo "【系統資訊】"
echo "  macOS 版本：$OS_VERSION ($OS_BUILD)"
echo "  處理器架構：$ARCH"
echo ""

# 檢測處理器類型
if [ "$ARCH" = "arm64" ]; then
    CHIP_TYPE="Apple Silicon (M1/M2/M3)"
    echo "  晶片類型：$CHIP_TYPE"
elif [ "$ARCH" = "x86_64" ]; then
    CHIP_TYPE="Intel"
    echo "  晶片類型：$CHIP_TYPE"
else
    CHIP_TYPE="未知"
    echo "  晶片類型：$CHIP_TYPE"
fi
echo ""

# 檢查最低系統要求
echo "【系統要求檢查】"
MIN_VERSION="10.15"
CURRENT_MAJOR=$(echo $OS_VERSION | cut -d. -f1)
CURRENT_MINOR=$(echo $OS_VERSION | cut -d. -f2)

if [ "$CURRENT_MAJOR" -gt 10 ] || ([ "$CURRENT_MAJOR" -eq 10 ] && [ "$CURRENT_MINOR" -ge 15 ]); then
    echo "  ✅ macOS 版本符合要求（>= $MIN_VERSION）"
else
    echo "  ❌ macOS 版本過舊（需要 >= $MIN_VERSION）"
    exit 1
fi
echo ""

# 檢查 Homebrew
echo "【依賴檢查】"
if command -v brew &> /dev/null; then
    BREW_VERSION=$(brew --version | head -1)
    echo "  ✅ Homebrew：已安裝 ($BREW_VERSION)"
else
    echo "  ❌ Homebrew：未安裝"
    echo ""
    echo "請安裝 Homebrew："
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

# 檢查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        echo "  ✅ Python：$PYTHON_VERSION"
    else
        echo "  ⚠️  Python：$PYTHON_VERSION（建議 >= 3.9）"
    fi
else
    echo "  ❌ Python：未安裝"
    echo ""
    echo "請安裝 Python："
    echo "  brew install python@3.9"
    exit 1
fi

# 檢查 portaudio
if brew list portaudio &> /dev/null; then
    PORTAUDIO_VERSION=$(brew list --versions portaudio | cut -d' ' -f2)
    echo "  ✅ portaudio：$PORTAUDIO_VERSION"
else
    echo "  ❌ portaudio：未安裝"
    echo ""
    echo "請安裝 portaudio："
    echo "  brew install portaudio"
    exit 1
fi

# 檢查 BlackHole
echo ""
echo "【音訊裝置檢查】"
if system_profiler SPAudioDataType | grep -q "BlackHole"; then
    echo "  ✅ BlackHole：已安裝"
else
    echo "  ⚠️  BlackHole：未檢測到"
    echo ""
    echo "如需使用系統音訊擷取，請安裝 BlackHole 2ch："
    echo "  https://existential.audio/blackhole/"
fi

# 檢查虛擬環境
echo ""
echo "【虛擬環境檢查】"
if [ -d ".venv" ]; then
    echo "  ✅ Python 虛擬環境：已存在"

    # 檢查依賴是否安裝
    if [ -f ".venv/bin/streamlit" ]; then
        echo "  ✅ 依賴套件：已安裝"
    else
        echo "  ⚠️  依賴套件：未安裝"
        echo ""
        echo "請執行以下命令安裝依賴："
        echo "  .venv/bin/pip install -r requirements.txt"
    fi
else
    echo "  ❌ Python 虛擬環境：未建立"
    echo ""
    echo "請執行以下命令建立虛擬環境："
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
fi

# Apple Silicon 特殊提示
if [ "$ARCH" = "arm64" ]; then
    echo ""
    echo "【Apple Silicon 提示】"
    echo "  ✅ 本專案原生支援 Apple Silicon"
    echo "  ✅ 所有依賴套件均可直接安裝，無需 Rosetta 2"
fi

echo ""
echo "========================================"
echo "  檢查完成！"
echo "========================================"
echo ""

# 顯示建議的下一步
if [ -d ".venv" ] && [ -f ".venv/bin/streamlit" ]; then
    echo "系統已準備就緒，可以執行："
    echo "  雙擊：run_meeting_translator.command"
    echo "  或執行：.venv/bin/streamlit run app.py"
else
    echo "請先執行安裝腳本："
    echo "  bash setup.sh"
fi
echo ""
