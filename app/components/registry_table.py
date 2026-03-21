"""Компонент таблицы реестра документов — AG Grid с живыми данными.

Phase 08, Plans 01-03.

Exports: COLUMN_DEFS, render_registry_table, load_table_data, _fetch_rows, _fuzzy_filter,
         build_version_rows, load_version_children
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

# Expand/collapse toggle (first column) — per D-15, D-16
_EXPAND_CELL_RENDERER = """(params) => {
    if (!params.value) return '';
    const expanded = params.data && params.data.is_expanded;
    return `<span class="expand-icon" style="cursor:pointer">${expanded ? '\u25bc' : '\u25b6'}</span>`;
}"""

# Actions cell renderer (last column) — per D-12, D-13
_ACTIONS_CELL_RENDERER = """(params) => {
    if (params.data && params.data.is_child) return '';
    const div = document.createElement('div');
    div.className = 'actions-cell';
    div.innerHTML = '<span class="action-icon" title="\u041c\u0435\u043d\u044e">\u22ef</span>';
    return div;
}"""

COLUMN_DEFS = [
    # Expand toggle (D-15, D-16)
    {
        "headerName": "",
        "field": "has_children",
        "width": 40,
        "sortable": False,
        "filter": False,
        "resizable": False,
        "cellRenderer": _EXPAND_CELL_RENDERER,
    },
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
    # Actions column (D-12) — last
    {
        "headerName": "",
        "field": "actions",
        "width": 80,
        "sortable": False,
        "filter": False,
        "resizable": False,
        "cellRenderer": _ACTIONS_CELL_RENDERER,
    },
    # Скрытые колонки (D-02)
    {"field": "date_end", "hide": True},
    {"field": "validation_score", "hide": True},
    {"field": "filename", "hide": True},
    {"field": "processed_at", "hide": True, "sort": "desc"},
    {"field": "id", "hide": True},
    {"field": "is_child", "hide": True},
    {"field": "is_expanded", "hide": True},
    {"field": "indent", "hide": True},
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


def build_version_rows(base_rows: list[dict], db) -> list[dict]:
    """Помечает строки реестра с версиями (dopsoглашения).

    Per D-15, D-16, D-17: lazy подход — только помечает родителей.
    Дочерние строки загружаются отдельно через load_version_children при раскрытии.

    Args:
        base_rows: плоский список строк из _fetch_rows
        db: Database объект с db.conn
    Returns:
        тот же список с добавленными полями has_children, is_child, is_expanded, indent
    """
    ids = [r["id"] for r in base_rows]
    if not ids:
        return base_rows

    # Bulk check: какие contract_id имеют версии в группах >1 членов
    placeholders = ",".join("?" * len(ids))
    version_counts: dict[int, int] = {}
    try:
        cursor = db.conn.execute(
            f"SELECT contract_id, contract_group_id FROM document_versions WHERE contract_id IN ({placeholders})",
            ids,
        )
        groups: dict[int, list[int]] = {}
        for row in cursor:
            gid = row[1]
            cid = row[0]
            groups.setdefault(gid, []).append(cid)
        # Родитель имеет детей если его группа содержит >1 member
        for gid, members in groups.items():
            if len(members) > 1:
                for cid in members:
                    version_counts[cid] = len(members)
    except Exception:
        pass  # document_versions может отсутствовать в старых БД

    result = []
    for row in base_rows:
        row["has_children"] = row["id"] in version_counts and version_counts[row["id"]] > 1
        row["is_child"] = False
        row["is_expanded"] = False
        row["indent"] = 0
        result.append(row)
    return result


async def load_version_children(grid, db, parent_id: int) -> None:
    """Загружает и вставляет дочерние строки версий после родительской строки.

    Per D-15, D-17: вызывается при клике ▶ на строке с has_children=True.
    Вставляет дочерние строки с is_child=True, indent=1 после родителя.
    """
    from nicegui import run
    from services.version_service import get_version_group

    versions = await run.io_bound(get_version_group, db, parent_id)
    if not versions:
        return

    # Загружаем метаданные дочерних контрактов
    child_ids = [v.contract_id for v in versions if v.contract_id != parent_id]
    if not child_ids:
        return

    placeholders = ",".join("?" * len(child_ids))
    try:
        rows_raw = db.conn.execute(
            f"SELECT id, contract_type, counterparty, amount, computed_status FROM ("
            f"SELECT id, contract_type, counterparty, amount, "
            f"CASE WHEN manual_status IS NOT NULL THEN manual_status "
            f"WHEN date_end IS NULL THEN 'unknown' "
            f"WHEN date_end < date('now') THEN 'expired' "
            f"ELSE 'active' END AS computed_status "
            f"FROM contracts WHERE id IN ({placeholders}))",
            child_ids,
        ).fetchall()
    except Exception as exc:
        logger.warning("Ошибка загрузки дочерних версий: %s", exc)
        return

    child_rows = [
        {
            "id": r[0],
            "contract_type": r[1],
            "counterparty": r[2],
            "amount": r[3],
            "computed_status": r[4],
            "has_children": False,
            "is_child": True,
            "is_expanded": False,
            "indent": 1,
        }
        for r in rows_raw
    ]

    # Найти позицию родителя в rowData и вставить после
    row_data: list[dict] = grid.options.get("rowData", [])
    parent_idx = next(
        (i for i, r in enumerate(row_data) if r.get("id") == parent_id), None
    )
    if parent_idx is not None:
        # Пометить родителя как раскрытого
        row_data[parent_idx]["is_expanded"] = True
        # Удалить старые дочерние строки этого родителя если были
        while parent_idx + 1 < len(row_data) and row_data[parent_idx + 1].get("is_child"):
            row_data.pop(parent_idx + 1)
        # Вставить новые
        for i, child in enumerate(child_rows):
            row_data.insert(parent_idx + 1 + i, child)
        grid.options["rowData"] = row_data
        grid.update()
        logger.debug("Вставлено %d дочерних версий после parent_id=%d", len(child_rows), parent_id)


def _collapse_version_children(grid, parent_id: int) -> None:
    """Скрывает дочерние строки версий (сворачивает группу)."""
    row_data: list[dict] = grid.options.get("rowData", [])
    parent_idx = next(
        (i for i, r in enumerate(row_data) if r.get("id") == parent_id), None
    )
    if parent_idx is not None:
        row_data[parent_idx]["is_expanded"] = False
        # Удалить дочерние строки
        while parent_idx + 1 < len(row_data) and row_data[parent_idx + 1].get("is_child"):
            row_data.pop(parent_idx + 1)
        grid.options["rowData"] = row_data
        grid.update()


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
    Per D-15: помечает строки с версиями через build_version_rows.
    """
    from nicegui import run

    rows = await run.io_bound(
        _fetch_rows,
        state.current_client,
        segment,
        state.filter_search,
        state.warning_days_threshold,
    )
    # Пометить строки с версиями (D-15, D-16)
    db = _client_manager.get_db(state.current_client)
    rows = build_version_rows(rows, db)

    # Per D-20, Pitfall 5: sync filtered_doc_ids on every data load, not just on click
    state.filtered_doc_ids = [r['id'] for r in rows if not r.get('is_child')]

    grid.options["rowData"] = rows
    grid.update()
    logger.debug("Загружено %d строк реестра (сегмент=%s)", len(rows), segment)
