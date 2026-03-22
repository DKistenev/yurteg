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
SEG_INACTIVE = "px-4 py-1.5 text-sm font-semibold rounded-md text-slate-600 hover:bg-slate-100 transition-colors duration-150"

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
