#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest conftest — 確保專案根目錄在 sys.path 中
"""

import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
