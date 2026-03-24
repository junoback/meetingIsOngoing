#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主題 CSS — 從 app.py 提取

提供 get_main_css() 回傳完整 <style> 區塊字串，
由 app.py 在頁面初始化時注入。
"""


def get_main_css() -> str:
    """回傳主畫面的完整 CSS（含 light / dark mode）"""
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        color-scheme: light dark;
        --bg-base: #f4efe7;
        --bg-alt: #f8f6f1;
        --panel: rgba(255, 255, 255, 0.72);
        --panel-strong: rgba(255, 255, 255, 0.88);
        --surface-border: rgba(20, 31, 43, 0.08);
        --surface-border-strong: rgba(20, 31, 43, 0.14);
        --text-strong: #12202d;
        --text-main: #2d3e4f;
        --text-muted: #6a7c8f;
        --chip-bg: rgba(255, 255, 255, 0.62);
        --accent-primary: #0f766e;
        --accent-secondary: #2563eb;
        --accent-warm: #d97706;
        --accent-red: #dc2626;
        --accent-green: #16a34a;
        --shadow-sm: 0 20px 40px rgba(15, 23, 42, 0.08);
        --shadow-md: 0 28px 60px rgba(15, 23, 42, 0.14);
        --shadow-lg: 0 36px 84px rgba(15, 23, 42, 0.18);
        --tone-ja: rgba(37, 99, 235, 0.08);
        --tone-ja-border: rgba(37, 99, 235, 0.22);
        --tone-en: rgba(22, 163, 74, 0.08);
        --tone-en-border: rgba(22, 163, 74, 0.22);
        --tone-zh: rgba(217, 119, 6, 0.1);
        --tone-zh-border: rgba(217, 119, 6, 0.24);
        --tone-neutral: rgba(100, 116, 139, 0.08);
        --tone-neutral-border: rgba(100, 116, 139, 0.18);
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --bg-base: #08111a;
            --bg-alt: #0d1722;
            --panel: rgba(10, 18, 28, 0.74);
            --panel-strong: rgba(13, 23, 34, 0.9);
            --surface-border: rgba(148, 163, 184, 0.14);
            --surface-border-strong: rgba(148, 163, 184, 0.24);
            --text-strong: #eef6ff;
            --text-main: #d7e4f2;
            --text-muted: #8ba0b6;
            --chip-bg: rgba(15, 23, 42, 0.58);
            --shadow-sm: 0 24px 48px rgba(2, 6, 23, 0.28);
            --shadow-md: 0 30px 72px rgba(2, 6, 23, 0.34);
            --shadow-lg: 0 44px 96px rgba(2, 6, 23, 0.42);
            --tone-ja: rgba(59, 130, 246, 0.14);
            --tone-ja-border: rgba(96, 165, 250, 0.3);
            --tone-en: rgba(22, 163, 74, 0.14);
            --tone-en-border: rgba(74, 222, 128, 0.3);
            --tone-zh: rgba(217, 119, 6, 0.16);
            --tone-zh-border: rgba(251, 191, 36, 0.34);
            --tone-neutral: rgba(100, 116, 139, 0.16);
            --tone-neutral-border: rgba(148, 163, 184, 0.28);
        }
    }

    html,
    body,
    [data-testid="stAppViewContainer"],
    .stApp {
        font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-main);
        background: transparent;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(14, 165, 233, 0.16), transparent 32%),
            radial-gradient(circle at top right, rgba(245, 158, 11, 0.16), transparent 28%),
            linear-gradient(180deg, var(--bg-base) 0%, var(--bg-alt) 100%);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .main .block-container {
        max-width: 1420px;
        padding: 2.25rem 2rem 4rem 2rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--panel-strong) 0%, var(--panel) 100%);
        border-right: 1px solid var(--surface-border);
        backdrop-filter: blur(24px);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 1.25rem 1rem 2rem 1rem;
    }

    h1,
    h2,
    h3,
    h4,
    p,
    label,
    .stMarkdown,
    .stCaption,
    .stText {
        font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-main);
    }

    h1,
    h2,
    h3,
    h4 {
        color: var(--text-strong);
        letter-spacing: -0.03em;
    }

    a {
        color: var(--accent-secondary);
    }

    hr {
        margin: 1.4rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--surface-border-strong) 50%, transparent 100%);
    }

    .sidebar-brand {
        position: relative;
        overflow: hidden;
        padding: 1.2rem 1.05rem 1.15rem 1.05rem;
        border-radius: 28px;
        border: 1px solid var(--surface-border-strong);
        background:
            linear-gradient(135deg, rgba(15, 118, 110, 0.16), rgba(37, 99, 235, 0.12) 58%, transparent 100%),
            var(--panel);
        box-shadow: var(--shadow-md);
    }

    .sidebar-brand::before {
        content: "";
        position: absolute;
        width: 180px;
        height: 180px;
        right: -72px;
        top: -108px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.18);
        filter: blur(8px);
    }

    .sidebar-kicker {
        position: relative;
        z-index: 1;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .sidebar-title {
        position: relative;
        z-index: 1;
        margin-top: 0.55rem;
        font-size: 1.38rem;
        font-weight: 800;
        line-height: 1.15;
        color: var(--text-strong);
    }

    .sidebar-subtitle {
        position: relative;
        z-index: 1;
        margin: 0.5rem 0 0 0;
        font-size: 0.86rem;
        line-height: 1.55;
        color: var(--text-main);
    }

    .sidebar-note,
    .sidebar-summary-card {
        margin-top: 0.85rem;
        padding: 0.95rem 1rem;
        border-radius: 20px;
        border: 1px solid var(--surface-border);
        background: var(--chip-bg);
        box-shadow: var(--shadow-sm);
    }

    .sidebar-block-title {
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .sidebar-block-copy {
        margin-top: 0.5rem;
        font-size: 0.88rem;
        line-height: 1.6;
        color: var(--text-main);
    }

    .sidebar-summary-card {
        display: grid;
        gap: 0.72rem;
    }

    .sidebar-summary-row {
        display: grid;
        gap: 0.2rem;
    }

    .sidebar-summary-key {
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .sidebar-summary-value {
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 1.5;
        color: var(--text-strong);
        white-space: normal;
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    .sidebar-file-note {
        margin-top: 0.7rem;
        font-size: 0.84rem;
        line-height: 1.6;
        color: var(--text-main);
        white-space: normal;
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    .section-label {
        margin: 0.2rem 0 0.8rem 0;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .hero-shell {
        position: relative;
        overflow: hidden;
        min-height: 100%;
        padding: 2rem 2rem 2.15rem 2rem;
        border-radius: 32px;
        border: 1px solid var(--surface-border-strong);
        background:
            linear-gradient(135deg, rgba(15, 118, 110, 0.18), rgba(37, 99, 235, 0.14) 50%, transparent 80%),
            var(--panel-strong);
        box-shadow: var(--shadow-lg);
    }

    .hero-shell::before {
        content: "";
        position: absolute;
        width: 340px;
        height: 340px;
        right: -120px;
        top: -160px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.12);
        filter: blur(8px);
    }

    .hero-kicker {
        position: relative;
        z-index: 1;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .hero-title {
        position: relative;
        z-index: 1;
        margin-top: 0.8rem;
        font-size: clamp(2.15rem, 4.4vw, 3.6rem);
        font-weight: 800;
        line-height: 0.98;
        color: var(--text-strong);
        max-width: 12ch;
    }

    .hero-copy {
        position: relative;
        z-index: 1;
        max-width: 64ch;
        margin-top: 1rem;
        font-size: 1rem;
        line-height: 1.75;
        color: var(--text-main);
    }

    .hero-pill-row {
        position: relative;
        z-index: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 1.3rem;
    }

    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.65rem 0.9rem;
        border-radius: 999px;
        border: 1px solid var(--surface-border);
        background: var(--chip-bg);
        font-size: 0.83rem;
        font-weight: 600;
        color: var(--text-strong);
    }

    .status-panel {
        height: 500px;
        box-sizing: border-box;
        padding: 1.2rem 1rem;
        border-radius: 26px;
        border: 1px solid var(--surface-border-strong);
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 30%),
            var(--panel);
        box-shadow: var(--shadow-md);
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .status-panel-title {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .status-panel-value {
        margin-top: 0.85rem;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.05;
        color: var(--text-strong);
    }

    .status-panel-copy {
        margin-top: 0.45rem;
        font-size: 0.84rem;
        line-height: 1.55;
        color: var(--text-main);
    }

    .status-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.7rem;
        margin-top: auto;
        min-height: 0;
    }

    .status-mini {
        padding: 0.8rem 0.85rem;
        border-radius: 18px;
        border: 1px solid var(--surface-border);
        background: var(--chip-bg);
    }

    .status-mini-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .status-mini-value {
        margin-top: 0.38rem;
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-strong);
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.95rem;
        padding: 0.6rem 0.95rem;
        border-radius: 999px;
        border: 1px solid transparent;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }

    .status-recording {
        color: #ffe4e6;
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.92), rgba(249, 115, 22, 0.84));
        box-shadow: 0 18px 32px rgba(220, 38, 38, 0.22);
    }

    .status-paused {
        color: #422006;
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.92), rgba(245, 158, 11, 0.82));
        box-shadow: 0 18px 32px rgba(245, 158, 11, 0.18);
    }

    .status-stopped {
        color: var(--text-strong);
        border-color: var(--surface-border);
        background: var(--chip-bg);
    }

    .status-icon {
        font-size: 0.84rem;
    }

    .recording-indicator {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        background: #fff5f5;
        display: inline-block;
        animation: pulse-dot 1.5s ease-in-out infinite;
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.22); }
        50% { opacity: 0.4; box-shadow: 0 0 0 10px rgba(255, 255, 255, 0); }
    }

    .control-caption {
        margin: 1.3rem 0 0.75rem 0;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .control-note {
        margin: -0.15rem 0 1rem 0;
        font-size: 0.92rem;
        line-height: 1.6;
        color: var(--text-main);
    }

    .metric-shell {
        position: relative;
        overflow: hidden;
        min-height: 132px;
        padding: 1.1rem 1.15rem 1.25rem 1.15rem;
        border-radius: 24px;
        border: 1px solid var(--surface-border);
        background: var(--panel);
        box-shadow: var(--shadow-sm);
    }

    .metric-shell::after {
        content: "";
        position: absolute;
        width: 130px;
        height: 130px;
        right: -42px;
        bottom: -76px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
    }

    .accent-primary {
        background:
            linear-gradient(180deg, rgba(15, 118, 110, 0.12), transparent 52%),
            var(--panel);
    }

    .accent-secondary {
        background:
            linear-gradient(180deg, rgba(37, 99, 235, 0.12), transparent 52%),
            var(--panel);
    }

    .accent-warm {
        background:
            linear-gradient(180deg, rgba(217, 119, 6, 0.12), transparent 52%),
            var(--panel);
    }

    .accent-neutral {
        background:
            linear-gradient(180deg, rgba(100, 116, 139, 0.12), transparent 52%),
            var(--panel);
    }

    .metric-label {
        position: relative;
        z-index: 1;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .metric-value {
        position: relative;
        z-index: 1;
        margin-top: 0.75rem;
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1.08;
        color: var(--text-strong);
    }

    .metric-detail {
        position: relative;
        z-index: 1;
        margin-top: 0.45rem;
        font-size: 0.88rem;
        line-height: 1.5;
        color: var(--text-main);
    }

    .section-head {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 1rem;
        margin: 2rem 0 1rem 0;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: var(--text-strong);
        letter-spacing: -0.03em;
    }

    .section-copy {
        margin-top: 0.25rem;
        font-size: 0.92rem;
        line-height: 1.6;
        color: var(--text-main);
    }

    .section-chip {
        display: inline-flex;
        align-items: center;
        padding: 0.68rem 0.9rem;
        border-radius: 999px;
        border: 1px solid var(--surface-border);
        background: var(--chip-bg);
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--text-strong);
        white-space: nowrap;
    }

    .transcript-card {
        padding: 1.25rem;
        margin-bottom: 1rem;
        border-radius: 28px;
        border: 1px solid var(--surface-border);
        background: var(--panel-strong);
        box-shadow: var(--shadow-sm);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    .transcript-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .transcript-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.55rem;
    }

    .timestamp,
    .latency {
        font-family: 'IBM Plex Mono', 'SF Mono', Monaco, monospace;
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    .timestamp {
        font-size: 0.8rem;
        color: var(--text-strong);
    }

    .latency {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .language-panel {
        margin-top: 0.8rem;
        padding: 1rem 1rem 1.05rem 1rem;
        border-radius: 22px;
        border: 1px solid var(--surface-border);
        background: var(--chip-bg);
    }

    .language-panel.tone-ja {
        background: var(--tone-ja);
        border-color: var(--tone-ja-border);
    }

    .language-panel.tone-en {
        background: var(--tone-en);
        border-color: var(--tone-en-border);
    }

    .language-panel.tone-zh {
        background: var(--tone-zh);
        border-color: var(--tone-zh-border);
    }

    .language-panel.tone-neutral {
        background: var(--tone-neutral);
        border-color: var(--tone-neutral-border);
    }

    .language-label {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .language-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: currentColor;
        opacity: 0.72;
    }

    .language-copy {
        margin-top: 0.55rem;
        font-size: 0.98rem;
        line-height: 1.78;
        color: var(--text-strong);
    }

    .empty-state {
        padding: 4.1rem 2rem;
        border-radius: 32px;
        border: 1px dashed var(--surface-border-strong);
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 65%),
            var(--panel);
        text-align: center;
        box-shadow: var(--shadow-sm);
    }

    .empty-icon {
        font-size: 3.3rem;
        opacity: 0.7;
    }

    .empty-title {
        margin-top: 1rem;
        font-size: 1.15rem;
        font-weight: 800;
        color: var(--text-strong);
    }

    .empty-copy {
        max-width: 42ch;
        margin: 0.55rem auto 0 auto;
        font-size: 0.94rem;
        line-height: 1.7;
        color: var(--text-main);
    }

    .stButton > button,
    [data-testid="stDownloadButton"] button {
        min-height: 3.5rem;
        border-radius: 999px;
        border: 1px solid transparent;
        padding: 0.88rem 1.25rem;
        font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
    }

    .stButton > button[kind="primary"] {
        color: #f8fafc;
        background: linear-gradient(135deg, #0f766e, #2563eb 58%, #1d4ed8 100%);
        box-shadow: 0 26px 44px rgba(37, 99, 235, 0.28);
    }

    .stButton > button[kind="secondary"],
    [data-testid="stDownloadButton"] button {
        color: var(--text-strong);
        background: linear-gradient(180deg, rgba(217, 119, 6, 0.1), var(--chip-bg));
        border-color: var(--surface-border);
        box-shadow: 0 14px 26px rgba(15, 23, 42, 0.08);
    }

    .stButton > button:hover,
    [data-testid="stDownloadButton"] button:hover {
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 26px 44px rgba(37, 99, 235, 0.28);
    }

    .stButton > button:disabled,
    [data-testid="stDownloadButton"] button:disabled {
        opacity: 0.38;
        transform: none;
    }

    [data-testid="stSidebar"] .stButton > button {
        min-height: 2.85rem;
        font-size: 0.92rem;
        box-shadow: none;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] > div,
    div[data-baseweb="select"] > div,
    .stTextInput input,
    .stTextArea textarea {
        border-radius: 18px !important;
        border: 1px solid var(--surface-border) !important;
        background: var(--panel) !important;
        color: var(--text-strong) !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] div[data-baseweb="select"] span {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
        line-height: 1.4 !important;
    }

    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        min-height: 3.85rem;
        align-items: flex-start;
        padding-top: 0.7rem;
        padding-bottom: 0.7rem;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: var(--text-muted) !important;
    }

    .stTextInput label,
    .stSelectbox label,
    .stSlider label,
    .stCheckbox label,
    .stRadio label,
    .stTextArea label {
        color: var(--text-main) !important;
        font-weight: 600;
    }

    .stRadio > div {
        gap: 0.55rem;
    }

    .stRadio > div > label {
        border-radius: 18px;
        border: 1px solid var(--surface-border);
        background: var(--panel);
        padding: 0.78rem 0.92rem;
    }

    .stRadio > div > label:hover {
        border-color: var(--surface-border-strong);
    }

    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: var(--accent-secondary);
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14);
    }

    .stSlider [data-baseweb="slider"] > div > div {
        background: rgba(37, 99, 235, 0.22);
    }

    label[data-baseweb="checkbox"] > div:first-child {
        border-color: var(--surface-border-strong) !important;
        background: var(--panel) !important;
    }

    [data-testid="stMetric"] {
        border-radius: 22px;
        border: 1px solid var(--surface-border);
        background: var(--panel);
        padding: 0.95rem 1rem;
    }

    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', 'SF Mono', Monaco, monospace;
        font-size: 1.25rem;
        color: var(--text-strong);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .streamlit-expanderHeader,
    .stAlert,
    .stCodeBlock,
    pre {
        border-radius: 20px !important;
        border: 1px solid var(--surface-border) !important;
        background: var(--panel) !important;
        color: var(--text-main) !important;
    }

    [data-testid="stMarkdownContainer"] p {
        color: var(--text-main);
    }

    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: var(--surface-border-strong);
        border-radius: 999px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }

    @media (max-width: 900px) {
        .main .block-container {
            padding: 1.5rem 1rem 3rem 1rem;
        }

        .hero-shell,
        .status-panel,
        .transcript-card,
        .empty-state {
            border-radius: 24px;
        }

        .status-panel {
            height: auto;
            min-height: 420px;
        }

        .hero-title {
            max-width: none;
            font-size: 2.4rem;
        }

        .status-grid {
            grid-template-columns: 1fr;
        }

        .section-head {
            flex-direction: column;
            align-items: flex-start;
        }
    }
</style>
"""
