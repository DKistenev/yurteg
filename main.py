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
    /* Шрифт и общий стиль */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Убрать лишние отступы сверху */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }

    /* Заголовок */
    h1 {
        background: linear-gradient(135deg, #4F46E5, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Sidebar стиль */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #E2E8F0 !important;
    }

    /* Tooltip в sidebar — тёмный текст на светлом фоне */
    [data-testid="stSidebar"] [data-testid="stTooltipContent"],
    [data-testid="stSidebar"] [data-testid="stTooltipContent"] p,
    [data-testid="stSidebar"] [data-testid="stTooltipContent"] span,
    [data-testid="stSidebar"] div[data-baseweb="tooltip"] span,
    [data-testid="stSidebar"] div[data-baseweb="tooltip"] p,
    div[role="tooltip"] span,
    div[role="tooltip"] p,
    div[data-baseweb="tooltip"] div span,
    div[data-baseweb="tooltip"] div p {
        color: #1E293B !important;
    }

    /* Кнопка запуска — градиент */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        border: none;
        color: white;
        font-weight: 600;
        font-size: 1.05rem;
        padding: 0.65rem 2rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
        transform: translateY(-1px);
    }

    /* Карточки метрик */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label {
        color: #64748B !important;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1E293B;
    }

    /* Лог обработки */
    .processing-log {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        line-height: 1.6;
        max-height: 300px;
        overflow-y: auto;
    }

    /* Dataframe стиль */
    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Скрыть Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Алерты */
    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    /* Разделитель */
    hr {
        border-color: #E2E8F0;
        margin: 1.5rem 0;
    }

    /* Download button */
    div.stDownloadButton > button {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        border: none;
        color: white;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
    }
    div.stDownloadButton > button:hover {
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ── Заголовок ───────────────────────────────────────────────────

st.title("ЮрТэг")
st.markdown(
    '<p style="color: #64748B; margin-top: -10px; font-size: 1.1rem;">'
    "Автоматическая обработка архива документов</p>",
    unsafe_allow_html=True,
)

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
        '<h2 style="margin-bottom: 0.2rem;">⚙️ Настройки</h2>',
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
        '<p style="color: #94A3B8; font-size: 0.75rem; text-align: center;">'
        "ЮрТэг v0.4</p>",
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
                icon, color = "⚠️", "#F59E0B"
            elif v and v.status in ("unreliable", "error"):
                icon, color = "🔶", "#EF4444"
            else:
                icon, color = "✅", "#10B981"
            meta = ""
            if result.metadata:
                parts = []
                if result.metadata.contract_type:
                    parts.append(result.metadata.contract_type)
                if result.metadata.counterparty:
                    parts.append(result.metadata.counterparty)
                if parts:
                    meta = " — " + ", ".join(parts)
            log_lines.append(
                f'<div style="padding:2px 0;color:{color}">'
                f"{icon} {result.file_info.filename}{meta}</div>"
            )
        else:
            log_lines.append(
                f'<div style="padding:2px 0;color:#EF4444">'
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

    controller = Controller(config)
    try:
        stats = controller.process_archive(
            source_dir=source_dir,
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

    # Success-banner
    st.divider()
    if stats["errors"] == 0:
        avg_conf = ""
        st.success(
            f"Обработано **{stats['done']}** файлов за **{_total_time:.1f}** сек. "
            f"Ошибок: **0**. Средняя скорость: ~{_total_time / max(stats['done'], 1):.1f} сек/файл."
        )
    else:
        st.warning(
            f"Обработано **{stats['done']}** файлов за **{_total_time:.1f}** сек. "
            f"Проблемы: **{stats['errors']}**. Проверьте вкладку Реестр."
        )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Обработано", stats["done"])
    col2.metric("Ошибки", stats["errors"])
    col3.metric("Пропущено", stats["skipped"])
    col4.metric("Время", f"{_total_time:.1f}с", f"~{_total_time / max(stats['done'], 1):.1f} с/файл")

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

            tab_summary, tab_registry, tab_details = st.tabs(
                ["Сводка", "Реестр", "Детали"]
            )

            # ── Таб: Сводка ─────────────────────────────────────
            with tab_summary:
                # Ряд 1: Типы договоров — на всю ширину
                st.markdown("**Типы документов**", help="Распределение обработанных файлов по типам документов")
                type_counts = df["contract_type"].dropna().value_counts().reset_index()
                type_counts.columns = ["Тип", "Количество"]
                if not type_counts.empty:
                    pie = (
                        alt.Chart(type_counts)
                        .mark_arc(innerRadius=50, stroke="#fff", strokeWidth=2)
                        .encode(
                            theta=alt.Theta("Количество:Q"),
                            color=alt.Color(
                                "Тип:N",
                                scale=alt.Scale(scheme="tableau20"),
                                legend=alt.Legend(orient="right", columns=1),
                            ),
                            tooltip=["Тип:N", "Количество:Q"],
                        )
                        .properties(height=280)
                    )
                    st.altair_chart(pie, use_container_width=True)
                else:
                    st.info("Нет данных о типах")

                # Ряд 2: два gauge рядом
                gauge_l, gauge_r = st.columns(2)

                with gauge_l:
                    st.markdown("**Качество данных**", help="Доля файлов без замечаний. Проверка: структура полей, логика дат и сумм, уверенность AI, перекрёстная проверка")
                    total_validated = len(df[df["validation_status"].notna()])
                    ok_count = len(df[df["validation_status"] == "ok"])
                    quality_pct = int(round(ok_count / max(total_validated, 1) * 100))
                    q_color = "#10B981" if quality_pct >= 80 else "#F59E0B" if quality_pct >= 50 else "#EF4444"

                    q_data = pd.DataFrame([{"seg": "fill", "v": quality_pct}, {"seg": "bg", "v": 100 - quality_pct}])
                    q_arc = (
                        alt.Chart(q_data)
                        .mark_arc(innerRadius=55, outerRadius=80, stroke="#fff", strokeWidth=2)
                        .encode(theta=alt.Theta("v:Q", stack=True), color=alt.Color("seg:N", scale=alt.Scale(domain=["fill", "bg"], range=[q_color, "#E2E8F0"]), legend=None), tooltip=alt.value(None))
                        .properties(width=200, height=200)
                    )
                    q_text = alt.Chart(pd.DataFrame([{"t": f"{quality_pct}%"}])).mark_text(fontSize=32, fontWeight="bold", color=q_color).encode(text="t:N", tooltip=alt.value(None))
                    q_sub = alt.Chart(pd.DataFrame([{"t": f"{ok_count} из {total_validated}"}])).mark_text(fontSize=12, dy=22, color="#94A3B8").encode(text="t:N", tooltip=alt.value(None))
                    st.altair_chart(q_arc + q_text + q_sub, use_container_width=True)

                with gauge_r:
                    if "confidence" in df.columns:
                        conf_values = df["confidence"].dropna()
                        if not conf_values.empty:
                            avg_conf = float(conf_values.mean())
                            avg_pct = int(round(avg_conf * 100))
                            st.markdown("**Уверенность AI**", help="Средняя уверенность AI в правильности данных. 80%+ — отлично, 50-80% — стоит проверить, ниже 50% — ненадёжно")
                            g_color = "#10B981" if avg_conf >= 0.8 else "#F59E0B" if avg_conf >= 0.5 else "#EF4444"

                            g_data = pd.DataFrame([{"seg": "fill", "v": avg_pct}, {"seg": "bg", "v": 100 - avg_pct}])
                            g_arc = (
                                alt.Chart(g_data)
                                .mark_arc(innerRadius=55, outerRadius=80, stroke="#fff", strokeWidth=2)
                                .encode(theta=alt.Theta("v:Q", stack=True), color=alt.Color("seg:N", scale=alt.Scale(domain=["fill", "bg"], range=[g_color, "#E2E8F0"]), legend=None), tooltip=alt.value(None))
                                .properties(width=200, height=200)
                            )
                            g_text = alt.Chart(pd.DataFrame([{"t": f"{avg_pct}%"}])).mark_text(fontSize=32, fontWeight="bold", color=g_color).encode(text="t:N", tooltip=alt.value(None))
                            g_sub = alt.Chart(pd.DataFrame([{"t": "из 100"}])).mark_text(fontSize=12, dy=22, color="#94A3B8").encode(text="t:N", tooltip=alt.value(None))
                            st.altair_chart(g_arc + g_text + g_sub, use_container_width=True)


            # ── Таб: Реестр ─────────────────────────────────────
            with tab_registry:
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
                display_df = df_filtered[[
                    "filename", "contract_type", "counterparty",
                    "date_signed", "amount", "confidence",
                    "validation_status", "review_status",
                ]].copy()
                display_df.columns = [
                    "Файл", "Тип", "Контрагент", "Дата",
                    "Сумма", "AI", "Качество", "Проверка",
                ]
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

                    # Статус — бейдж
                    _det_badge = {
                        "ok": ("Все в порядке", "#dcfce7", "#166534"),
                        "warning": ("Есть замечания", "#fef9c3", "#854d0e"),
                        "unreliable": ("Ненадёжно", "#fee2e2", "#991b1b"),
                        "error": ("Ошибка", "#fee2e2", "#991b1b"),
                    }
                    vs = r.get("validation_status", "")
                    b_label, b_bg, b_fg = _det_badge.get(vs, (str(vs), "#f3f4f6", "#374151"))

                    conf = r.get("confidence")
                    conf_str = f"{float(conf):.0%}" if conf and conf == conf else "—"
                    conf_color = "#166534" if conf and float(conf) >= 0.8 else "#854d0e" if conf and float(conf) >= 0.5 else "#991b1b"

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

                    card_html = f"""<style>
.yt-detail {{ border:1px solid #e5e7eb; border-radius:12px; overflow:hidden; margin-bottom:16px; }}
.yt-detail-header {{ background:linear-gradient(135deg,#4F46E5,#7C3AED); color:#fff; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; }}
.yt-detail-header .name {{ font-weight:700; font-size:1.05em; }}
.yt-detail-header .badge {{ background:rgba(255,255,255,0.2); padding:3px 10px; border-radius:12px; font-size:0.8em; font-weight:500; margin-left:10px; }}
.yt-detail-header .ai {{ font-weight:700; font-size:1.1em; }}
.yt-detail-body {{ padding:16px 18px; background:#fafbfc; }}
.yt-detail-body table {{ width:100%; font-size:0.9rem; border-collapse:collapse; }}
.yt-detail-body td {{ padding:8px 4px; vertical-align:middle; }}
.yt-detail-body .label {{ color:#6b7280; width:130px; font-size:0.82em; text-transform:uppercase; letter-spacing:0.03em; text-align:center; }}
.yt-detail-body .val {{ font-weight:500; text-align:center; }}
</style>
<div class="yt-detail">
<div class="yt-detail-header">
<div><span class="name">{_fname}</span><span class="badge">{b_label}</span></div>
<span class="ai">AI: {conf_str}</span>
</div>
<div class="yt-detail-body">
<table>
<tr><td class="label">Тип документа</td><td class="val">{_ctype}</td><td class="label">Дата подписания</td><td class="val">{_dsign}</td></tr>
<tr><td class="label">Контрагент</td><td class="val">{_cparty}</td><td class="label">Срок действия</td><td class="val">{_dstart} — {_dend}</td></tr>
<tr><td class="label">Предмет</td><td colspan="3" class="val">{_subj}</td></tr>
<tr><td class="label">Сумма</td><td class="val">{_amt}</td><td class="label">Стороны</td><td class="val">{_pty}</td></tr>
</table>
</div>
</div>"""
                    st.markdown(card_html, unsafe_allow_html=True)

                    # Замечания валидации — понятные пояснения
                    warnings = r.get("validation_warnings")
                    if warnings:
                        st.markdown(
                            "**Замечания**",
                            help="Автоматические проверки качества. "
                            "L1 — пустые поля, L2 — логика данных, "
                            "L3 — уверенность AI, L4 — кросс-файловые.",
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
                            <div style="background:{bg}; border-left:4px solid {border}; border-radius:6px; padding:10px 14px; margin-bottom:8px;">
                                <div style="font-weight:600; color:{color}; font-size:0.9em;">{icon} {title}</div>
                                <div style="color:{color}; font-size:0.85em; margin-top:2px;">{detail_text}</div>
                                <div style="color:{color}; font-size:0.78em; margin-top:4px; font-style:italic; opacity:0.85;">💡 {tip}</div>
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
