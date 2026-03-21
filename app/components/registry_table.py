"""Компонент таблицы реестра документов — AG Grid с живыми данными.

Phase 08, Plan 01.

Exports: COLUMN_DEFS, render_registry_table, load_table_data, _fetch_rows, _fuzzy_filter
"""
import json
import logging
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

from services.client_manager import ClientManager
from services.lifecycle_service import get_computed_status_sql

if TYPE_CHECKING:
    from app.state import AppState

logger = logging.getLogger(__name__)

# ── Singleton ──────────────────────────────────────────────────────────────────

# Per Pitfall 5 from RESEARCH: ClientManager инициализируется один раз на модуль
_client_manager = ClientManager()

# ── Fuzzy search config ───────────────────────────────────────────────────────

_SEARCH_FIELDS = ("contract_type", "counterparty", "subject", "filename", "amount")
_THRESHOLD = 80

# ── Status cell renderer (JS) ──────────────────────────────────────────────────

STATUS_CELL_RENDERER = """(params) => {
    const labels = {
        active:      ['\u2714', '\u0414\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442', 'status-active'],
        expiring:    ['\u26a0', '\u0421\u043a\u043e\u0440\u043e \u0438\u0441\u0442\u0435\u043a\u0430\u0435\u0442', 'status-expiring'],
        expired:     ['\u2717', '\u0418\u0441\u0442\u0451\u043a', 'status-expired'],
        unknown:     ['?', '\u041d\u0435\u0442 \u0434\u0430\u0442\u044b', 'status-unknown'],
        terminated:  ['\u2716', '\u0420\u0430\u0441\u0442\u043e\u0440\u0433\u043d\u0443\u0442', 'status-terminated'],
        extended:    ['\u21bb', '\u041f\u0440\u043e\u0434\u043b\u0451\u043d', 'status-extended'],
        negotiation: ['~', '\u041d\u0430 \u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u043d\u0438\u0438', 'status-negotiation'],
        suspended:   ['\u23f8', '\u041f\u0440\u0438\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d', 'status-suspended'],
    };
    const [icon, label, cls] = labels[params.value] || ['?', params.value, 'status-unknown'];
    return `<span class="${cls}">${icon} ${label}</span>`;
}"""

# ── Column definitions ─────────────────────────────────────────────────────────

COLUMN_DEFS = [
    {
        "headerName": "Тип документа",
        "field": "contract_type",
        "flex": 2,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "sortable": True,
    },
    {
        "headerName": "Контрагент",
        "field": "counterparty",
        "flex": 2,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "sortable": True,
    },
    {
        "headerName": "Статус",
        "field": "computed_status",
        "width": 160,
        "sortable": True,
        "filter": "agTextColumnFilter",
        "cellRenderer": STATUS_CELL_RENDERER,
    },
    {
        "headerName": "Сумма",
        "field": "amount",
        "width": 140,
        "sortable": True,
        "filter": "agTextColumnFilter",
    },
    # Скрытые колонки (D-02)
    {"field": "date_end", "hide": True},
    {"field": "validation_score", "hide": True},
    {"field": "filename", "hide": True},
    {"field": "processed_at", "hide": True, "sort": "desc"},
    {"field": "id", "hide": True},
]

# ── Data layer ─────────────────────────────────────────────────────────────────


def _fuzzy_filter(rows: list[dict], query: str) -> list[dict]:
    """Фильтрует строки по нечёткому поиску.

    Per D-07, D-08, D-09:
    - Разбивает query на слова
    - Каждое слово проверяется по всем _SEARCH_FIELDS через fuzz.partial_ratio
    - Строка проходит если ВСЕ слова нашли совпадение ≥ _THRESHOLD (AND-логика)
    - Пустой query возвращает все строки
    """
    if not query.strip():
        return rows

    words = query.lower().split()
    result = []
    for row in rows:
        haystack = " ".join(str(row.get(f) or "") for f in _SEARCH_FIELDS).lower()
        if all(fuzz.partial_ratio(word, haystack) >= _THRESHOLD for word in words):
            result.append(row)
    return result


def _fetch_rows(
    client_name: str,
    segment: str,
    search: str,
    warning_days: int,
) -> list[dict]:
    """Загружает и фильтрует строки реестра из БД.

    Синхронная функция — вызывается через run.io_bound() из async контекста.

    Per Pattern 1 from RESEARCH:
    - Получает БД через ClientManager
    - Вычисляет computed_status через SQL CASE (get_computed_status_sql)
    - Фильтрует по сегменту (Python-side, D-05, D-06)
    - Применяет fuzzy search если search непустой (D-07)
    """
    db = _client_manager.get_db(client_name)
    sql = f"""
        SELECT id, contract_type, counterparty, amount, filename, subject,
               date_end, validation_score, validation_warnings, processed_at,
               manual_status,
               {get_computed_status_sql(warning_days)} AS computed_status
        FROM contracts
        WHERE status = 'done'
        ORDER BY processed_at DESC
    """
    rows = [dict(r) for r in db.conn.execute(sql, {"warning_days": warning_days}).fetchall()]

    # Segment filter (D-05, D-06)
    if segment == "expiring":
        rows = [r for r in rows if r.get("computed_status") == "expiring"]
    elif segment == "attention":
        rows = [
            r for r in rows
            if (r.get("validation_score") or 1.0) < 0.7
            or bool(json.loads(r.get("validation_warnings") or "[]"))
        ]

    # Fuzzy search (D-07, D-08, D-09)
    if search.strip():
        rows = _fuzzy_filter(rows, search)

    return rows


# ── UI components ──────────────────────────────────────────────────────────────


async def render_registry_table(state: "AppState"):
    """Создаёт и возвращает пустой ui.aggrid для реестра.

    Данные загружаются отдельно через load_table_data().
    """
    from nicegui import ui

    grid = ui.aggrid(
        {
            "columnDefs": COLUMN_DEFS,
            "rowData": [],
            "domLayout": "autoHeight",
            "defaultColDef": {
                "sortable": True,
                "resizable": True,
            },
            "rowSelection": "single",
        }
    ).classes("w-full")

    return grid


async def load_table_data(grid, state: "AppState", segment: str = "all") -> None:
    """Загружает данные в grid из БД.

    Использует run.io_bound для блокирующего DB-вызова.
    Per Pitfall 2 from RESEARCH: обновляет rowData через grid.options + grid.update().
    """
    from nicegui import run

    rows = await run.io_bound(
        _fetch_rows,
        state.current_client,
        segment,
        state.filter_search,
        state.warning_days_threshold,
    )
    grid.options["rowData"] = rows
    grid.update()
    logger.debug("Загружено %d строк реестра (сегмент=%s)", len(rows), segment)
