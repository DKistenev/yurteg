"""Design tokens — единое место для цветов, стилей и повторяющихся class-строк.

Используй эти константы вместо хардкода Tailwind-классов в компонентах.
Hex-значения нужны для inline HTML/JS (tour, deviations, calendar).
"""

# ── Hex palette (для inline HTML/JS) ─────────────────────────────────────────

HEX = {
    "slate_300": "#cbd5e1",
    "slate_400": "#94a3b8",
    "slate_500": "#64748b",
    "slate_600": "#475569",
    "slate_900": "#0f172a",
    "indigo_600": "#4f46e5",
    "indigo_700": "#4338ca",
    "indigo_50": "#eef2ff",
}

# ── Card styles ───────────────────────────────────────────────────────────────

CARD_SECTION = "w-full shadow-none border rounded-lg p-5"
CARD_DIALOG = "p-6 min-w-[400px]"
CARD_DIALOG_SM = "p-6 min-w-[360px]"

# ── Button styles ─────────────────────────────────────────────────────────────

BTN_PRIMARY = "px-6 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg"
BTN_FLAT = "text-sm text-slate-400 hover:text-slate-600"

# ── Segment toggle ────────────────────────────────────────────────────────────

SEG_ACTIVE = "px-4 py-1.5 text-sm font-semibold rounded-md bg-indigo-600 text-white transition-colors duration-150"
SEG_INACTIVE = "px-4 py-1.5 text-sm font-semibold rounded-md text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 transition-colors duration-150"

# ── View toggle (list/calendar) ───────────────────────────────────────────────

TOGGLE_ACTIVE = "p-2 rounded-md bg-slate-100 text-slate-700"
TOGGLE_INACTIVE = "p-2 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors duration-150"

# ── Typography ────────────────────────────────────────────────────────────────

TEXT_HEADING = "text-lg font-semibold text-slate-900"
TEXT_HEADING_XL = "text-xl font-semibold text-slate-900"
TEXT_HEADING_2XL = "text-2xl font-semibold text-slate-900"
TEXT_SUBHEAD = "text-sm font-semibold text-slate-700"
TEXT_BODY = "text-sm text-slate-600 font-normal"
TEXT_SECONDARY = "text-sm text-slate-500"
TEXT_MUTED = "text-sm text-slate-400"
TEXT_LABEL_UPPER = "text-xs font-normal text-slate-400 uppercase tracking-wide"
TEXT_LABEL_SECTION = "text-xs font-semibold text-slate-400 uppercase tracking-wide"

# ── v0.7 Design System constants ─────────────────────────────────────────────

# Hero / dark surface typography
TEXT_HERO = "font-bold text-white tracking-tight leading-tight"
TEXT_HERO_SUB = "text-lg font-light text-slate-300"
TEXT_EYEBROW = "text-xs font-semibold text-slate-400 uppercase tracking-widest"

# Stats bar (Phase 16)
STAT_NUMBER = "text-2xl font-bold tabular-nums"
STAT_LABEL = "text-xs uppercase tracking-wide"

# Section structural
SECTION_LABEL = "text-xs font-semibold uppercase tracking-wider"
DIVIDER = "border-t border-slate-200 my-4"

# Template card (Phase 17)
TEMPLATE_CARD = "bg-white border border-slate-200 rounded-xl p-5 cursor-pointer"

# Accent CTA (filled, per D-decision — не Quasar color prop, а Tailwind класс)
BTN_ACCENT_FILLED = "px-5 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 transition-colors duration-150"

# Stats bar item (Phase 16, REGI-01)
STATS_BAR = "flex items-center gap-6 px-6 py-3 bg-white border-b border-slate-200"
STATS_ITEM = "flex flex-col items-center gap-0"

# Document card — Phase 16 (CARD-01, CARD-02, CARD-03)
BREADCRUMB_LINK = "text-sm text-indigo-600 hover:text-indigo-800 cursor-pointer font-medium"
BREADCRUMB_SEP  = "text-sm text-slate-400 mx-1"
BREADCRUMB_CURRENT = "text-sm text-slate-900 font-semibold"

# Section divider header (text-xs uppercase + 1px border-bottom)
SECTION_DIVIDER_HEADER = "text-xs font-semibold text-slate-400 uppercase tracking-wider pb-2 border-b border-slate-200 w-full mb-4"

# AI review block — amber/orange left border accent (CARD-03)
AI_REVIEW_BLOCK = "w-full pl-4 py-1"
AI_REVIEW_BORDER_STYLE = "border-left: 4px solid #f59e0b; background: #fffbeb;"

# Metadata row — compact key-value (CARD-03: no card wrapper)
META_KEY = "text-xs text-slate-400 font-medium uppercase tracking-wide"
META_VAL = "text-sm text-slate-900"

# Version timeline dot
VERSION_DOT = "w-2.5 h-2.5 rounded-full bg-indigo-400 shrink-0 mt-1"
VERSION_LINE = "w-0.5 bg-slate-200 flex-1 min-h-[20px] mx-auto"

# ── Template type color palette (Phase 17, TMPL-01, TMPL-02) ─────────────────
# 4px left border color + badge bg/text per document type
# Keys are Russian strings from Config().document_types_hints
TMPL_TYPE_COLORS: dict[str, dict[str, str]] = {
    "Договор поставки":        {"border": "#4f46e5", "badge_bg": "#eef2ff", "badge_text": "#4338ca", "icon": "📦"},
    "Договор аренды":          {"border": "#059669", "badge_bg": "#d1fae5", "badge_text": "#065f46", "icon": "🏠"},
    "Трудовой договор":        {"border": "#0284c7", "badge_bg": "#e0f2fe", "badge_text": "#0369a1", "icon": "👤"},
    "Договор подряда":         {"border": "#d97706", "badge_bg": "#fef3c7", "badge_text": "#92400e", "icon": "🔧"},
    "Договор оказания услуг":  {"border": "#7c3aed", "badge_bg": "#ede9fe", "badge_text": "#5b21b6", "icon": "✨"},
    "Лицензионное соглашение": {"border": "#db2777", "badge_bg": "#fce7f3", "badge_text": "#9d174d", "icon": "📄"},
    "Договор займа":           {"border": "#dc2626", "badge_bg": "#fee2e2", "badge_text": "#991b1b", "icon": "💰"},
    "Прочее":                  {"border": "#94a3b8", "badge_bg": "#f1f5f9", "badge_text": "#475569", "icon": "📋"},
}

# Fallback for unknown document types
TMPL_TYPE_DEFAULT = TMPL_TYPE_COLORS["Прочее"]

# Template empty state style constants (TMPL-03)
TMPL_EMPTY_ICON = "description"  # Material icon name for ui.icon()
TMPL_EMPTY_TITLE = "text-xl font-semibold text-slate-700 mt-4"
TMPL_EMPTY_BODY = "text-sm text-slate-400 text-center max-w-xs mt-2"
