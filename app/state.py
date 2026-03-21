"""AppState dataclass — единственный источник правды для UI-состояния.

Per D-04: AppState dataclass в app/state.py.
Per D-05: app.storage.client['state'] для хранения (per-connection, in-memory).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AppState:
    """Typed UI state — замена 45 st.session_state ключей из Streamlit."""

    # Processing
    source_dir: str = ""
    output_dir: Optional[Path] = None
    report_path: Optional[Path] = None
    show_results: bool = False
    force_reprocess: bool = False
    processing: bool = False
    processing_time: Optional[float] = None
    upload_dir: Optional[Path] = None

    # Settings cache (UI-side — canonical source is ~/.yurteg/settings.json)
    warning_days_threshold: int = 30
    telegram_chat_id: int = 0
    telegram_server_url: str = ""
    tg_queue_fetched: bool = False
    startup_toast_shown: bool = False
    deadlines_pushed: bool = False
    auto_bind_summary: Optional[dict] = None

    # Navigation
    current_client: str = "Основной реестр"
    selected_doc_id: Optional[int] = None
    filtered_doc_ids: list = field(default_factory=list)

    # Filters
    filter_type: str = ""
    filter_status: str = ""
    filter_search: str = ""


def get_state() -> AppState:
    """Return per-connection AppState from app.storage.client (D-05)."""
    from nicegui import app
    if 'state' not in app.storage.client:
        app.storage.client['state'] = AppState()
    return app.storage.client['state']
