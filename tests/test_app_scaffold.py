"""Tests for Phase 7 app scaffold: AppState dataclass, page modules, header component.

All tests are import-level or dataclass-level — no NiceGUI server required.
get_state() runtime test is skipped (requires NiceGUI app context).
"""
import pytest


class TestAppStateFields:
    """Verify AppState dataclass structure and defaults."""

    def test_appstate_has_all_fields(self):
        """AppState must have exactly 21 fields (20 original + filtered_doc_ids added in Phase 9)."""
        from app.state import AppState
        fields = AppState.__dataclass_fields__
        assert len(fields) == 21, f"Expected 21 fields, got {len(fields)}: {list(fields.keys())}"

    def test_appstate_defaults(self):
        """Verify default values match spec."""
        from app.state import AppState
        s = AppState()

        # Processing
        assert s.source_dir == ""
        assert s.output_dir is None
        assert s.report_path is None
        assert s.show_results is False
        assert s.force_reprocess is False
        assert s.processing is False
        assert s.processing_time is None
        assert s.upload_dir is None

        # Settings cache
        assert s.warning_days_threshold == 30
        assert s.telegram_chat_id == 0
        assert s.telegram_server_url == ""
        assert s.tg_queue_fetched is False
        assert s.startup_toast_shown is False
        assert s.deadlines_pushed is False
        assert s.auto_bind_summary is None

        # Navigation
        assert s.current_client == "Основной реестр"
        assert s.selected_doc_id is None

        # Filters
        assert s.filter_type == ""
        assert s.filter_status == ""
        assert s.filter_search == ""

    def test_appstate_field_types(self):
        """Verify field type annotations are present and sane."""
        from app.state import AppState
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(AppState)}

        # Check a subset of critical types
        assert fields['source_dir'].default == ""
        assert fields['processing'].default is False
        assert fields['warning_days_threshold'].default == 30
        assert fields['current_client'].default == "Основной реестр"
        assert fields['selected_doc_id'].default is None

    def test_appstate_mutable(self):
        """AppState fields can be mutated (it's a plain dataclass, not frozen)."""
        from app.state import AppState
        s = AppState()
        s.source_dir = "/some/path"
        s.processing = True
        s.current_client = "Клиент А"
        assert s.source_dir == "/some/path"
        assert s.processing is True
        assert s.current_client == "Клиент А"


class TestPageModules:
    """Verify page modules are importable and have build() callables."""

    def test_page_modules_importable(self):
        """All page modules must be importable."""
        from app.pages import registry, document, templates, settings
        assert registry is not None
        assert document is not None
        assert templates is not None
        assert settings is not None

    def test_page_modules_have_build(self):
        """Each page module must expose a callable build attribute."""
        from app.pages import registry, document, templates, settings
        assert callable(registry.build), "registry.build must be callable"
        assert callable(document.build), "document.build must be callable"
        assert callable(templates.build), "templates.build must be callable"
        assert callable(settings.build), "settings.build must be callable"


class TestHeaderModule:
    """Verify header component is importable."""

    def test_header_importable(self):
        """render_header must be importable from app.components.header."""
        from app.components.header import render_header
        assert callable(render_header)

    def test_nav_link_importable(self):
        """_nav_link helper must exist in header module."""
        import app.components.header as header_mod
        assert hasattr(header_mod, '_nav_link')
        assert callable(header_mod._nav_link)


class TestStateModule:
    """Verify state module exports."""

    def test_state_module_importable(self):
        """AppState and get_state must be importable from app.state."""
        from app.state import AppState, get_state
        assert AppState is not None
        assert callable(get_state)

    def test_get_state_skipped_without_context(self):
        """get_state() requires NiceGUI app context — skip at import level."""
        from app.state import get_state
        # We only verify get_state is callable; runtime test requires NiceGUI server
        assert callable(get_state)
        # Would raise RuntimeError or similar outside NiceGUI context — that's expected
