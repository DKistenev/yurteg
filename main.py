"""ЮрТэг — Streamlit UI для обработки архива документов."""
import io
import os
import tempfile
import time
import zipfile
from pathlib import Path

# tkinter конфликтует с pywebview в десктопном режиме
_DESKTOP_MODE = os.environ.get("YURTEG_DESKTOP") == "1"
if not _DESKTOP_MODE:
    try:
        import tkinter as tk
        from tkinter import filedialog
        _HAS_TK = True
    except Exception:
        _HAS_TK = False
else:
    _HAS_TK = False

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ── Облачный режим: бридж Streamlit Secrets → os.environ ──────
try:
    for _key in ("ZHIPU_API_KEY", "OPENROUTER_API_KEY", "ZAI_API_KEY", "YURTEG_CLOUD"):
        if _key in st.secrets and _key not in os.environ:
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass  # Нет secrets (десктопный режим)

_CLOUD_MODE = os.environ.get("YURTEG_CLOUD") == "1"

from config import Config
from controller import Controller
from modules.ai_extractor import verify_api_key
from modules.anonymizer import ENTITY_TYPES
from modules.reporter import generate_report
from services import pipeline_service
from services.client_manager import ClientManager
from services.lifecycle_service import (
    get_computed_status_sql, set_manual_status, clear_manual_status,
    get_attention_required, MANUAL_STATUSES, STATUS_LABELS,
)
from services.version_service import (
    get_version_group, diff_versions, generate_redline_docx,
)
from services.payment_service import get_calendar_events
from services.review_service import (
    add_template, list_templates, match_template,
    review_against_template, mark_contract_as_template,
)

try:
    from streamlit_calendar import calendar as st_calendar
    _HAS_CALENDAR = True
except ImportError:
    _HAS_CALENDAR = False

from services.llama_server import LlamaServerManager
from modules.postprocessor import get_grammar_path

# Загрузить API-ключи из .env (десктоп; в облаке уже в os.environ)
load_dotenv()

# ── Автозапуск llama-server для локальной LLM ──────────────────


@st.cache_resource
def _get_llama_manager() -> "LlamaServerManager | None":
    """Запускает llama-server один раз, переживает Streamlit reruns."""
    config = Config()
    if config.active_provider != "ollama":
        return None

    manager = LlamaServerManager(port=config.llama_server_port)

    # Скачивание модели (~940 МБ, только при первом запуске)
    try:
        with st.spinner("Скачивание модели (~940 МБ)..."):
            manager.ensure_model()
    except Exception as e:
        st.warning(f"Не удалось скачать модель: {e}. Переключение на облачный провайдер.")
        return None

    # Скачивание llama-server бинарника
    try:
        with st.spinner("Скачивание llama-server..."):
            manager.ensure_server_binary()
    except Exception as e:
        st.warning(f"Не удалось скачать llama-server: {e}. Переключение на облачный провайдер.")
        return None

    # Запуск сервера
    if not manager.is_running():
        try:
            grammar = get_grammar_path()
            manager.start(grammar_path=grammar)
        except Exception as e:
            st.warning(f"llama-server не запустился: {e}. Переключение на облачный провайдер.")
            return None

    return manager


# Запустить при загрузке приложения (cache_resource — только один раз)
_llama = _get_llama_manager()
if _llama is None and Config().active_provider == "ollama":
    st.warning("Локальная модель недоступна. Используется облачный провайдер.")
    # Провайдер упадёт в fallback через ai_extractor verify_key → OllamaProvider.verify_key() == False

# ── Настройка страницы ──────────────────────────────────────────

st.set_page_config(
    page_title="ЮрТэг",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Кастомные стили ─────────────────────────────────────────────

st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════════
       ЮрТэг — Liquid Glass Design System
       ═══════════════════════════════════════════════════════════ */

    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --glass-bg-1: rgba(255,255,255,0.03);
        --glass-bg-2: rgba(255,255,255,0.06);
        --glass-bg-3: rgba(255,255,255,0.10);
        --glass-border: rgba(255,255,255,0.08);
        --glass-border-hi: rgba(255,255,255,0.15);
        --glass-blur-1: blur(20px);
        --glass-blur-2: blur(32px);
        --accent: #06B6D4;
        --accent-soft: rgba(6,182,212,0.15);
        --accent-glow: rgba(6,182,212,0.25);
        --surface: #0B1120;
        --surface-raised: #111827;
        --text-primary: #F1F5F9;
        --text-secondary: #94A3B8;
        --text-muted: #475569;
        --success: #34D399;
        --warning: #FBBF24;
        --error: #F87171;
        --radius-sm: 10px;
        --radius-md: 16px;
        --radius-lg: 24px;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ── Фон: mesh-gradient с мягкими пятнами ─────────────────── */
    .stApp {
        background:
            radial-gradient(ellipse 600px 600px at 15% 20%, rgba(6,182,212,0.07) 0%, transparent 70%),
            radial-gradient(ellipse 500px 500px at 85% 60%, rgba(99,102,241,0.05) 0%, transparent 70%),
            radial-gradient(ellipse 400px 400px at 50% 90%, rgba(168,85,247,0.04) 0%, transparent 70%),
            #080C14;
    }

    .block-container { padding-top: 0.75rem; padding-bottom: 1rem; }

    /* Скрыть Streamlit branding */
    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

    /* ── Типография ───────────────────────────────────────────── */
    h1 {
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary);
        font-weight: 800; letter-spacing: -0.03em;
        font-size: 1.8rem !important;
    }

    /* ── Liquid Glass Panel (универсальный) ────────────────────── */
    .lg-panel {
        background: var(--glass-bg-1);
        backdrop-filter: var(--glass-blur-1);
        -webkit-backdrop-filter: var(--glass-blur-1);
        border: 0.5px solid var(--glass-border);
        border-top: 0.5px solid var(--glass-border-hi);
        border-radius: var(--radius-md);
        box-shadow:
            0 8px 32px rgba(0,0,0,0.25),
            inset 0 1px 0 rgba(255,255,255,0.06),
            inset 0 -1px 0 rgba(0,0,0,0.1);
        padding: 1.25rem;
        position: relative;
        overflow: hidden;
    }
    .lg-panel::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1) 30%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.1) 70%, transparent);
    }
    .lg-panel-elevated {
        background: var(--glass-bg-2);
        backdrop-filter: var(--glass-blur-2);
        -webkit-backdrop-filter: var(--glass-blur-2);
        border-top: 0.5px solid rgba(255,255,255,0.2);
        box-shadow:
            0 12px 48px rgba(0,0,0,0.35),
            inset 0 1px 0 rgba(255,255,255,0.1);
    }

    /* ── Header кастомный ─────────────────────────────────────── */
    .yt-hero {
        display: flex; align-items: center; gap: 14px;
        padding: 1rem 0 0.75rem 0;
    }
    .yt-hero-logo {
        width: 44px; height: 44px; border-radius: 12px;
        background: linear-gradient(135deg, #0891B2, #06B6D4);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 18px; color: #080C14;
        box-shadow: 0 4px 16px var(--accent-glow);
        flex-shrink: 0;
    }
    .yt-hero-text h1 {
        margin: 0 !important; padding: 0 !important;
        font-size: 1.65rem !important; line-height: 1.1;
    }
    .yt-hero-text p {
        color: var(--text-muted); font-size: 0.85rem;
        margin: 2px 0 0 0; font-weight: 500;
        letter-spacing: 0.03em;
    }
    .yt-hero-divider {
        height: 1px; margin: 0 0 1rem 0;
        background: linear-gradient(90deg, var(--accent-soft), transparent 80%);
    }

    /* ── Stat cards (заменяют st.metric) ──────────────────────── */
    .yt-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 1rem 0; }
    .yt-stat {
        background: var(--glass-bg-1);
        backdrop-filter: var(--glass-blur-1);
        -webkit-backdrop-filter: var(--glass-blur-1);
        border: 0.5px solid var(--glass-border);
        border-top: 0.5px solid var(--glass-border-hi);
        border-radius: var(--radius-md);
        padding: 16px 18px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05);
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
        position: relative; overflow: hidden;
    }
    .yt-stat::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08) 50%, transparent);
    }
    .yt-stat:hover {
        border-color: var(--glass-border-hi);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .yt-stat .label {
        color: var(--text-muted); font-size: 0.72rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;
    }
    .yt-stat .value {
        color: var(--text-primary); font-size: 1.75rem; font-weight: 800;
        line-height: 1; letter-spacing: -0.02em;
    }
    .yt-stat .sub {
        color: var(--text-muted); font-size: 0.72rem; margin-top: 4px;
    }
    .yt-stat.accent .value { color: var(--accent); }
    .yt-stat.success .value { color: var(--success); }
    .yt-stat.warning .value { color: var(--warning); }
    .yt-stat.error .value { color: var(--error); }

    /* Indicator dot on stat cards */
    .yt-stat .dot {
        width: 6px; height: 6px; border-radius: 50%;
        display: inline-block; margin-right: 6px;
        vertical-align: middle; position: relative; top: -1px;
    }

    /* ── CSS-only radial gauge ────────────────────────────────── */
    .yt-gauge-wrap {
        display: flex; gap: 16px; margin: 1rem 0;
    }
    .yt-gauge-card {
        flex: 1;
        background: var(--glass-bg-1);
        backdrop-filter: var(--glass-blur-1);
        -webkit-backdrop-filter: var(--glass-blur-1);
        border: 0.5px solid var(--glass-border);
        border-top: 0.5px solid var(--glass-border-hi);
        border-radius: var(--radius-md);
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05);
        text-align: center;
        position: relative; overflow: hidden;
    }
    .yt-gauge-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08) 50%, transparent);
    }
    .yt-gauge-card .title {
        font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 16px;
    }
    .yt-gauge {
        width: 120px; height: 120px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto;
        position: relative;
    }
    .yt-gauge .ring {
        position: absolute; inset: 0; border-radius: 50%;
    }
    .yt-gauge .pct {
        font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em;
        position: relative; z-index: 1;
    }
    .yt-gauge .sub-text {
        font-size: 0.72rem; color: var(--text-muted); margin-top: 10px;
    }

    /* ── Sidebar ──────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060D1B 0%, #030712 100%);
        border-right: 0.5px solid var(--glass-border);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #CBD5E1 !important; }

    /* Tooltip — тёмный текст */
    [data-testid="stSidebar"] [data-testid="stTooltipContent"],
    [data-testid="stSidebar"] [data-testid="stTooltipContent"] p,
    [data-testid="stSidebar"] [data-testid="stTooltipContent"] span,
    [data-testid="stSidebar"] div[data-baseweb="tooltip"] span,
    [data-testid="stSidebar"] div[data-baseweb="tooltip"] p,
    div[role="tooltip"] span, div[role="tooltip"] p,
    div[data-baseweb="tooltip"] div span,
    div[data-baseweb="tooltip"] div p { color: #1E293B !important; }

    /* ── Кнопки ───────────────────────────────────────────────── */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0891B2 0%, #06B6D4 50%, #22D3EE 100%);
        border: none; color: #080C14; font-weight: 700; font-size: 1rem;
        padding: 0.6rem 1.8rem; border-radius: var(--radius-sm);
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
        box-shadow: 0 4px 20px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.2);
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 30px rgba(6,182,212,0.4), inset 0 1px 0 rgba(255,255,255,0.3);
        transform: translateY(-2px);
    }
    div.stDownloadButton > button {
        background: var(--glass-bg-2); border: 0.5px solid var(--glass-border);
        color: var(--success); font-weight: 600; border-radius: var(--radius-sm);
        backdrop-filter: var(--glass-blur-1); -webkit-backdrop-filter: var(--glass-blur-1);
        box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
    }
    div.stDownloadButton > button:hover {
        border-color: rgba(52,211,153,0.3);
        box-shadow: 0 4px 20px rgba(52,211,153,0.15);
        transform: translateY(-1px);
    }

    /* ── Стеклянные метрики (fallback если где-то остались) ────── */
    div[data-testid="stMetric"] {
        background: var(--glass-bg-1);
        border: 0.5px solid var(--glass-border);
        border-radius: var(--radius-md); padding: 16px 20px;
        backdrop-filter: var(--glass-blur-1); -webkit-backdrop-filter: var(--glass-blur-1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetric"] label { color: var(--text-muted) !important; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.75rem; font-weight: 800; color: var(--text-primary) !important; }

    /* ── Лог обработки ────────────────────────────────────────── */
    .processing-log {
        background: var(--glass-bg-1);
        border: 0.5px solid var(--glass-border); border-radius: var(--radius-md);
        padding: 16px; font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem; line-height: 1.7;
        max-height: 300px; overflow-y: auto;
        backdrop-filter: var(--glass-blur-1); -webkit-backdrop-filter: var(--glass-blur-1);
    }
    .processing-log::-webkit-scrollbar { width: 5px; }
    .processing-log::-webkit-scrollbar-track { background: transparent; }
    .processing-log::-webkit-scrollbar-thumb { background: rgba(6,182,212,0.2); border-radius: 3px; }

    /* ── Dataframe ────────────────────────────────────────────── */
    div[data-testid="stDataFrame"] {
        border-radius: var(--radius-md); overflow: hidden;
        border: 0.5px solid var(--glass-border);
    }

    /* ── Алерты ───────────────────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: var(--radius-sm);
        backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    }

    /* ── Разделитель ──────────────────────────────────────────── */
    hr { border-color: var(--glass-border); margin: 1.25rem 0; }

    /* ── Табы ─────────────────────────────────────────────────── */
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        color: var(--text-secondary); font-weight: 500; font-size: 0.9rem;
        transition: color 0.2s;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent); font-weight: 700;
    }

    /* ── Expander ─────────────────────────────────────────────── */
    details[data-testid="stExpander"] {
        background: var(--glass-bg-1);
        border: 0.5px solid var(--glass-border); border-radius: var(--radius-sm);
    }

    /* ── Form controls ────────────────────────────────────────── */
    div[data-baseweb="select"] > div {
        border-color: var(--glass-border) !important;
        background: var(--glass-bg-1) !important;
        border-radius: var(--radius-sm) !important;
    }
    div[data-baseweb="select"] > div:hover { border-color: var(--glass-border-hi) !important; }

    /* ── Progress bar ─────────────────────────────────────────── */
    div[data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, #0891B2, var(--accent));
        border-radius: 4px;
    }

    /* ── Section header ───────────────────────────────────────── */
    .yt-section-label {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.12em; color: var(--text-muted);
        margin-bottom: 12px; padding-left: 2px;
    }

    /* ── Animation: fade-in ───────────────────────────────────── */
    @keyframes yt-fadein {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .yt-animate { animation: yt-fadein 0.4s ease-out forwards; }
</style>
""", unsafe_allow_html=True)

# ── Кастомный Header ──────────────────────────────────────────────
st.markdown("""
<div class="yt-hero yt-animate">
    <div class="yt-hero-logo">ЮТ</div>
    <div class="yt-hero-text">
        <h1>ЮрТэг</h1>
        <p>Автоматическая обработка архива документов</p>
    </div>
</div>
<div class="yt-hero-divider"></div>
""", unsafe_allow_html=True)

# ── Классификация замечаний для вкладки «Детали» ────────────────

def _classify_warning(w: str) -> tuple[str, str, str, str, str, str]:
    """Возвращает (title, icon, color, bg, border, tip) для замечания."""
    wl = w.lower()

    # --- L1: пустые обязательные поля ---
    if w.startswith("L1"):
        if "тип документа" in wl or "contract_type" in wl:
            return ("Не определён тип", "📄", "#854d0e", "#fef9c3", "#F59E0B",
                    "AI не смог определить тип документа. Проверьте, есть ли в файле заголовок или преамбула.")
        if "контрагент" in wl or "counterparty" in wl:
            return ("Не найден контрагент", "👤", "#854d0e", "#fef9c3", "#F59E0B",
                    "В тексте не удалось найти название второй стороны. Возможно, документ — внутренний или шаблон.")
        if "предмет" in wl or "subject" in wl:
            return ("Не определён предмет", "📋", "#854d0e", "#fef9c3", "#F59E0B",
                    "AI не извлёк предмет документа. Проверьте вручную — возможно, текст извлечён некорректно.")
        if "формат даты" in wl or "date" in wl:
            return ("Ошибка формата даты", "📅", "#854d0e", "#fef9c3", "#F59E0B",
                    "Дата не в формате ГГГГ-ММ-ДД. AI мог неправильно распознать дату из текста.")
        if "confidence" in wl:
            return ("Ошибка уверенности AI", "🎯", "#854d0e", "#fef9c3", "#F59E0B",
                    "Значение confidence вне допустимого диапазона. Технический сбой AI-модели.")
        return ("Пустое поле", "⚠️", "#854d0e", "#fef9c3", "#F59E0B",
                "Обязательное поле не заполнено. Информация может отсутствовать в документе.")

    # --- L2: логика и формат ---
    if w.startswith("L2"):
        if "в будущем" in wl:
            return ("Дата в будущем", "📅", "#7c2d12", "#fee2e2", "#EF4444",
                    "Дата подписания позже сегодняшнего дня. Если это не ошибка — возможно, договор ещё не подписан.")
        if "подозрительно стар" in wl:
            return ("Подозрительная дата", "📅", "#7c2d12", "#fee2e2", "#EF4444",
                    "Дата до 2000 года — необычно для активного договора. Проверьте корректность.")
        if "позже даты окончания" in wl or "начала" in wl and "окончания" in wl:
            return ("Даты перепутаны", "🔄", "#7c2d12", "#fee2e2", "#EF4444",
                    "Дата начала позже даты окончания. Скорее всего, AI перепутал поля местами.")
        if "долгий срок" in wl:
            return ("Очень долгий срок", "⏳", "#854d0e", "#fef9c3", "#F59E0B",
                    "Срок действия более 50 лет — необычно. Проверьте даты вручную.")
        if "нестандартный тип" in wl:
            return ("Нестандартный тип", "🏷️", "#854d0e", "#fef9c3", "#F59E0B",
                    "Тип документа не совпал с известными категориями. Это нормально для редких типов.")
        if "аномально большая сумма" in wl:
            return ("Огромная сумма", "💰", "#7c2d12", "#fee2e2", "#EF4444",
                    "Сумма свыше 10 млрд — проверьте, нет ли лишних нулей или ошибки распознавания.")
        if "аномально малая сумма" in wl:
            return ("Подозрительно малая сумма", "💰", "#854d0e", "#fef9c3", "#F59E0B",
                    "Сумма менее 1000 — возможно, AI ошибся или указана неполная сумма.")
        if "не содержит чисел" in wl:
            return ("Сумма не распознана", "💰", "#854d0e", "#fef9c3", "#F59E0B",
                    "В поле суммы нет числовых значений. Проверьте, была ли сумма указана в документе.")
        if "короткий предмет" in wl:
            return ("Слишком короткий предмет", "📝", "#854d0e", "#fef9c3", "#F59E0B",
                    "Предмет документа подозрительно краткий. Возможно, AI извлёк не тот фрагмент.")
        if "длинный предмет" in wl:
            return ("Слишком длинный предмет", "📝", "#854d0e", "#fef9c3", "#F59E0B",
                    "AI скопировал слишком большой кусок текста как предмет.")
        if "невалидный ИНН" in wl:
            return ("Ошибка в ИНН", "🔢", "#7c2d12", "#fee2e2", "#EF4444",
                    "Контрольная сумма ИНН не сходится — опечатка или ошибка в документе.")
        if "стороны" in wl and "совпадают" in wl:
            return ("Стороны совпадают", "👥", "#7c2d12", "#fee2e2", "#EF4444",
                    "Обе стороны документа одинаковые. AI мог ошибиться при извлечении.")
        return ("Проблема с данными", "⚠️", "#854d0e", "#fef9c3", "#F59E0B",
                "Обнаружена логическая ошибка. Рекомендуется проверить файл вручную.")

    # --- L3: уверенность AI ---
    if w.startswith("L3"):
        if "низкая уверенность" in wl:
            return ("Низкая уверенность AI", "🤖", "#1e3a5f", "#dbeafe", "#3B82F6",
                    "AI сомневается в результатах. Текст мог быть сложным, размытым или неполным.")
        if "средняя уверенность" in wl:
            return ("Средняя уверенность AI", "🤖", "#1e3a5f", "#dbeafe", "#60A5FA",
                    "AI частично уверен. Основные данные скорее верны, но детали стоит перепроверить.")
        if "галлюцинац" in wl and "контрагент" in wl:
            return ("Подозрение на выдумку AI", "🧠", "#7c2d12", "#fee2e2", "#EF4444",
                    "Контрагент похож на шаблонное или выдуманное значение (ООО Ромашка и т.п.).")
        if "все три даты совпадают" in wl:
            return ("Все даты одинаковые", "📅", "#1e3a5f", "#dbeafe", "#3B82F6",
                    "Подписание, начало и окончание — одна дата. AI мог скопировать одну дату во все поля.")
        return ("Внимание AI", "🤖", "#1e3a5f", "#dbeafe", "#3B82F6",
                "AI-модель не уверена в результатах. Рекомендуется проверить.")

    # --- L4: кросс-файловые ---
    if w.startswith("L4"):
        if "дубликат" in wl:
            return ("Возможный дубликат", "📑", "#3b0764", "#f3e8ff", "#A855F7",
                    "Найден файл с такими же контрагентом, датой и суммой. Возможно, это одна и та же версия.")
        if "совпадающие даты" in wl:
            return ("Совпадающие даты", "📅", "#3b0764", "#f3e8ff", "#A855F7",
                    "У нескольких файлов одинаковые даты начала и окончания — возможно, копии шаблона.")
        if "определены как" in wl:
            return ("Однотипная классификация", "🏷️", "#3b0764", "#f3e8ff", "#A855F7",
                    "Больше половины файлов — одного типа. Возможно, AI классифицирует однообразно.")
        if "предупреждения" in wl or "системные проблемы" in wl:
            return ("Много предупреждений", "📊", "#3b0764", "#f3e8ff", "#A855F7",
                    "Более 30% файлов с замечаниями — возможно, проблемы с качеством документов или OCR.")
        return ("Кросс-файловая проверка", "📑", "#3b0764", "#f3e8ff", "#A855F7",
                "Обнаружено совпадение между файлами. Стоит проверить вручную.")

    # --- L5: AI-верификация ---
    if w.startswith("L5"):
        if "исправил" in wl:
            return ("AI исправил данные", "🔧", "#065f46", "#d1fae5", "#10B981",
                    "AI перепроверил результат и внёс исправление. Проверьте, корректно ли.")
        if "подтвердил" in wl:
            return ("AI подтвердил", "✔️", "#065f46", "#d1fae5", "#10B981",
                    "AI перепроверил данные и считает их корректными.")
        if "неточными" in wl:
            return ("AI сомневается", "🔍", "#7c2d12", "#fee2e2", "#EF4444",
                    "AI перепроверил и считает данные неточными, но не смог предложить конкретные исправления.")
        return ("AI-верификация", "🔍", "#065f46", "#d1fae5", "#10B981",
                "Результат дополнительной проверки AI-моделью.")

    # Неизвестный уровень
    return ("Замечание", "ℹ️", "#854d0e", "#fef9c3", "#F59E0B",
            "Рекомендуется проверить файл вручную.")


# ── Sidebar: настройки ──────────────────────────────────────────

_ANON_HELP = {
    "ФИО": "Фамилии, имена, отчества физических лиц. Заменяются на [ФИО_1], [ФИО_2] и т.д.",
    "ТЕЛЕФОН": "Мобильные и стационарные номера телефонов в любом формате.",
    "EMAIL": "Адреса электронной почты, включая с кириллическими доменами.",
    "ПАСПОРТ": "Серия и номер паспорта РФ (исключая «технический паспорт» и т.п.).",
    "СНИЛС": "Страховой номер индивидуального лицевого счёта (11 цифр с проверкой).",
    "ИНН": "ИНН физлиц (12 цифр) и юрлиц (10 цифр с контекстом).",
    "ОГРН": "Основной государственный регистрационный номер (13 или 15 цифр).",
    "КПП": "Код причины постановки на учёт (9 цифр с контекстом).",
    "СЧЁТ": "Расчётные, корреспондентские и лицевые счета (20 цифр).",
}

# ── Мультиклиентский режим ───────────────────────────────────────
client_manager = ClientManager()

# ── Глобальный объект настроек ────────────────────────────────────
# Используется в sidebar и передаётся в Controller при обработке.
# active_provider персистируется в JSON-файле (D-08) — переживает перезапуск.

_SETTINGS_FILE = Path.home() / ".yurteg" / "settings.json"


def _load_settings() -> dict:
    """Загружает персистентные настройки из JSON-файла."""
    try:
        if _SETTINGS_FILE.exists():
            import json as _json
            return _json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_settings(settings: dict) -> None:
    """Сохраняет персистентные настройки в JSON-файл."""
    try:
        import json as _json
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(
            _json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning("Не удалось сохранить настройки: %s", _e)


_persisted = _load_settings()
config = Config()
# Восстановить active_provider из файла (если был сохранён ранее)
if "active_provider" in _persisted:
    config.active_provider = _persisted["active_provider"]
if "telegram_server_url" in _persisted:
    config.telegram_server_url = _persisted["telegram_server_url"]
if "telegram_chat_id" in _persisted:
    config.telegram_chat_id = _persisted["telegram_chat_id"]

with st.sidebar:
    # --- Клиент ---
    st.markdown("### Клиент")
    _clients = client_manager.list_clients()
    _selected_client = st.sidebar.selectbox(
        "Активный реестр",
        _clients,
        index=0,
        key="active_client",
        label_visibility="collapsed",
    )

    with st.sidebar.expander("Управление клиентами", expanded=False):
        _new_name = st.text_input("Название нового клиента", key="new_client_name")
        if st.button("Создать", key="create_client_btn") and _new_name:
            client_manager.add_client(_new_name)
            st.rerun()

    st.markdown("---")

    with st.sidebar.expander("Провайдер", expanded=False):
        _provider_options = {
            "Локальная модель (QWEN 1.5B)": "ollama",
            "ZAI (GLM-4.7, облако)": "zai",
            "OpenRouter (облако)": "openrouter",
        }
        _current_idx = list(_provider_options.values()).index(config.active_provider) \
            if config.active_provider in _provider_options.values() else 0
        _selected_provider_label = st.selectbox(
            "AI-провайдер",
            list(_provider_options.keys()),
            index=_current_idx,
            key="provider_select",
            label_visibility="collapsed",
        )
        _new_provider = _provider_options[_selected_provider_label]
        if _new_provider != config.active_provider:
            config.active_provider = _new_provider
            # Сохранить выбор в файл — переживает перезапуск приложения (D-08)
            _cur_settings = _load_settings()
            _cur_settings["active_provider"] = _new_provider
            _save_settings(_cur_settings)
            # Предупреждение об отсутствии API-ключа для облачных провайдеров
            if _new_provider in ("zai", "openrouter"):
                import os as _os_prov
                _has_key = bool(
                    _os_prov.environ.get("ZHIPU_API_KEY", "")
                    or _os_prov.environ.get("ZAI_API_KEY", "")
                    or _os_prov.environ.get("OPENROUTER_API_KEY", "")
                )
                if not _has_key:
                    st.warning("API-ключ не найден. Установите ZHIPU_API_KEY или OPENROUTER_API_KEY.")
            st.rerun()

    st.markdown("---")

    st.markdown(
        '<div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:#475569;margin-bottom:4px;">Настройки</div>',
        unsafe_allow_html=True,
    )

    tab_main, tab_anon = st.tabs(["📂 Структура", "🔒 Анонимизация"])

    with tab_main:
        # Группировка
        grouping_options = {
            "По типу + контрагенту": "both",
            "По типу документа": "type",
            "По контрагенту": "counterparty",
        }
        grouping_label = st.radio(
            "Группировка файлов",
            list(grouping_options.keys()),
            index=0,
            help="Определяет структуру папок при сортировке: "
            "«По типу + контрагенту» создаёт вложенные папки "
            "(Документы / Договор аренды / ООО Ромашка), "
            "«По типу» — только по типу документа, "
            "«По контрагенту» — только по названию контрагента.",
        )
        grouping = grouping_options[grouping_label]

        st.markdown("---")
        force_reprocess = st.checkbox(
            "Переобработать все файлы",
            value=st.session_state.get("force_reprocess", False),
            help="Игнорировать кэш: обработать все файлы заново, "
            "даже ранее обработанные.",
        )

        ai_verify = st.checkbox(
            "AI-верификация (L5)",
            value=False,
            help="AI перепроверяет свои результаты для файлов с замечаниями. "
            "Повышает точность, но добавляет ~2-3 сек на каждый "
            "проблемный файл (дополнительный API-запрос).",
        )

        st.markdown("---")
        warning_days = st.selectbox(
            "Предупреждать о сроках за",
            options=[30, 60, 90],
            index=0,
            format_func=lambda d: f"{d} дней",
            key="warning_days_threshold",
        )
        st.session_state["warning_days_threshold"] = warning_days

    with tab_anon:
        st.caption("Выберите, какие персональные данные маскировать "
                   "перед отправкой текста в AI-модель.")
        anon_enabled = set()
        for key, desc in ENTITY_TYPES.items():
            if st.checkbox(
                desc,
                value=True,
                key=f"anon_{key}",
                help=_ANON_HELP.get(key) or None,
            ):
                anon_enabled.add(key)
        if len(anon_enabled) < len(ENTITY_TYPES):
            st.warning(
                "Немаскированные данные будут отправлены в AI как есть. "
                "Это может повысить точность, но снижает защиту ПД.",
                icon="⚠️",
            )

    # --- Telegram ---
    with st.sidebar.expander("Telegram", expanded=False):
        tg_server = st.text_input(
            "URL сервера бота",
            value=config.telegram_server_url,
            key="tg_server_url",
            placeholder="https://yurteg-bot.railway.app",
        )
        config.telegram_server_url = tg_server

        if config.telegram_chat_id > 0:
            st.success(f"Привязан (chat_id: {config.telegram_chat_id})")
        else:
            tg_code = st.text_input(
                "Код привязки",
                max_chars=6,
                key="tg_bind_code",
                help="Введите /start в боте @YurTagBot, получите код",
            )
            if st.button("Привязать", key="tg_bind_btn") and tg_code and tg_server:
                from services.telegram_sync import TelegramSync
                _sync_bind = TelegramSync(tg_server, 0)
                _chat_id = _sync_bind.bind(tg_code)
                if _chat_id:
                    config.telegram_chat_id = _chat_id
                    st.session_state["telegram_chat_id"] = _chat_id
                    st.session_state["telegram_server_url"] = tg_server
                    st.success(f"Привязано! chat_id: {_chat_id}")
                    st.rerun()
                else:
                    st.error("Код не найден или истёк. Попробуйте заново через /start.")

    # Внизу sidebar — статус API + версия (всегда видны, вне табов)
    st.markdown("---")

    # Статус API-ключа (из .env) — показываем только если нет
    api_key = os.environ.get("ZHIPU_API_KEY", "") or os.environ.get(
        "OPENROUTER_API_KEY", ""
    )
    if not api_key:
        if _CLOUD_MODE:
            st.error(
                "API-ключ не найден. Настройте ZHIPU_API_KEY "
                "в Streamlit Secrets.",
                icon="🔑",
            )
        else:
            st.error(
                "API-ключ не найден. Добавьте ZHIPU_API_KEY или "
                "OPENROUTER_API_KEY в файл .env",
                icon="🔑",
            )

    st.markdown(
        '<div style="text-align:center;padding:6px 0;">'
        '<span style="color:#334155;font-size:0.65rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;">'
        "ЮрТэг v0.4</span></div>",
        unsafe_allow_html=True,
    )

# ── Основная область ────────────────────────────────────────────

# --- Fetch & process Telegram queue (INTG-01) ---
_tg_server = st.session_state.get("telegram_server_url", "") or st.session_state.get("tg_server_url", "")
_tg_chat_id = st.session_state.get("telegram_chat_id", 0)

if not st.session_state.get("tg_queue_fetched") and _tg_server and _tg_chat_id and _tg_chat_id > 0:
    from services.telegram_sync import TelegramSync
    _sync = TelegramSync(_tg_server, _tg_chat_id)
    _tg_dest = Path(tempfile.mkdtemp(prefix="yurteg_tg_"))
    _tg_files = _sync.fetch_queue(_tg_dest)
    if _tg_files:
        st.info(f"Получено {len(_tg_files)} файлов из Telegram. Обработка...")
        # Обработать файлы через существующий пайплайн
        _tg_config = Config()
        _tg_collected: list = []
        _tg_stats = pipeline_service.process_archive(
            source_dir=_tg_dest,
            config=_tg_config,
            on_file_done=lambda r: _tg_collected.append(r),
        )
        _tg_done = _tg_stats.get("done", 0)
        _tg_errors = _tg_stats.get("errors", 0)
        _tg_total = _tg_stats.get("total", len(_tg_files))
        # Отправить карточку с результатами обратно в Telegram
        _tg_summary = f"Обработано {_tg_done} из {_tg_total} файлов."
        if _tg_errors:
            _tg_summary += f" Ошибок: {_tg_errors}."
        _sync.notify_processed(_tg_chat_id, _tg_summary)
        st.success(
            f"Telegram: обработано {_tg_done} файлов"
            + (f", ошибок: {_tg_errors}" if _tg_errors else "")
        )
        # Автопривязка для Telegram-файлов (PROF-01)
        _tg_clients = client_manager.list_clients()
        if _tg_collected and set(_tg_clients) != {ClientManager.DEFAULT_CLIENT}:
            from controller import auto_bind_results
            _tg_bind = auto_bind_results(_tg_collected, client_manager)
            st.session_state["auto_bind_summary"] = _tg_bind
    st.session_state["tg_queue_fetched"] = True


def _select_folder() -> str:
    """Открывает нативный диалог выбора папки (Finder на macOS)."""
    if _DESKTOP_MODE:
        # В десктопном режиме используем osascript (без tkinter)
        import subprocess
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'POSIX path of (choose folder with prompt '
                 '"Выберите папку с документами")'],
                capture_output=True, text=True, timeout=120,
            )
            return result.stdout.strip()
        except Exception:
            return ""
    if not _HAS_TK:
        return ""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    folder = filedialog.askdirectory(
        master=root, title="Выберите папку с документами"
    )
    root.destroy()
    return folder


# Быстрый выбор тестовой папки
_test_data_path = Path(__file__).parent / "tests" / "test_data"
if _test_data_path.is_dir():
    _test_file_count = sum(
        1 for f in _test_data_path.glob("*")
        if f.suffix.lower() in (".pdf", ".docx")
    )
    if st.button(
        f"Тестовая папка ({_test_file_count} документов)",
        help="Загрузить тестовые файлы для демонстрации. "
        "Автоматически включает режим переобработки.",
    ):
        if _CLOUD_MODE:
            # В облаке: копируем тестовые файлы во временную папку
            import shutil
            _cloud_test = Path(tempfile.mkdtemp(prefix="yurteg_test_"))
            for _tf in _test_data_path.glob("*"):
                if _tf.suffix.lower() in (".pdf", ".docx"):
                    shutil.copy2(_tf, _cloud_test / _tf.name)
            st.session_state["source_dir"] = str(_cloud_test)
        else:
            # Десктоп: используем напрямую (или копируем из .app бандла)
            _use_path = _test_data_path
            if "/Applications/" in str(_test_data_path) or ".app/" in str(_test_data_path):
                import shutil
                _writable_test = Path.home() / "Documents" / "ЮрТэг_Тест"
                if _writable_test.exists():
                    shutil.rmtree(_writable_test)
                shutil.copytree(_test_data_path, _writable_test)
                _use_path = _writable_test
            st.session_state["source_dir"] = str(_use_path)
        st.session_state["force_reprocess"] = True
        st.rerun()

if _CLOUD_MODE:
    # ── Облачный режим: загрузка файлов через drag & drop ──
    uploaded_files = st.file_uploader(
        "Загрузите PDF/DOCX файлы",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="Перетащите файлы сюда или нажмите Browse",
    )
    if uploaded_files:
        if "upload_dir" not in st.session_state:
            st.session_state["upload_dir"] = Path(tempfile.mkdtemp(prefix="yurteg_upload_"))
        _upload_dir = st.session_state["upload_dir"]
        for uf in uploaded_files:
            (_upload_dir / uf.name).write_bytes(uf.getbuffer())
        st.session_state["source_dir"] = str(_upload_dir)

    source_dir_str = st.session_state.get("source_dir", "")
else:
    # ── Десктопный режим: поле ввода пути + кнопка Обзор ──
    col_path, col_browse = st.columns([5, 1])
    with col_path:
        source_dir_str = st.text_input(
            "Папка с документами",
            value=st.session_state.get("source_dir", ""),
            placeholder="/Users/you/Documents/Contracts",
            help="Полный путь к папке с PDF/DOCX файлами",
        )
    with col_browse:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Обзор"):
            folder = _select_folder()
            if folder:
                st.session_state["source_dir"] = folder
                st.rerun()

source_dir = Path(source_dir_str) if source_dir_str else None
dir_valid = source_dir is not None and source_dir.is_dir()

if source_dir_str and not dir_valid:
    st.error("Папка не найдена. Проверьте путь.")

# Предупреждение о файлах
file_count = 0
if dir_valid:
    config_preview = Config()
    file_count = sum(
        1
        for f in source_dir.rglob("*")
        if f.suffix.lower() in config_preview.supported_extensions
        and f.stat().st_size <= config_preview.max_file_size_mb * 1024 * 1024
    )
    if file_count == 0:
        st.warning("В папке нет PDF/DOCX файлов.")
    elif file_count > 20:
        st.info(
            f"Найдено **{file_count}** файлов. "
            f"Примерная стоимость API: ~${file_count * 0.005:.2f}. "
            f"Обработка может занять несколько минут."
        )
    else:
        st.success(f"Найдено **{file_count}** файлов")

# ── Автозагрузка предыдущих результатов из БД ──────────────────
if dir_valid and not st.session_state.get("show_results") and not _CLOUD_MODE:
    _possible_db = source_dir.parent / Config().output_folder_name / "yurteg.db"
    if _possible_db.exists():
        from modules.database import Database as _DBCheck
        with _DBCheck(_possible_db) as _db_check:
            _prev_stats = _db_check.get_stats()
        if _prev_stats["done"] > 0:
            st.info(
                f"Найдены результаты предыдущей обработки: "
                f"**{_prev_stats['done']}** файлов."
            )
            if st.button("Показать результаты"):
                st.session_state["output_dir"] = _possible_db.parent
                st.session_state["report_path"] = (
                    _possible_db.parent / "Реестр_договоров.xlsx"
                )
                st.session_state["show_results"] = True
                st.rerun()

# ── Кнопка запуска ──────────────────────────────────────────────

can_start = dir_valid and bool(api_key) and file_count > 0

if not api_key and dir_valid and file_count > 0:
    if _CLOUD_MODE:
        st.warning("API-ключ не задан. Настройте ZHIPU_API_KEY в Streamlit Secrets.")
    else:
        st.warning("API-ключ не задан. Добавьте ZHIPU_API_KEY или OPENROUTER_API_KEY в файл `.env`")

if st.button("Начать обработку", type="primary", disabled=not can_start):
    config = Config()
    # Применить выбранный провайдер из sidebar (персистируется в settings.json)
    config.active_provider = _persisted.get("active_provider", config.active_provider)
    # Настройки анонимизации из sidebar
    if len(anon_enabled) < len(ENTITY_TYPES):
        config.anonymize_types = anon_enabled
    else:
        config.anonymize_types = None  # Все типы → маскировать всё

    # AI-верификация L5
    if ai_verify:
        config.validation_mode = "selective"

    # Проверить ключ
    with st.spinner("Проверка API-ключа..."):
        key_ok = verify_api_key(config)
    if not key_ok:
        if _CLOUD_MODE:
            st.error("API-ключ недействителен. Проверьте Streamlit Secrets.")
        else:
            st.error("API-ключ недействителен. Проверьте .env файл.")
        st.stop()

    # Контейнеры для обновления
    progress_bar = st.progress(0, text="Подготовка...")
    log_placeholder = st.empty()
    log_lines: list[str] = []
    _start_time = time.time()
    _collected_results: list = []  # накапливаем для auto_bind_results (PROF-01)

    def on_progress(current: int, total: int, message: str) -> None:
        if total > 0:
            elapsed = time.time() - _start_time
            pct = min(current / total, 1.0)
            if current > 0:
                avg = elapsed / current
                remaining = avg * (total - current)
                eta_text = f"{message}  |  {elapsed:.0f}с / ~{remaining:.0f}с осталось"
            else:
                eta_text = message
            progress_bar.progress(pct, text=eta_text)
        else:
            progress_bar.progress(0, text=message)

    def on_file_done(result) -> None:
        _collected_results.append(result)
        if result.status == "done":
            v = result.validation
            if v and v.status == "warning":
                icon, color = "⚠️", "#FBBF24"
            elif v and v.status in ("unreliable", "error"):
                icon, color = "🔶", "#F87171"
            else:
                icon, color = "✅", "#34D399"
            meta = ""
            if result.metadata:
                parts = []
                if result.metadata.contract_type:
                    parts.append(result.metadata.contract_type)
                if result.metadata.counterparty:
                    parts.append(result.metadata.counterparty)
                if parts:
                    meta = f' <span style="color:#64748B">— {", ".join(parts)}</span>'
            log_lines.append(
                f'<div style="padding:3px 0;color:{color}">'
                f"{icon} {result.file_info.filename}{meta}</div>"
            )
        else:
            log_lines.append(
                f'<div style="padding:3px 0;color:#F87171">'
                f"❌ {result.file_info.filename} — "
                f"{result.error_message}</div>"
            )
        log_placeholder.markdown(
            '<div class="processing-log">'
            + "\n".join(log_lines[-30:])
            + "</div>",
            unsafe_allow_html=True,
        )

    # Запуск
    _cloud_output = None
    if _CLOUD_MODE:
        _cloud_output = Path(tempfile.mkdtemp(prefix="yurteg_out_"))

    try:
        stats = pipeline_service.process_archive(
            source_dir=source_dir,
            config=config,
            grouping=grouping,
            force_reprocess=force_reprocess,
            on_progress=on_progress,
            on_file_done=on_file_done,
            output_dir_override=_cloud_output,
        )
    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.stop()

    _total_time = time.time() - _start_time
    progress_bar.progress(1.0, text="Готово!")

    # Success-banner — кастомные stat-cards
    _avg_speed = _total_time / max(stats['done'], 1)
    _err_cls = "error" if stats["errors"] > 0 else "success"
    st.markdown(f"""
    <div class="yt-stats yt-animate">
        <div class="yt-stat success">
            <div class="label"><span class="dot" style="background:var(--success)"></span>Обработано</div>
            <div class="value">{stats['done']}</div>
        </div>
        <div class="yt-stat {_err_cls}">
            <div class="label"><span class="dot" style="background:var(--{_err_cls})"></span>Ошибки</div>
            <div class="value">{stats['errors']}</div>
        </div>
        <div class="yt-stat">
            <div class="label"><span class="dot" style="background:var(--text-muted)"></span>Пропущено</div>
            <div class="value">{stats['skipped']}</div>
        </div>
        <div class="yt-stat accent">
            <div class="label"><span class="dot" style="background:var(--accent)"></span>Время</div>
            <div class="value">{_total_time:.1f}<span style="font-size:0.5em;font-weight:500;color:var(--text-muted)"> сек</span></div>
            <div class="sub">~{_avg_speed:.1f} сек/файл</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Автопривязка к клиентам (PROF-01) ---
    _all_clients = client_manager.list_clients()
    _has_extra_clients = set(_all_clients) != {ClientManager.DEFAULT_CLIENT}
    if _collected_results and _has_extra_clients:
        from controller import auto_bind_results
        _bind_summary = auto_bind_results(_collected_results, client_manager)
        st.session_state["auto_bind_summary"] = _bind_summary

        if _bind_summary["bindings"] or _bind_summary["unmatched"]:
            st.subheader("Привязка к клиентам")

            for _cl_name, _cl_files in _bind_summary["bindings"].items():
                st.success(f"{len(_cl_files)} док → {_cl_name}")
                for _f in _cl_files:
                    st.caption(f"  {_f}")

            if _bind_summary["bindings"]:
                if st.button("Подтвердить привязку", key="confirm_bind_btn", type="primary"):
                    from controller import move_record_to_client
                    from modules.database import Database

                    _src_db_path = client_manager.get_db_path(_selected_client)
                    _moved = 0
                    _move_errors = 0

                    with Database(_src_db_path) as _from_db:
                        _all_src = _from_db.get_all_results()
                        _filename_to_id = {r["filename"]: r["id"] for r in _all_src}

                        for _cl_name, _cl_files in _bind_summary["bindings"].items():
                            _dest_db_path = client_manager.get_db_path(_cl_name)
                            with Database(_dest_db_path) as _to_db:
                                for _fname in _cl_files:
                                    _rid = _filename_to_id.get(_fname)
                                    if _rid and move_record_to_client(_rid, _from_db, _to_db):
                                        _moved += 1
                                    else:
                                        _move_errors += 1

                    if _moved:
                        st.success(f"Перемещено {_moved} документов")
                    if _move_errors:
                        st.warning(f"Не удалось переместить {_move_errors} документов")
                    if _moved:
                        st.rerun()

            if _bind_summary["unmatched"]:
                st.warning(f"{len(_bind_summary['unmatched'])} док → не определено")
                for _f in _bind_summary["unmatched"]:
                    _col1, _col2 = st.columns([3, 1])
                    _col1.caption(f"  {_f}")
                    _assign = _col2.selectbox(
                        "Клиент",
                        ["---"] + client_manager.list_clients() + ["+ Новый клиент"],
                        key=f"assign_{_f}",
                        label_visibility="collapsed",
                    )
    else:
        st.session_state.pop("auto_bind_summary", None)

    # Сохранить для таблицы
    st.session_state["output_dir"] = stats["output_dir"]
    st.session_state["report_path"] = stats["report_path"]
    st.session_state["show_results"] = True
    st.session_state["processing_time"] = _total_time
    st.session_state["force_reprocess"] = False

# ── Результаты: Табы ───────────────────────────────────────────

if st.session_state.get("show_results"):
    output_dir = st.session_state.get("output_dir")
    report_path = st.session_state.get("report_path")

    st.divider()

    from modules.database import Database

    db_path = client_manager.get_db_path(_selected_client)
    if db_path.exists():
        with Database(db_path) as db:
            all_results = db.get_all_results()

        # --- Startup notification (INTG-04) ---
        if not st.session_state.get("startup_toast_shown"):
            _toast_warning_days = st.session_state.get("warning_days_threshold", 30)
            with Database(db_path) as _db_toast:
                _alerts = get_attention_required(_db_toast, _toast_warning_days)
            if _alerts:
                _expiring = sum(1 for a in _alerts if a.computed_status == "expiring")
                _expired = sum(1 for a in _alerts if a.computed_status == "expired")
                _parts = []
                if _expiring:
                    _parts.append(f"{_expiring} истекают скоро")
                if _expired:
                    _parts.append(f"{_expired} уже истекли")
                st.toast(f"Внимание: {', '.join(_parts)}", icon="warning")
            st.session_state["startup_toast_shown"] = True

        # --- Push deadline data to Telegram bot server (INTG-02) ---
        if not st.session_state.get("deadlines_pushed") and _tg_server and _tg_chat_id and _tg_chat_id > 0:
            from services.telegram_sync import TelegramSync
            _dl_sync = TelegramSync(_tg_server, _tg_chat_id)
            # _alerts может не существовать, если startup_toast_shown уже был True
            try:
                _push_alerts = _alerts  # type: ignore[name-defined]
            except NameError:
                _toast_wd = st.session_state.get("warning_days_threshold", 30)
                with Database(db_path) as _db_dl:
                    _push_alerts = get_attention_required(_db_dl, _toast_wd)
            if _push_alerts:
                _dl_data = [
                    {
                        "filename": a.filename,
                        "counterparty": a.counterparty,
                        "contract_type": a.contract_type,
                        "date_end": a.date_end,
                        "days_until_expiry": a.days_until_expiry,
                        "computed_status": a.computed_status,
                    }
                    for a in _push_alerts
                ]
                _dl_sync.push_deadlines(_dl_data)
            else:
                # Нет алертов — очистить устаревшие данные на сервере
                _dl_sync.push_deadlines([])
            st.session_state["deadlines_pushed"] = True

        if all_results:
            df = pd.DataFrame(all_results)

            # ── Панель «требует внимания» ────────────────────────
            _warning_days = st.session_state.get("warning_days_threshold", 30)
            with Database(db_path) as _db_alert:
                alerts = get_attention_required(_db_alert, _warning_days)
            if alerts:
                with st.expander(f"⚠ Требует внимания — {len(alerts)} договор(ов)", expanded=True):
                    for alert in alerts:
                        icon, label, color = STATUS_LABELS.get(
                            alert.computed_status, ("?", alert.computed_status, "#9ca3af")
                        )
                        days_text = (
                            f"истёк {abs(alert.days_until_expiry)} дн. назад"
                            if alert.days_until_expiry < 0
                            else f"истекает через {alert.days_until_expiry} дн."
                        )
                        st.markdown(
                            f'<span style="color:{color}">{icon}</span> '
                            f'**{alert.filename}** — {alert.counterparty or "нет контрагента"} '
                            f'· {days_text}',
                            unsafe_allow_html=True,
                        )

            tab_summary, tab_registry, tab_details, tab_calendar, tab_templates = st.tabs(
                ["Сводка", "Реестр", "Детали", "Платёжный календарь", "Шаблоны"]
            )

            # ── Таб: Сводка ─────────────────────────────────────
            with tab_summary:
                # Подсчёты для gauge
                total_validated = len(df[df["validation_status"].notna()])
                ok_count = len(df[df["validation_status"] == "ok"])
                quality_pct = int(round(ok_count / max(total_validated, 1) * 100))
                q_color = "#34D399" if quality_pct >= 80 else "#FBBF24" if quality_pct >= 50 else "#F87171"

                avg_pct = 0
                g_color = "#475569"
                if "confidence" in df.columns:
                    conf_values = df["confidence"].dropna()
                    if not conf_values.empty:
                        avg_conf = float(conf_values.mean())
                        avg_pct = int(round(avg_conf * 100))
                        g_color = "#34D399" if avg_conf >= 0.8 else "#FBBF24" if avg_conf >= 0.5 else "#F87171"

                # Типы документов — stat-badges
                type_counts = df["contract_type"].dropna().value_counts()
                _type_colors = ["#06B6D4", "#8B5CF6", "#F59E0B", "#10B981", "#EC4899", "#3B82F6", "#EF4444", "#14B8A6"]
                _type_badges = ""
                for i, (t, c) in enumerate(type_counts.items()):
                    _tc = _type_colors[i % len(_type_colors)]
                    _type_badges += f'<span style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);border:0.5px solid rgba(255,255,255,0.08);border-radius:20px;padding:6px 14px 6px 10px;font-size:0.82rem;color:#CBD5E1;"><span style="width:8px;height:8px;border-radius:50%;background:{_tc};flex-shrink:0;"></span>{t} <b style="color:{_tc}">{c}</b></span> '

                # CSS-only gauge + type badges — всё в одном HTML-блоке
                st.markdown(f"""
                <div class="yt-section-label">Сводка обработки</div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
                    {_type_badges}
                </div>
                <div class="yt-gauge-wrap yt-animate">
                    <div class="yt-gauge-card">
                        <div class="title">Качество данных</div>
                        <div class="yt-gauge">
                            <div class="ring" style="background:conic-gradient({q_color} 0% {quality_pct}%, rgba(255,255,255,0.06) {quality_pct}% 100%); -webkit-mask:radial-gradient(farthest-side, transparent calc(100% - 8px), #000 calc(100% - 7px)); mask:radial-gradient(farthest-side, transparent calc(100% - 8px), #000 calc(100% - 7px)); border-radius:50%;"></div>
                            <div class="pct" style="color:{q_color}">{quality_pct}%</div>
                        </div>
                        <div class="sub-text">{ok_count} из {total_validated} без замечаний</div>
                    </div>
                    <div class="yt-gauge-card">
                        <div class="title">Уверенность AI</div>
                        <div class="yt-gauge">
                            <div class="ring" style="background:conic-gradient({g_color} 0% {avg_pct}%, rgba(255,255,255,0.06) {avg_pct}% 100%); -webkit-mask:radial-gradient(farthest-side, transparent calc(100% - 8px), #000 calc(100% - 7px)); mask:radial-gradient(farthest-side, transparent calc(100% - 8px), #000 calc(100% - 7px)); border-radius:50%;"></div>
                            <div class="pct" style="color:{g_color}">{avg_pct}%</div>
                        </div>
                        <div class="sub-text">средняя уверенность</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


            # ── Таб: Реестр ─────────────────────────────────────
            with tab_registry:
                # ── Computed status для всех договоров ──
                _reg_warning_days = st.session_state.get("warning_days_threshold", 30)
                status_sql = get_computed_status_sql(_reg_warning_days)
                with Database(db_path) as _db_reg:
                    _status_rows = _db_reg.conn.execute(
                        f"SELECT id, {status_sql} AS computed_status FROM contracts"
                        f" WHERE status = 'done'",
                        {"warning_days": _reg_warning_days},
                    ).fetchall()
                _id_to_computed = {row[0]: row[1] for row in _status_rows}
                if "id" in df.columns:
                    df["computed_status"] = df["id"].map(_id_to_computed).fillna("unknown")
                else:
                    df["computed_status"] = "unknown"

                # ── Фильтры: ряд 1 (тип, качество, поиск) ──
                col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
                with col_f1:
                    types_all = sorted(set(df["contract_type"].dropna().unique()))
                    selected_types = st.multiselect(
                        "Тип документа", types_all, default=types_all
                    )
                with col_f2:
                    _filter_status_labels = {
                        "ok": "Все в порядке",
                        "warning": "Есть замечания",
                        "unreliable": "Ненадёжно",
                        "error": "Ошибка",
                    }
                    _filter_status_reverse = {v: k for k, v in _filter_status_labels.items()}
                    statuses_raw = sorted(set(df["validation_status"].dropna().unique()))
                    statuses_display = [_filter_status_labels.get(s, s) for s in statuses_raw]
                    selected_display = st.multiselect(
                        "Качество данных", statuses_display, default=statuses_display
                    )
                    selected_statuses = [_filter_status_reverse.get(s, s) for s in selected_display]
                with col_f3:
                    _cp_options = [""] + sorted(
                        set(df["counterparty"].dropna().unique())
                    )
                    search = st.selectbox(
                        "Контрагент",
                        _cp_options,
                        format_func=lambda x: "Все контрагенты" if x == "" else x,
                    )

                # ── Фильтры: ряд 2 (дата, сумма, контрагент) ──
                with st.expander("Расширенные фильтры", expanded=False):
                    col_f4, col_f5, col_f6 = st.columns([1, 1, 2])
                    with col_f4:
                        date_range = st.date_input(
                            "Дата подписания (от — до)",
                            value=[],
                            help="Выберите диапазон дат",
                        )
                    with col_f5:
                        # Парсинг сумм для определения диапазона
                        from modules.validator import _parse_amount
                        _amounts = []
                        for _a in df["amount"].dropna():
                            _parsed = _parse_amount(str(_a))
                            if _parsed is not None and _parsed > 0:
                                _amounts.append(_parsed)
                        if _amounts:
                            _max_k = int(max(_amounts) / 1000) + 1
                            amount_range = st.slider(
                                "Сумма (тыс. руб.)", 0, _max_k,
                                (0, _max_k),
                                help="Фильтр по сумме документа",
                            )
                        else:
                            amount_range = None
                    with col_f6:
                        counterparties_all = sorted(
                            set(df["counterparty"].dropna().unique())
                        )
                        selected_counterparties = st.multiselect(
                            "Контрагент", counterparties_all,
                            default=counterparties_all,
                        )

                # ── Применение всех фильтров ──
                mask = pd.Series(True, index=df.index)
                if selected_types:
                    mask &= df["contract_type"].isin(selected_types) | df[
                        "contract_type"
                    ].isna()
                if selected_statuses:
                    mask &= df["validation_status"].isin(selected_statuses) | df[
                        "validation_status"
                    ].isna()
                if search:
                    mask &= df["counterparty"] == search
                # Фильтр по дате
                if date_range and len(date_range) == 2:
                    df_dates = pd.to_datetime(df["date_signed"], errors="coerce")
                    mask &= (
                        (df_dates >= pd.Timestamp(date_range[0]))
                        & (df_dates <= pd.Timestamp(date_range[1]))
                    ) | df["date_signed"].isna()
                # Фильтр по сумме
                if amount_range is not None and _amounts:
                    lo_k, hi_k = amount_range
                    def _amount_in_range(val):
                        p = _parse_amount(str(val)) if val else None
                        if p is None:
                            return True  # не фильтруем пустые
                        return lo_k * 1000 <= p <= hi_k * 1000
                    mask &= df["amount"].apply(_amount_in_range)
                # Фильтр по контрагенту
                if selected_counterparties and len(selected_counterparties) < len(counterparties_all):
                    mask &= df["counterparty"].isin(selected_counterparties) | df[
                        "counterparty"
                    ].isna()

                df_filtered = df[mask]

                # ── Таблица реестра (единый вид) ──
                _status_emoji = {
                    "ok": "✅ Все ОК",
                    "warning": "⚠️ Замечания",
                    "unreliable": "🔴 Ненадёжно",
                    "error": "❌ Ошибка",
                }
                _review_emoji = {
                    "not_reviewed": "—",
                    "reviewed": "✅ Проверен",
                    "attention_needed": "⚠️ Внимание",
                }
                _cols_for_display = ["filename", "contract_type", "counterparty",
                    "date_signed", "amount", "confidence",
                    "validation_status", "review_status"]
                if "computed_status" in df_filtered.columns:
                    _cols_for_display = ["computed_status"] + _cols_for_display
                display_df = df_filtered[_cols_for_display].copy()
                if "computed_status" in display_df.columns:
                    display_df["computed_status"] = display_df["computed_status"].apply(
                        lambda s: STATUS_LABELS.get(s, ("?", str(s), "#9ca3af"))[0]
                        + " "
                        + STATUS_LABELS.get(s, ("?", str(s), "#9ca3af"))[1]
                    )
                    display_df.rename(columns={"computed_status": "Статус"}, inplace=True)
                display_df.rename(columns={
                    "filename": "Файл", "contract_type": "Тип",
                    "counterparty": "Контрагент", "date_signed": "Дата",
                    "amount": "Сумма", "confidence": "AI",
                    "validation_status": "Качество", "review_status": "Проверка",
                }, inplace=True)
                # Форматируем даты в DD.MM.YYYY
                def _fmt_date(v):
                    if not v or str(v).strip() == "":
                        return "—"
                    s = str(v)
                    if "-" in s:
                        parts = s.split("-")
                        if len(parts) == 3:
                            return f"{parts[2]}.{parts[1]}.{parts[0]}"
                    return s
                display_df["Дата"] = display_df["Дата"].apply(_fmt_date)
                display_df["AI"] = pd.to_numeric(display_df["AI"], errors="coerce").fillna(0) * 100
                display_df["Качество"] = display_df["Качество"].map(
                    _status_emoji
                ).fillna("—")
                display_df["Проверка"] = display_df["Проверка"].map(
                    _review_emoji
                ).fillna("—")

                st.dataframe(
                    display_df,
                    column_config={
                        "Статус": st.column_config.TextColumn(width="small"),
                        "AI": st.column_config.ProgressColumn(
                            format="%.0f%%", min_value=0, max_value=100,
                        ),
                        "Файл": st.column_config.TextColumn(width="medium"),
                        "Тип": st.column_config.TextColumn(width="medium"),
                        "Контрагент": st.column_config.TextColumn(width="medium"),
                        "Сумма": st.column_config.TextColumn(width="small"),
                    },
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(f"Показано {len(df_filtered)} из {len(df)}")

                # ── Ручная коррекция статуса ─────────────────────
                if not df_filtered.empty and "id" in df_filtered.columns:
                    st.markdown("---")
                    st.subheader("Ручная коррекция статуса")
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        _override_filenames = df_filtered["filename"].tolist()
                        _override_ids = df_filtered["id"].tolist()
                        _contract_options = dict(zip(_override_filenames, _override_ids))
                        selected_name = st.selectbox(
                            "Договор", options=_override_filenames,
                            key="status_override_contract",
                        )
                    with col2:
                        _status_options = {
                            "Авто (сбросить)": None,
                            "Расторгнут": "terminated",
                            "Продлён": "extended",
                            "На согласовании": "negotiation",
                            "Приостановлен": "suspended",
                        }
                        selected_status_label = st.selectbox(
                            "Статус", options=list(_status_options.keys()),
                            key="status_override_value",
                        )
                    with col3:
                        st.write("")  # выравнивание по вертикали
                        if st.button("Применить", key="status_override_btn"):
                            _contract_id = _contract_options.get(selected_name)
                            _new_status = _status_options[selected_status_label]
                            if _contract_id is not None:
                                with Database(db_path) as _db_override:
                                    if _new_status is None:
                                        clear_manual_status(_db_override, _contract_id)
                                    else:
                                        set_manual_status(_db_override, _contract_id, _new_status)
                            st.rerun()

                # Действия
                col_a1, col_a2, col_a3 = st.columns([1, 1, 1])
                with col_a1:
                    if report_path and Path(report_path).exists():
                        with open(report_path, "rb") as f:
                            excel_bytes = f.read()
                        st.download_button(
                            "Скачать Excel",
                            data=excel_bytes,
                            file_name="Реестр_документов.xlsx",
                            mime="application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet",
                        )
                with col_a2:
                    if _CLOUD_MODE:
                        # ZIP-архив с организованными файлами
                        _docs_dir = Path(str(output_dir)) / "Документы"
                        if _docs_dir.exists() and any(_docs_dir.rglob("*")):
                            _buf = io.BytesIO()
                            with zipfile.ZipFile(_buf, "w", zipfile.ZIP_DEFLATED) as _zf:
                                for _f in _docs_dir.rglob("*"):
                                    if _f.is_file():
                                        _zf.write(_f, _f.relative_to(Path(str(output_dir))))
                            st.download_button(
                                "Скачать файлы (ZIP)",
                                data=_buf.getvalue(),
                                file_name="ЮрТэг_Результат.zip",
                                mime="application/zip",
                            )
                    else:
                        st.markdown(f"Результаты: `{output_dir}`")
                with col_a3:
                    if st.button("Очистить"):
                        for k in ("show_results", "output_dir", "report_path", "processing_time"):
                            st.session_state.pop(k, None)
                        st.rerun()

            # ── Таб: Детали ─────────────────────────────────────
            with tab_details:
                filenames = df["filename"].tolist()
                selected_file = st.selectbox("Выберите файл", filenames, help="Выберите файл для просмотра подробной информации")
                if selected_file:
                    r = df[df["filename"] == selected_file].iloc[0]
                    selected_contract_id = int(r.get("id", 0)) if r.get("id") else None

                    tab_main, tab_versions, tab_payments, tab_review = st.tabs(
                        ["Основное", "Версии", "Платежи", "Ревью"]
                    )

                    # ── Вкладка: Основное ────────────────────────────
                    with tab_main:
                        # Статус — бейдж (тёмная тема)
                        _det_badge = {
                            "ok": ("Все в порядке", "rgba(52,211,153,0.15)", "#34D399"),
                            "warning": ("Есть замечания", "rgba(251,191,36,0.15)", "#FBBF24"),
                            "unreliable": ("Ненадёжно", "rgba(248,113,113,0.15)", "#F87171"),
                            "error": ("Ошибка", "rgba(248,113,113,0.15)", "#F87171"),
                        }
                        vs = r.get("validation_status", "")
                        b_label, b_bg, b_fg = _det_badge.get(vs, (str(vs), "rgba(255,255,255,0.05)", "#94A3B8"))

                        conf = r.get("confidence")
                        conf_str = f"{float(conf):.0%}" if conf and conf == conf else "—"
                        conf_color = "#34D399" if conf and float(conf) >= 0.8 else "#FBBF24" if conf and float(conf) >= 0.5 else "#F87171"

                        # Форматирование дат
                        def _fmt_date(val):
                            if not val or str(val) == "None" or str(val) == "nan":
                                return "—"
                            s = str(val)
                            if "-" in s:
                                p = s.split("-")
                                if len(p) == 3:
                                    return f"{p[2]}.{p[1]}.{p[0]}"
                            return s

                        # Форматирование сторон
                        _parties_raw = r.get("parties", "—") or "—"
                        if isinstance(_parties_raw, list):
                            _parties_str = ", ".join(str(p) for p in _parties_raw)
                        elif isinstance(_parties_raw, str) and _parties_raw.startswith("["):
                            import ast
                            try:
                                _pl = ast.literal_eval(_parties_raw)
                                _parties_str = ", ".join(str(p) for p in _pl) if isinstance(_pl, list) else _parties_raw
                            except Exception:
                                _parties_str = _parties_raw
                        else:
                            _parties_str = str(_parties_raw)

                        # Карточка в стиле реестра
                        import html as _html
                        _e = _html.escape
                        _fname = _e(r.get('filename', '—'))
                        _ctype = _e(r.get('contract_type', '—') or '—')
                        _dsign = _fmt_date(r.get('date_signed'))
                        _cparty = _e(r.get('counterparty', '—') or '—')
                        _dstart = _fmt_date(r.get('date_start'))
                        _dend = _fmt_date(r.get('date_end'))
                        _subj = _e(r.get('subject', '—') or '—')
                        _amt = _e(str(r.get('amount', '—') or '—'))
                        _pty = _e(_parties_str)

                        card_html = f"""
<div class="lg-panel yt-animate" style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-weight:700;font-size:1.05em;color:var(--text-primary);">{_fname}</span>
      <span style="background:{b_bg};color:{b_fg};padding:3px 10px;border-radius:16px;font-size:0.75em;font-weight:600;">{b_label}</span>
    </div>
    <span style="font-weight:700;font-size:1.05em;color:{conf_color};">AI {conf_str}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
    <div style="background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
      <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Тип документа</div>
      <div style="font-size:0.9rem;font-weight:600;color:var(--text-primary);">{_ctype}</div>
    </div>
    <div style="background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
      <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Контрагент</div>
      <div style="font-size:0.9rem;font-weight:600;color:var(--text-primary);">{_cparty}</div>
    </div>
    <div style="background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
      <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Дата подписания</div>
      <div style="font-size:0.9rem;font-weight:600;color:var(--text-primary);">{_dsign}</div>
    </div>
    <div style="background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
      <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Сумма</div>
      <div style="font-size:0.9rem;font-weight:600;color:var(--accent);">{_amt}</div>
    </div>
    <div style="background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
      <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Срок действия</div>
      <div style="font-size:0.9rem;font-weight:500;color:var(--text-secondary);">{_dstart} — {_dend}</div>
    </div>
    <div style="background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
      <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Стороны</div>
      <div style="font-size:0.85rem;font-weight:500;color:var(--text-secondary);">{_pty}</div>
    </div>
  </div>
  <div style="margin-top:12px;background:var(--glass-bg-1);border:0.5px solid var(--glass-border);border-radius:var(--radius-sm);padding:12px 14px;">
    <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:4px;">Предмет</div>
    <div style="font-size:0.88rem;font-weight:500;color:var(--text-secondary);line-height:1.5;">{_subj}</div>
  </div>
</div>"""
                        st.markdown(card_html, unsafe_allow_html=True)

                        # Замечания валидации
                        _warnings = r.get("validation_warnings")
                        if _warnings:
                            st.markdown(
                                '<div class="yt-section-label">Замечания</div>',
                                unsafe_allow_html=True,
                            )
                            _items = (
                                _warnings.split("; ")
                                if isinstance(_warnings, str)
                                else (_warnings if isinstance(_warnings, list) else [])
                            )
                            for _w in _items:
                                _w_str = str(_w).strip()
                                if not _w_str:
                                    continue
                                _wtitle, _wicon, _wcolor, _wbg, _wborder, _wtip = _classify_warning(_w_str)
                                _detail = _w_str.split(": ", 1)[1] if ": " in _w_str else _w_str
                                st.markdown(f"""
                                <div style="background:rgba(255,255,255,0.03); border-left:3px solid {_wborder}; border-radius:10px; padding:12px 16px; margin-bottom:8px; backdrop-filter:blur(8px);">
                                    <div style="font-weight:600; color:{_wborder}; font-size:0.88em;">{_wicon} {_wtitle}</div>
                                    <div style="color:#94A3B8; font-size:0.83em; margin-top:3px;">{_detail}</div>
                                    <div style="color:#64748B; font-size:0.76em; margin-top:5px; font-style:italic;">💡 {_wtip}</div>
                                </div>""", unsafe_allow_html=True)

                        # Особые условия
                        _special = r.get("special_conditions")
                        if _special:
                            with st.expander("Особые условия", expanded=False):
                                if isinstance(_special, str):
                                    st.info(_special)
                                elif isinstance(_special, list):
                                    for _s in _special:
                                        st.info(str(_s))

                        # ── Кнопки навигации к файлу ──
                        import platform
                        import subprocess as _sp
                        if platform.system() == "Darwin" and not _CLOUD_MODE:
                            _col_nav1, _col_nav2 = st.columns(2)
                            _orig_path = r.get("original_path", "")
                            _org_path = r.get("organized_path", "")
                            with _col_nav1:
                                if _orig_path and Path(str(_orig_path)).exists():
                                    if st.button("Показать оригинал в Finder",
                                                 key=f"finder_orig_{selected_file}"):
                                        _sp.Popen(["open", "-R", str(_orig_path)])
                                else:
                                    st.button("Оригинал не найден",
                                              disabled=True,
                                              key=f"finder_orig_{selected_file}")
                            with _col_nav2:
                                if _org_path and Path(str(_org_path)).exists():
                                    if st.button("Показать копию в Finder",
                                                 key=f"finder_copy_{selected_file}"):
                                        _sp.Popen(["open", "-R", str(_org_path)])
                                else:
                                    st.button("Копия не найдена",
                                              disabled=True,
                                              key=f"finder_copy_{selected_file}")

                        # ── Пометки юриста ──
                        st.markdown("---")
                        st.markdown("**Пометки юриста**")
                        _review_options = {
                            "Не проверен": "not_reviewed",
                            "Проверен": "reviewed",
                            "Требует внимания": "attention_needed",
                        }
                        _review_reverse = {v: k for k, v in _review_options.items()}
                        _current_review = r.get("review_status", "not_reviewed")
                        _current_label = _review_reverse.get(_current_review, "Не проверен")
                        _review_keys = list(_review_options.keys())

                        new_review = st.radio(
                            "Статус проверки",
                            _review_keys,
                            index=_review_keys.index(_current_label),
                            horizontal=True,
                            key=f"review_{selected_file}",
                        )
                        lawyer_comment = st.text_area(
                            "Комментарий",
                            value=r.get("lawyer_comment", "") or "",
                            key=f"comment_{selected_file}",
                            height=80,
                            placeholder="Заметки по документу...",
                        )
                        if st.button("Сохранить пометку",
                                     key=f"save_review_{selected_file}"):
                            from modules.database import Database as _DB
                            _file_hash = r.get("file_hash", "")
                            if _file_hash:
                                with _DB(db_path) as _db_w:
                                    _db_w.update_review(
                                        _file_hash,
                                        _review_options[new_review],
                                        lawyer_comment,
                                    )
                                st.success("Пометка сохранена!")
                                st.rerun()
                            else:
                                st.error("Не удалось найти хеш файла")

                    # ── Вкладка: Версии ──────────────────────────────
                    with tab_versions:
                        if selected_contract_id is None:
                            st.info("Не удалось определить ID документа")
                        else:
                            with Database(db_path) as _db_ver:
                                versions = get_version_group(_db_ver, selected_contract_id)
                            if not versions:
                                st.info("Версии не найдены")
                            else:
                                st.markdown(f"**Всего версий:** {len(versions)}")
                                for v in versions:
                                    _v_icon = "📋" if v.version_number == len(versions) else "📄"
                                    _v_method = "авто" if v.link_method == "auto_embedding" else "вручную"
                                    st.markdown(
                                        f"{_v_icon} **v{v.version_number}** · {v.created_at or '—'} "
                                        f"· связан {_v_method}"
                                    )
                                if len(versions) >= 2:
                                    st.markdown("---")
                                    st.subheader("Сравнение версий")
                                    version_options = {f"v{v.version_number}": v.contract_id for v in versions}
                                    v_keys = list(version_options.keys())
                                    _col_v1, _col_v2 = st.columns(2)
                                    with _col_v1:
                                        v_old_label = st.selectbox("Старая версия", v_keys[:-1], key="diff_old")
                                    with _col_v2:
                                        v_new_label = st.selectbox("Новая версия", v_keys[1:], key="diff_new")

                                    if st.button("Сравнить", key="diff_btn"):
                                        _old_cid = version_options[v_old_label]
                                        _new_cid = version_options[v_new_label]

                                        def _load_meta(cid):
                                            with Database(db_path) as _db_m:
                                                _mrow = _db_m.conn.execute(
                                                    "SELECT contract_type, counterparty, subject, "
                                                    "date_signed, date_start, date_end, amount "
                                                    "FROM contracts WHERE id=?", (cid,)
                                                ).fetchone()
                                            if _mrow:
                                                from modules.models import ContractMetadata
                                                return ContractMetadata(
                                                    contract_type=_mrow[0], counterparty=_mrow[1],
                                                    subject=_mrow[2], date_signed=_mrow[3],
                                                    date_start=_mrow[4], date_end=_mrow[5],
                                                    amount=_mrow[6],
                                                )
                                            from modules.models import ContractMetadata
                                            return ContractMetadata()

                                        diffs = diff_versions(_load_meta(_old_cid), _load_meta(_new_cid))
                                        changed = [d for d in diffs if d["changed"]]
                                        if not changed:
                                            st.success("Ключевые поля идентичны")
                                        else:
                                            for d in changed:
                                                st.markdown(
                                                    f"**{d['field']}:** "
                                                    f"~~{d['old']}~~ → **{d['new']}**"
                                                )

                                    st.markdown("---")
                                    st.subheader("Скачать редлайн")
                                    _col_rl1, _col_rl2 = st.columns(2)
                                    with _col_rl1:
                                        rl_old = st.selectbox("Старая (редлайн)", v_keys[:-1], key="rl_old")
                                    with _col_rl2:
                                        rl_new = st.selectbox("Новая (редлайн)", v_keys[1:], key="rl_new")

                                    if st.button("Сгенерировать редлайн", key="rl_btn"):
                                        with Database(db_path) as _db_rl:
                                            _rl_old_row = _db_rl.conn.execute(
                                                "SELECT subject, contract_type FROM contracts WHERE id=?",
                                                (version_options[rl_old],)
                                            ).fetchone()
                                            _rl_new_row = _db_rl.conn.execute(
                                                "SELECT subject, contract_type FROM contracts WHERE id=?",
                                                (version_options[rl_new],)
                                            ).fetchone()
                                        _old_txt = (_rl_old_row[0] or "") if _rl_old_row else ""
                                        _new_txt = (_rl_new_row[0] or "") if _rl_new_row else ""
                                        _ctype_rl = (_rl_old_row[1] or "Договор") if _rl_old_row else "Договор"
                                        docx_bytes = generate_redline_docx(
                                            _old_txt, _new_txt,
                                            f"Редлайн: {_ctype_rl} ({rl_old} → {rl_new})"
                                        )
                                        st.download_button(
                                            "Скачать .docx",
                                            data=docx_bytes,
                                            file_name=f"redline_{rl_old}_vs_{rl_new}.docx",
                                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            key="rl_download",
                                        )

                    with tab_payments:
                        if selected_contract_id is not None:
                            with Database(db_path) as _db_pay:
                                all_pay_events = get_calendar_events(_db_pay)
                            contract_payments = [
                                e for e in all_pay_events
                                if e["extendedProps"].get("contract_id") == selected_contract_id
                            ]
                            if not contract_payments:
                                st.info("Платёжные данные для этого договора отсутствуют")
                            else:
                                st.markdown(f"**Платежей:** {len(contract_payments)}")
                                for p in contract_payments:
                                    direction_label = "Расход" if p["extendedProps"]["direction"] == "expense" else "Доход"
                                    amount_str = f"{p['extendedProps']['amount']:,.0f} ₽".replace(",", " ")
                                    color = p["backgroundColor"]
                                    st.markdown(
                                        f'<span style="color:{color}">●</span> {p["start"]} — {direction_label} {amount_str}',
                                        unsafe_allow_html=True,
                                    )
                        else:
                            st.info("Не удалось определить ID договора")

                    # ── Вкладка: Ревью ───────────────────────────────
                    with tab_review:
                        _doc_type = r.get("contract_type")
                        _doc_subject = r.get("subject") or ""
                        if not _doc_subject:
                            st.info(
                                "Текст договора недоступен для ревью "
                                "(нет поля Subject в метаданных)"
                            )
                        else:
                            with Database(db_path) as _db_rev:
                                _auto_match = match_template(_db_rev, _doc_subject, _doc_type)
                                _all_templates = list_templates(_db_rev)

                            if not _all_templates:
                                st.warning(
                                    "Библиотека шаблонов пуста. "
                                    "Добавьте шаблоны во вкладке «Шаблоны»."
                                )
                            else:
                                _tmpl_names = {t.name: t for t in _all_templates}
                                _default_idx = 0
                                if _auto_match:
                                    st.success(
                                        f"Автоматически подобран шаблон: **{_auto_match.name}**"
                                    )
                                    if _auto_match.name in _tmpl_names:
                                        _default_idx = list(_tmpl_names.keys()).index(
                                            _auto_match.name
                                        )

                                _selected_tmpl_name = st.selectbox(
                                    "Шаблон для сравнения",
                                    list(_tmpl_names.keys()),
                                    index=_default_idx,
                                    key=f"review_template_select_{selected_file}",
                                )
                                _selected_tmpl = _tmpl_names[_selected_tmpl_name]

                                if st.button(
                                    "Запустить ревью",
                                    key=f"run_review_btn_{selected_file}",
                                ):
                                    _deviations = review_against_template(
                                        _selected_tmpl.content_text or "",
                                        _doc_subject,
                                    )
                                    st.session_state[f"_rev_deviations_{selected_file}"] = _deviations

                                _deviations = st.session_state.get(
                                    f"_rev_deviations_{selected_file}"
                                )
                                if _deviations is not None:
                                    if not _deviations:
                                        st.success("Отступлений от шаблона не найдено")
                                    else:
                                        st.markdown(
                                            f"**Найдено отступлений: {len(_deviations)}**"
                                        )
                                        for _dev in _deviations:
                                            _type_label = {
                                                "added":   "Добавлено в договоре",
                                                "removed": "Отсутствует в договоре",
                                                "changed": "Изменено",
                                            }.get(_dev["type"], _dev["type"])
                                            _tmpl_part = (
                                                f'<span style="text-decoration:line-through;'
                                                f'color:#6b7280">{_dev["template_text"]}</span><br>'
                                                if _dev["template_text"]
                                                else ""
                                            )
                                            _doc_part = (
                                                _dev["document_text"]
                                                if _dev["document_text"]
                                                else ""
                                            )
                                            st.markdown(
                                                f'<div style="background:{_dev["color"]};'
                                                f'padding:8px;border-radius:4px;margin:4px 0;'
                                                f'color:#1a1a1a;">'
                                                f"<b>{_type_label}</b><br>"
                                                f"{_tmpl_part}{_doc_part}</div>",
                                                unsafe_allow_html=True,
                                            )

                                        # Кнопка редлайна
                                        st.markdown("---")
                                        from services.version_service import generate_redline_docx as _gen_redline
                                        _docx_bytes = _gen_redline(
                                            _selected_tmpl.content_text or "",
                                            _doc_subject,
                                            title=f"Ревью: {_selected_tmpl_name}",
                                        )
                                        st.download_button(
                                            "Скачать редлайн .docx",
                                            data=_docx_bytes,
                                            file_name=f"review_{selected_file}.docx",
                                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            key=f"review_download_{selected_file}",
                                        )

            # ── Таб: Шаблоны (библиотека эталонов) ──────────────
            with tab_templates:
                st.markdown(
                    '<div class="yt-section-label">Библиотека шаблонов</div>',
                    unsafe_allow_html=True,
                )

                # Способ 1: загрузить файл
                st.subheader("Загрузить новый шаблон")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tmpl_type = st.text_input(
                        "Тип договора",
                        placeholder="NDA, Поставка, Аренда...",
                        key="tmpl_type_input",
                    )
                    tmpl_name = st.text_input(
                        "Название шаблона",
                        placeholder="Стандартное NDA v1",
                        key="tmpl_name_input",
                    )
                with col_t2:
                    tmpl_file = st.file_uploader(
                        "Файл шаблона (PDF или DOCX)",
                        type=["pdf", "docx"],
                        key="tmpl_file_uploader",
                    )

                if st.button("Добавить шаблон", key="add_template_btn"):
                    if not tmpl_type or not tmpl_name:
                        st.error("Укажите тип договора и название шаблона")
                    elif tmpl_file is None:
                        st.error("Загрузите файл шаблона")
                    else:
                        import tempfile as _tempfile
                        from modules.extractor import Extractor
                        from modules.models import FileInfo as _FileInfo

                        with _tempfile.NamedTemporaryFile(
                            suffix=Path(tmpl_file.name).suffix, delete=False
                        ) as _tmp:
                            _tmp.write(tmpl_file.read())
                            _tmp_path = Path(_tmp.name)
                        try:
                            _extractor = Extractor()
                            _fi = _FileInfo(
                                path=_tmp_path,
                                filename=tmpl_file.name,
                                extension=_tmp_path.suffix,
                                size_bytes=_tmp_path.stat().st_size,
                                file_hash="",
                            )
                            _extracted = _extractor.extract(_fi)
                            _content = _extracted.text or tmpl_file.name
                            with Database(db_path) as _db_tmpl:
                                add_template(_db_tmpl, tmpl_type, tmpl_name, _content, tmpl_file.name)
                            st.success(f"Шаблон «{tmpl_name}» добавлен")
                        except Exception as _e:
                            st.error(f"Ошибка при обработке файла: {_e}")
                        finally:
                            _tmp_path.unlink(missing_ok=True)

                # Способ 2: отметить из реестра
                st.markdown("---")
                st.subheader("Сделать документ из реестра эталоном")
                with Database(db_path) as _db_reg_tmpl:
                    _all_reg_docs = _db_reg_tmpl.conn.execute(
                        "SELECT id, filename, contract_type FROM contracts WHERE status='done' ORDER BY filename"
                    ).fetchall()
                if _all_reg_docs:
                    _doc_tmpl_options = {f"{_r[1]} ({_r[2] or 'без типа'})": _r[0] for _r in _all_reg_docs}
                    _selected_for_template = st.selectbox(
                        "Выбрать документ",
                        list(_doc_tmpl_options.keys()),
                        key="tmpl_from_registry",
                    )
                    _tmpl_name_from_reg = st.text_input(
                        "Название эталона (необязательно)",
                        key="tmpl_name_reg",
                    )
                    if st.button("Сделать эталоном", key="make_template_btn"):
                        _cid = _doc_tmpl_options[_selected_for_template]
                        with Database(db_path) as _db_mark:
                            mark_contract_as_template(
                                _db_mark, _cid,
                                _tmpl_name_from_reg or None,
                            )
                        st.success("Документ добавлен как шаблон-эталон")
                        st.rerun()
                else:
                    st.info("Нет обработанных документов для создания эталона")

                # Текущая библиотека
                st.markdown("---")
                st.subheader("Текущие шаблоны")
                with Database(db_path) as _db_list_tmpl:
                    _templates_list = list_templates(_db_list_tmpl)
                if not _templates_list:
                    st.info("Библиотека шаблонов пуста — загрузите первый шаблон выше")
                else:
                    for _t in _templates_list:
                        st.markdown(f"**{_t.contract_type}** — {_t.name}")

            # ── Таб: Платёжный календарь ─────────────────────────
            with tab_calendar:
                st.header("Платёжный календарь")
                if not _HAS_CALENDAR:
                    st.warning(
                        "Зависимость streamlit-calendar не установлена. "
                        "Запустите: pip install streamlit-calendar==1.4.0"
                    )
                else:
                    with Database(db_path) as _db_cal:
                        cal_events = get_calendar_events(_db_cal)
                    if not cal_events:
                        st.info(
                            "Платёжные данные отсутствуют. "
                            "Загрузите договоры с указанными суммами и сроками."
                        )
                    else:
                        expense_total = sum(
                            e["extendedProps"]["amount"]
                            for e in cal_events
                            if e["extendedProps"].get("direction") == "expense"
                        )
                        income_total = sum(
                            e["extendedProps"]["amount"]
                            for e in cal_events
                            if e["extendedProps"].get("direction") == "income"
                        )
                        col_e, col_i = st.columns(2)
                        with col_e:
                            st.metric("Расходы (всего)", f"{expense_total:,.0f} ₽".replace(",", " "))
                        with col_i:
                            st.metric("Доходы (всего)", f"{income_total:,.0f} ₽".replace(",", " "))

                        calendar_options = {
                            "initialView": "dayGridMonth",
                            "headerToolbar": {
                                "left": "prev,next today",
                                "center": "title",
                                "right": "dayGridMonth,timeGridWeek",
                            },
                            "locale": "ru",
                            "height": 600,
                        }
                        clicked = st_calendar(
                            events=cal_events,
                            options=calendar_options,
                            key="payment_calendar",
                        )

                        if clicked and clicked.get("eventClick"):
                            event_data = clicked["eventClick"]["event"]
                            props = event_data.get("extendedProps", {})
                            direction_label = "Расход" if props.get("direction") == "expense" else "Доход"
                            amount_str = f"{props.get('amount', 0):,.0f} ₽".replace(",", " ")
                            with st.expander("Детали платежа", expanded=True):
                                st.markdown(f"**{event_data.get('title', '—')}**")
                                st.markdown(f"**Тип:** {direction_label}")
                                st.markdown(f"**Сумма:** {amount_str}")
                                st.markdown(f"**Контрагент:** {props.get('counterparty', '—')}")
                                st.markdown(f"**Тип договора:** {props.get('contract_type', '—')}")
                                st.markdown(f"**ID договора:** {props.get('contract_id', '—')}")

        else:
            st.info("Нет обработанных файлов.")
    else:
        st.warning("База данных не найдена.")
