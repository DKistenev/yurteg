# Testing Patterns

**Analysis Date:** 2026-03-25

## Test Framework

**Runner:**
- pytest (implicit from `pytest.ini` and test file imports)
- Config: `pytest.ini`
- Markers: `@pytest.mark.slow` for tests >5 sec, `@pytest.mark.xfail` for TDD RED phase tests

**Assertion Library:**
- Standard `assert` statements (no external library)
- `pytest.raises()` for exception testing (implicit in pytest)
- `unittest.mock.patch`, `MagicMock` for mocking

**Run Commands:**
```bash
pytest                              # Run all tests
pytest -m "not slow"                # Skip slow tests (>5 sec)
pytest tests/test_lifecycle.py      # Run specific test file
pytest tests/test_lifecycle.py::test_auto_status_computation  # Run specific test
```

## Test File Organization

**Location:**
- Co-located with source code: `tests/` directory at project root
- Structure mirrors source: `tests/test_{module_name}.py` for `modules/{module_name}.py`
- Examples: `tests/test_lifecycle.py` (Phase 2), `tests/test_registry_view.py` (Phase 8), `tests/test_app_scaffold.py` (Phase 7)

**Naming:**
- File: `test_{feature}.py`
- Function: `def test_{specific_scenario}():` (snake_case)
- Class: `class Test{Feature}:` (PascalCase)

**Structure:**
```
tests/
├── test_service_layer.py           # FUND-02: Services isolate from Streamlit
├── test_lifecycle.py                # LIFE-01 through LIFE-06 (Phase 2)
├── test_registry_view.py            # Data layer, fuzzy filter, sorting
├── test_app_scaffold.py             # AppState dataclass, page modules
├── test_payments.py                 # Payment unroll, save/load
├── test_migrations.py               # Database schema migrations
├── test_versioning.py               # Document version linking
├── test_client_manager.py           # Multi-client isolation (Phase 3)
└── test_providers.py                # AI provider factory patterns
```

## Test Structure

**Test File Header Pattern:**
```python
"""Тесты {feature} — {brief description}.

{Phase info}: {requirement codes}
Example: Wave 0: тест-скелеты созданы до реализации (RED стадия).
"""
import pytest
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch
```

**Docstring references phases and requirement IDs:**
- Example: `LIFE-01: SQL CASE возвращает expired/expiring/active/unknown по date_end`
- Example: `FUND-02: services.pipeline_service не импортирует streamlit`
- Used to track which features tests validate

**Fixture Pattern:**
```python
@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД с миграциями для тестов."""
    try:
        from modules.database import Database
        db = Database(tmp_path / "test.db", tmp_path)
        yield db
        db.close()
    except ImportError:
        pytest.skip("modules.database недоступен — запустите после 02-01")
```

Fixtures use:
- `@pytest.fixture` decorator
- Docstring in Russian describing setup
- `yield` for cleanup (teardown)
- `pytest.skip()` to skip if dependency unavailable
- Return or yield test object (not print)

**Test Class Structure:**
```python
class TestAppStateFields:
    """Verify AppState dataclass structure and defaults."""

    def test_appstate_has_all_fields(self):
        """AppState must have exactly 19 fields..."""
        from app.state import AppState
        fields = AppState.__dataclass_fields__
        assert len(fields) == 19, f"Expected 19 fields, got {len(fields)}: ..."

    def test_appstate_defaults(self):
        """Verify default values match spec."""
        from app.state import AppState
        s = AppState()
        assert s.source_dir == ""
        assert s.processing is False
```

Tests use:
- Class grouping by feature/component
- Imports inside test function (not top-level) — allows skipping if module unavailable
- Descriptive assertion messages with actual/expected
- One assertion per test (or closely related group)

## Mocking

**Framework:** `unittest.mock` from Python stdlib

**Patterns:**

```python
from unittest.mock import MagicMock, patch

# Simple mock
mock_db = MagicMock()
mock_db.get_all_results.return_value = [{"id": 1, "filename": "test.pdf"}]

# Mock in test
def test_registry_get_contracts():
    from services import registry_service
    mock_db = MagicMock()
    mock_db.get_all_results.return_value = [{"id": 1}]

    result = registry_service.get_all_contracts(mock_db)

    mock_db.get_all_results.assert_called_once()
    assert result == [{"id": 1}]

# Patching
@patch("services.pipeline_service.extract_text")
def test_pipeline(mock_extract):
    mock_extract.return_value = ExtractedText(text="...", page_count=1, ...)
    # Test code uses mock
```

**What to Mock:**
- External services (APIs, databases) — use MagicMock
- File system — use `tmp_path` fixture, don't mock os.path
- Imports only when necessary to isolate (e.g., `@patch("module.func")`)

**What NOT to Mock:**
- Pure functions — test directly with real inputs
- Dataclasses — instantiate real, not mock
- Fixtures (temp_db, tmp_path) — use real, not mocks

**Monkeypatch Pattern:**
```python
def test_with_monkeypatch(monkeypatch):
    """Use pytest's monkeypatch for temporary replacements."""
    from services import lifecycle_service
    monkeypatch.setattr(lifecycle_service, "WARNING_DAYS", 60)
    # Test uses modified value
    assert lifecycle_service.WARNING_DAYS == 60
```

## Fixtures and Factories

**Test Data:**

```python
@pytest.fixture
def tmp_db(tmp_path):
    """Создаёт временную SQLite БД с тестовыми договорами."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)

    # Вставляем тестовые договоры
    rows = [
        {
            "filename": "active1.pdf",
            "file_hash": "hash_active1",
            "status": "done",
            "contract_type": "Договор аренды",
            "counterparty": "ООО Ромашка",
            "date_end": "2030-12-31",
            "validation_score": 0.9,
        },
        # ... more rows
    ]
    for row in rows:
        db._conn.execute(
            "INSERT INTO contracts (filename, file_hash, status, ...) "
            "VALUES (:filename, :file_hash, :status, ...)",
            row
        )
    db._conn.commit()

    yield db
    db.close()
```

**Location:**
- Fixtures in same file as tests (`tests/test_*.py`)
- Shared fixtures could live in `conftest.py` (not present yet)
- No factory pattern; dataclasses instantiated directly in tests

## Coverage

**Requirements:** No explicit coverage requirement enforced

**Approach:**
- TDD (RED → GREEN → REFACTOR) — tests written before code
- Phases completed with `Wave 0: тест-скелеты созданы до реализации` (RED) before implementation
- `@pytest.mark.xfail` for RED phase tests (not yet implemented)

**Example - TDD RED Phase:**
```python
@pytest.mark.xfail(reason="lifecycle_service создаётся в 02-01", strict=False)
def test_auto_status_computation(temp_db):
    """LIFE-01: SQL CASE корректно вычисляет статус по date_end."""
    from services.lifecycle_service import get_computed_status_sql
    # Test written before service exists
    # Marked xfail until 02-01 completes
```

## Test Types

**Unit Tests:**
- Scope: Single function/method in isolation
- Approach: Direct function call with known inputs, assert outputs
- Examples: `test_compute_file_hash()` (scanner), `test_fuzzy_filter_single_word()` (registry)
- Location: `tests/test_{module}.py`

**Integration Tests:**
- Scope: Multiple modules working together
- Approach: Use real database fixtures (`tmp_db`), test end-to-end flows
- Examples: `test_payment_save_and_load()` (payment service + database), `test_build_version_rows()` (database + version service)
- Location: Same `tests/test_*.py` files

**E2E Tests:**
- Framework: Not used (NiceGUI integration testing not automated)
- Manual testing documented in phase plans instead

**Service Layer Tests:**
- Focus: Verify services don't import Streamlit, have correct signatures
- Pattern: Import inspection, mock verification
- Example: `test_no_streamlit_import()` — verifies `services/pipeline_service.py` source doesn't import streamlit
- Location: `tests/test_service_layer.py`

## Common Patterns

**Async Testing:**
No async tests found — NiceGUI UI tests are skipped (require running app).

**Error Testing:**
```python
def test_missing_file():
    """Test error handling for missing input."""
    from modules.scanner import scan_directory
    with pytest.raises(FileNotFoundError, match="Директория не найдена"):
        scan_directory(Path("/nonexistent"), config)
```

**Parametrized Tests:**
Not used yet in codebase. Could be added with:
```python
@pytest.mark.parametrize("input,expected", [
    ("test.pdf", "pdf"),
    ("test.docx", "docx"),
])
def test_extension(filename, expected):
    assert get_extension(filename) == expected
```

**Database Tests:**
```python
@pytest.fixture
def tmp_db(tmp_path):
    db = Database(tmp_path / "test.db")
    yield db
    db.close()  # Cleanup

def test_fetch_rows(tmp_db):
    """Test data retrieval from database."""
    rows = tmp_db.get_all_results()
    assert len(rows) > 0
    assert "filename" in rows[0]
```

## Test Execution

**Command Examples:**
```bash
# All tests
pytest

# Skip slow tests (>5 sec)
pytest -m "not slow"

# Single file
pytest tests/test_lifecycle.py

# Single test
pytest tests/test_lifecycle.py::test_auto_status_computation

# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Exit with error if no tests run
pytest --strict-markers
```

**CI/CD:**
Not configured (no github-ci, jenkins, etc. in repo)

## Debugging Tests

**Print in Tests:**
```python
def test_something():
    result = function()
    print(f"Result: {result}")  # visible with pytest -s
    assert result == expected
```

**Inspect Test Data:**
```python
def test_data(tmp_db):
    rows = tmp_db.get_all_results()
    print(json.dumps(rows, indent=2))  # visible with pytest -s
    assert len(rows) > 0
```

**Use pdb:**
```python
def test_with_debugger():
    import pdb; pdb.set_trace()  # Breaks here when running pytest
```

---

*Testing analysis: 2026-03-25*
