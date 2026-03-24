#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 樣板建構器與顯示常數

所有產生 HTML 的函式與它們依賴的常數、查找輔助函式都集中在這裡，
讓 app.py 只負責控制流程與 Streamlit widget 互動。
"""

import html as html_module
import streamlit as st
import streamlit.components.v1 as components


# ============================================================================
# 常數
# ============================================================================

LANGUAGE_OPTIONS = {
    "ja": "Japanese",
    "en": "English",
    "zh": "Chinese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German"
}

LANGUAGE_FILE_LABELS = {
    "ja": "日語",
    "en": "英文",
    "zh": "中文",
    "ko": "韓文",
    "es": "西班牙文",
    "fr": "法文",
    "de": "德文"
}

LANGUAGE_TONE_CLASSES = {
    "ja": "tone-ja",
    "en": "tone-en",
    "zh": "tone-zh"
}

MODE_ORDER = ("transcribe", "translate_en", "translate_target")

LEGACY_MODE_ALIASES = {
    "translate": "translate_en",
    "translate_zh": "translate_target"
}

TOP_PANEL_HEIGHT = 500
MAX_VISIBLE_FEED_ITEMS = 180
MAX_VISIBLE_TRANSCRIPT_CARDS = 120


# ============================================================================
# 查找輔助函式
# ============================================================================

def normalize_mode(mode: str) -> str:
    """將舊模式名稱轉成目前使用的模式名稱"""
    return LEGACY_MODE_ALIASES.get(mode, mode)


def get_language_label(language_code: str) -> str:
    """回傳介面用語言名稱"""
    return LANGUAGE_OPTIONS.get(language_code, language_code.upper())


def get_file_language_label(language_code: str) -> str:
    """回傳匯出檔案使用的語言名稱"""
    return LANGUAGE_FILE_LABELS.get(language_code, language_code.upper())


def get_language_tone(language_code: str) -> str:
    """回傳語言卡片配色"""
    return LANGUAGE_TONE_CLASSES.get(language_code, "tone-neutral")


def get_mode_options(source_language: str, target_language: str) -> dict[str, str]:
    """依來源語言建立可用模式與文案"""
    source_label = get_language_label(source_language)
    target_label = get_language_label(target_language)
    options = {
        "transcribe": f"Transcribe ({source_label})"
    }
    options["translate_en"] = f"Translate ({source_label} to English)"
    options["translate_target"] = f"Translate ({source_label} to Native Language: {target_label})"
    return options


def get_mode_summary(mode: str, source_language: str, target_language: str) -> str:
    """回傳模式摘要文案"""
    source_label = get_language_label(source_language)
    target_label = get_language_label(target_language)
    if mode == "transcribe":
        return f"Verbatim {source_label} transcript with no translation layer."
    if mode == "translate_en":
        return f"Capture {source_label} speech and render a live English translation."
    return f"Capture {source_label} speech and render a live {target_label} translation."


def get_default_mode(source_language: str, target_language: str) -> str:
    """依來源語言選擇預設模式"""
    if source_language != target_language:
        return "translate_target"
    if source_language != "en":
        return "translate_en"
    return "transcribe"


def get_flow_language_options(mode: str, source_language: str, target_language: str) -> list[str]:
    """依模式回傳可在閱讀流顯示的語言"""
    mode = normalize_mode(mode)
    languages = [source_language]

    if mode == "translate_en":
        languages.append("en")
    elif mode == "translate_target":
        languages.append("en")
        languages.append(target_language)

    unique_languages = []
    for language in languages:
        if language not in unique_languages:
            unique_languages.append(language)

    return unique_languages


def get_default_flow_language(mode: str, source_language: str, target_language: str) -> str:
    """依模式選擇閱讀流預設語言"""
    options = get_flow_language_options(mode, source_language, target_language)
    preferred = source_language

    if mode == "translate_en" and "en" in options:
        preferred = "en"
    elif mode == "translate_target" and target_language in options:
        preferred = target_language

    return preferred if preferred in options else options[0]


# ============================================================================
# 資料輔助函式
# ============================================================================

def limit_visible_items(items: list, max_items: int) -> tuple[list, int]:
    """限制前端一次渲染的項目數量，避免長 session 造成畫面 payload 過大"""
    if max_items <= 0 or len(items) <= max_items:
        return items, 0
    return items[-max_items:], len(items) - max_items


def normalize_transcript_payload(item: dict) -> tuple[str, str | None, dict[str, str], str]:
    """將逐字稿資料統一成以語言代碼為 key 的格式"""
    mode = normalize_mode(item.get('mode', 'transcribe'))
    raw_texts = item.get('texts', {}) or {}
    texts = {code: value for code, value in raw_texts.items() if value}
    source_language = item.get('source_language')
    target_language = item.get('target_language')

    if not source_language:
        if mode == "transcribe":
            source_language = item.get('language', 'ja')
        elif 'ja' in texts:
            source_language = 'ja'
        elif 'en' in texts and 'zh' not in texts:
            source_language = 'en'
        elif 'zh' in texts and 'en' not in texts:
            source_language = 'zh'
        else:
            source_language = item.get('language', 'ja')

    if 'original' in texts and source_language not in texts:
        texts[source_language] = texts['original']

    if not texts and item.get('text'):
        texts[item.get('language', source_language)] = item['text']

    if not target_language and mode == "translate_target":
        output_language = item.get('language')
        if output_language and output_language != source_language:
            target_language = output_language
        else:
            for language_code in texts.keys():
                if language_code not in [source_language, 'en']:
                    target_language = language_code
                    break

    return source_language, target_language, texts, mode


def get_transcript_language_order(item: dict) -> list[str]:
    """取得逐字稿卡片應顯示的語言順序"""
    source_language, target_language, texts, mode = normalize_transcript_payload(item)
    order = []

    if texts.get(source_language):
        order.append(source_language)

    if mode in ["translate_en", "translate_target"] and texts.get('en') and 'en' not in order:
        order.append('en')

    if mode == "translate_target" and target_language and texts.get(target_language) and target_language not in order:
        order.append(target_language)

    if not order and item.get('language'):
        order.append(item['language'])

    return order


def get_text_for_language(item: dict, language_code: str) -> str:
    """依語言代碼從逐字稿取出文字"""
    source_language, _, texts, _ = normalize_transcript_payload(item)

    if language_code in texts:
        return texts[language_code]
    if language_code == source_language and item.get('text') and item.get('language') == source_language:
        return item['text']
    if item.get('language') == language_code:
        return item.get('text', '')
    return ""


def get_feed_items(transcripts: list[dict], language_code: str) -> list[dict]:
    """取得依時間順序排列的閱讀流結果"""
    items = []
    for item in transcripts:
        selected_text = get_text_for_language(item, language_code)
        if selected_text:
            items.append({
                "timestamp": item['timestamp'].strftime('%H:%M:%S'),
                "text": selected_text
            })
    return items


# ============================================================================
# HTML 樣板建構器
# ============================================================================

def build_language_panel(label: str, text: str, tone_class: str) -> str:
    """建立語言區塊 HTML"""
    escaped_text = html_module.escape(text).replace("\n", "<br>")
    return f"""
    <div class='language-panel {tone_class}'>
        <div class='language-label'>
            <span class='language-dot'></span>
            <span>{html_module.escape(label)}</span>
        </div>
        <div class='language-copy'>{escaped_text}</div>
    </div>
    """


def render_metric_card(title: str, value: str, detail: str, accent: str = "accent-primary"):
    """渲染摘要資訊卡"""
    st.markdown(
        f"""
        <div class='metric-shell {accent}'>
            <div class='metric-label'>{html_module.escape(title)}</div>
            <div class='metric-value'>{html_module.escape(value)}</div>
            <div class='metric-detail'>{html_module.escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar_summary_card(rows: list[tuple[str, str]]):
    """渲染側邊欄摘要卡片"""
    row_html = "".join(
        f"<div class='sidebar-summary-row'><div class='sidebar-summary-key'>{html_module.escape(label)}</div><div class='sidebar-summary-value'>{html_module.escape(value)}</div></div>"
        for label, value in rows
        if value
    )
    if row_html:
        st.markdown(f"<div class='sidebar-summary-card'>{row_html}</div>", unsafe_allow_html=True)


def render_transcript_card(item: dict, show_multilingual: bool):
    """渲染單一逐字稿卡片"""
    timestamp_str = item['timestamp'].strftime('%H:%M:%S')
    latency = item['latency']
    source_language, _, _, _ = normalize_transcript_payload(item)
    panel_languages = get_transcript_language_order(item)

    if not show_multilingual:
        output_language = item.get('language', source_language)
        if output_language in panel_languages:
            panel_languages = [output_language]
        elif panel_languages:
            panel_languages = [panel_languages[-1]]

    panels = [
        build_language_panel(
            get_language_label(language_code),
            get_text_for_language(item, language_code),
            get_language_tone(language_code)
        )
        for language_code in panel_languages
        if get_text_for_language(item, language_code)
    ]

    st.markdown(
        f"""
        <div class='transcript-card'>
            <div class='transcript-top'>
                <span class='timestamp'>{timestamp_str}</span>
                <span class='latency'>{latency:.1f}s latency</span>
            </div>
            {''.join(panels)}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_live_feed_panel(
    feed_items: list[dict],
    feed_language: str,
    status_metadata: dict,
    meeting_name: str,
    meeting_topic: str,
    is_recording: bool
):
    """渲染上方閱讀流，保持最新內容可見"""
    flow_language_label = get_language_label(feed_language)

    if feed_items:
        content_html = (
            "<div class='feed-stream'>"
            + "<br>".join(
                html_module.escape(item['text']).replace("\n", "<br>")
                for item in feed_items
            )
            + "</div>"
        )
    else:
        if is_recording:
            empty_title = f"{flow_language_label} Reading Flow 已待命"
            empty_copy = f"正在等待第一段可顯示的 {flow_language_label} 內容。新內容會自動追加在下方，並保持最新段落可見。"
        else:
            empty_title = "等待開始"
            empty_copy = f"開始錄音後，這裡會依照語音順序串接 {flow_language_label} 內容，方便連續閱讀。"

        content_html = f"""
        <div class="feed-empty">
            <div class="feed-empty-title">{html_module.escape(empty_title)}</div>
            <div class="feed-empty-copy">{html_module.escape(empty_copy)}</div>
        </div>
        """

    panel_html = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            :root {{
                color-scheme: light dark;
                --bg: rgba(255, 255, 255, 0.88);
                --border: rgba(20, 31, 43, 0.12);
                --text-strong: #12202d;
                --text-main: #294053;
                --text-muted: #64748b;
                --chip: rgba(255, 255, 255, 0.78);
                --entry: rgba(255, 255, 255, 0.68);
                --accent: linear-gradient(135deg, rgba(15, 118, 110, 0.2), rgba(37, 99, 235, 0.16));
                --shadow: 0 26px 64px rgba(15, 23, 42, 0.14);
            }}

            @media (prefers-color-scheme: dark) {{
                :root {{
                    --bg: rgba(9, 16, 24, 0.92);
                    --border: rgba(148, 163, 184, 0.16);
                    --text-strong: #eef6ff;
                    --text-main: #d7e4f2;
                    --text-muted: #8ba0b6;
                    --chip: rgba(15, 23, 42, 0.62);
                    --entry: rgba(12, 20, 30, 0.74);
                    --accent: linear-gradient(135deg, rgba(15, 118, 110, 0.22), rgba(37, 99, 235, 0.18));
                    --shadow: 0 30px 72px rgba(2, 6, 23, 0.34);
                }}
            }}

            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                background: transparent;
                font-family: "Manrope", -apple-system, BlinkMacSystemFont, sans-serif;
                color: var(--text-main);
            }}

            .panel {{
                height: {TOP_PANEL_HEIGHT}px;
                padding: 1.15rem;
                border-radius: 30px;
                border: 1px solid var(--border);
                background:
                    radial-gradient(circle at top right, rgba(255,255,255,0.1), transparent 34%),
                    var(--accent),
                    var(--bg);
                box-shadow: var(--shadow);
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }}

            .panel-head {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 1rem;
                margin-bottom: 0.95rem;
            }}

            .eyebrow {{
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.16em;
                text-transform: uppercase;
                color: var(--text-muted);
            }}

            .title {{
                margin-top: 0.55rem;
                font-size: 1.48rem;
                font-weight: 800;
                line-height: 1.15;
                color: var(--text-strong);
                word-break: break-word;
            }}

            .subtitle {{
                margin-top: 0.38rem;
                font-size: 0.92rem;
                line-height: 1.55;
                color: var(--text-main);
                word-break: break-word;
            }}

            .status-chip {{
                flex-shrink: 0;
                padding: 0.58rem 0.82rem;
                border-radius: 999px;
                border: 1px solid var(--border);
                background: var(--chip);
                font-size: 0.8rem;
                font-weight: 700;
                color: var(--text-strong);
            }}

            .feed {{
                flex: 1;
                min-height: 0;
                padding-right: 0.3rem;
                overflow-y: auto;
                border-radius: 24px;
                border: 1px solid var(--border);
                background: var(--entry);
                padding: 1rem 1.05rem;
            }}

            .feed-stream {{
                font-size: 0.98rem;
                line-height: 1.78;
                color: var(--text-strong);
                white-space: normal;
                word-break: break-word;
                overflow-wrap: anywhere;
            }}

            .feed-empty {{
                height: 100%;
                display: grid;
                place-items: center;
                align-content: center;
                text-align: center;
                padding: 0.6rem;
            }}

            .feed-empty-title {{
                font-size: 1.12rem;
                font-weight: 800;
                color: var(--text-strong);
            }}

            .feed-empty-copy {{
                max-width: 38ch;
                margin-top: 0.55rem;
                font-size: 0.92rem;
                line-height: 1.68;
                color: var(--text-main);
            }}

            .feed::-webkit-scrollbar {{
                width: 8px;
            }}

            .feed::-webkit-scrollbar-thumb {{
                border-radius: 999px;
                background: var(--border);
            }}
        </style>
    </head>
    <body>
        <div class="panel">
            <div class="panel-head">
                <div>
                    <div class="eyebrow">Reading Flow</div>
                    <div class="title">{html_module.escape(meeting_name)}</div>
                    <div class="subtitle">{html_module.escape(meeting_topic)} · {html_module.escape(flow_language_label)}</div>
                </div>
                <div class="status-chip">{html_module.escape(status_metadata['label'])}</div>
            </div>
            <div class="feed" id="feed">{content_html}</div>
        </div>
        <script>
            const feed = document.getElementById("feed");
            if (feed) {{
                requestAnimationFrame(() => {{
                    feed.scrollTop = feed.scrollHeight;
                }});
                setTimeout(() => {{
                    feed.scrollTop = feed.scrollHeight;
                }}, 80);
            }}
        </script>
    </body>
    </html>
    """
    components.html(panel_html, height=TOP_PANEL_HEIGHT, scrolling=False)


def render_keyboard_shortcuts():
    """
    注入鍵盤快捷鍵 JS（透過 Streamlit 的隱藏 iframe 注入到頁面）

    快捷鍵：
      - Ctrl+Shift+R (or Cmd+Shift+R): Start Recording
      - Ctrl+Shift+P (or Cmd+Shift+P): Pause / Resume
      - Ctrl+Shift+S (or Cmd+Shift+S): Stop Session
    """
    shortcut_js = """
    <script>
    (function() {
        // 在 parent（Streamlit 主頁面）上綁定鍵盤事件
        const doc = window.parent.document;

        function clickButtonByText(text) {
            const buttons = doc.querySelectorAll('button[kind="primary"], button[kind="secondary"], button');
            for (const btn of buttons) {
                if (btn.textContent.trim().includes(text) && !btn.disabled) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }

        // 避免重複綁定
        if (doc._meetingShortcutsBound) return;
        doc._meetingShortcutsBound = true;

        doc.addEventListener('keydown', function(e) {
            const mod = e.ctrlKey || e.metaKey;
            if (!mod || !e.shiftKey) return;

            const key = e.key.toLowerCase();

            if (key === 'r') {
                e.preventDefault();
                clickButtonByText('Start Recording');
            } else if (key === 'p') {
                e.preventDefault();
                clickButtonByText('Pause') || clickButtonByText('Resume');
            } else if (key === 's') {
                e.preventDefault();
                clickButtonByText('Stop Session');
            }
        });
    })();
    </script>
    """
    components.html(shortcut_js, height=0)
