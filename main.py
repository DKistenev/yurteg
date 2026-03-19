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
from services.lifecycle_service import (
    get_computed_status_sql, set_manual_status, clear_manual_status,
    get_attention_required, MANUAL_STATUSES, STATUS_LABELS,
)

# Загрузить API-ключи из .env (десктоп; в облаке уже в os.environ)
load_dotenv()

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

with st.sidebar:
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

    db_path = output_dir / "yurteg.db"
    if db_path.exists():
        with Database(db_path) as db:
            all_results = db.get_all_results()

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

            tab_summary, tab_registry, tab_details = st.tabs(
                ["Сводка", "Реестр", "Детали"]
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
                    _e = _html.escape  # экранирование спецсимволов
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

                    # Замечания валидации — понятные пояснения
                    warnings = r.get("validation_warnings")
                    if warnings:
                        st.markdown(
                            '<div class="yt-section-label">Замечания</div>',
                            unsafe_allow_html=True,
                        )
                        items = (
                            warnings.split("; ")
                            if isinstance(warnings, str)
                            else (warnings if isinstance(warnings, list) else [])
                        )
                        for w in items:
                            w_str = str(w).strip()
                            if not w_str:
                                continue
                            title, icon, color, bg, border, tip = _classify_warning(w_str)
                            detail_text = w_str.split(": ", 1)[1] if ": " in w_str else w_str
                            warn_html = f"""
                            <div style="background:rgba(255,255,255,0.03); border-left:3px solid {border}; border-radius:10px; padding:12px 16px; margin-bottom:8px; border:1px solid rgba(6,182,212,0.08); border-left:3px solid {border}; backdrop-filter:blur(8px);">
                                <div style="font-weight:600; color:{border}; font-size:0.88em;">{icon} {title}</div>
                                <div style="color:#94A3B8; font-size:0.83em; margin-top:3px;">{detail_text}</div>
                                <div style="color:#64748B; font-size:0.76em; margin-top:5px; font-style:italic;">💡 {tip}</div>
                            </div>
                            """
                            st.markdown(warn_html, unsafe_allow_html=True)

                    # Особые условия
                    special = r.get("special_conditions")
                    if special:
                        with st.expander("Особые условия", expanded=False):
                            if isinstance(special, str):
                                st.info(special)
                            elif isinstance(special, list):
                                for s in special:
                                    st.info(str(s))

                    # ── Кнопки навигации к файлу ──
                    import platform
                    import subprocess as _sp
                    if platform.system() == "Darwin" and not _CLOUD_MODE:
                        col_nav1, col_nav2 = st.columns(2)
                        _orig_path = r.get("original_path", "")
                        _org_path = r.get("organized_path", "")
                        with col_nav1:
                            if _orig_path and Path(str(_orig_path)).exists():
                                if st.button("Показать оригинал в Finder",
                                             key=f"finder_orig_{selected_file}"):
                                    _sp.Popen(["open", "-R", str(_orig_path)])
                            else:
                                st.button("Оригинал не найден",
                                          disabled=True,
                                          key=f"finder_orig_{selected_file}")
                        with col_nav2:
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
                    _current_label = _review_reverse.get(
                        _current_review, "Не проверен"
                    )
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

        else:
            st.info("Нет обработанных файлов.")
    else:
        st.warning("База данных не найдена.")
