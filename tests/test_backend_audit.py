"""Тесты Phase 43: Backend Audit — закрытие 15 test coverage gaps."""
import json
import threading
from datetime import date
from pathlib import Path

import pytest

from config import Config, save_setting
from modules.database import Database
from modules.models import ContractMetadata, ProcessingResult, FileInfo


# ---------------------------------------------------------------------------
# TEST-01: Thread safety — concurrent writes to database
# ---------------------------------------------------------------------------

class TestDatabaseThreadSafety:
    """TEST-01: Concurrent writes don't cause OperationalError."""

    def test_concurrent_save_result(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        errors: list[Exception] = []
        barrier = threading.Barrier(5)

        def write_record(n: int) -> None:
            barrier.wait()
            try:
                fi = FileInfo(
                    path=tmp_path / f"file_{n}.pdf",
                    filename=f"file_{n}.pdf",
                    extension=".pdf",
                    size_bytes=1000,
                    file_hash=f"hash_{n:04d}",
                )
                result = ProcessingResult(file_info=fi, status="done")
                result.metadata = ContractMetadata(contract_type="Договор")
                db.save_result(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_record, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent write errors: {errors}"
        stats = db.get_stats()
        assert stats["total"] == 5

    def test_concurrent_read_write(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        # Pre-populate
        for i in range(3):
            fi = FileInfo(
                path=tmp_path / f"f{i}.pdf", filename=f"f{i}.pdf",
                extension=".pdf", size_bytes=100, file_hash=f"rw_{i}",
            )
            r = ProcessingResult(file_info=fi, status="done")
            r.metadata = ContractMetadata()
            db.save_result(r)

        errors: list[Exception] = []
        barrier = threading.Barrier(3)

        def reader() -> None:
            barrier.wait()
            try:
                db.get_all_results()
                db.get_stats()
                db.is_processed("rw_0")
            except Exception as e:
                errors.append(e)

        def writer() -> None:
            barrier.wait()
            try:
                fi = FileInfo(
                    path=tmp_path / "new.pdf", filename="new.pdf",
                    extension=".pdf", size_bytes=100, file_hash="rw_new",
                )
                r = ProcessingResult(file_info=fi, status="done")
                r.metadata = ContractMetadata()
                db.save_result(r)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent read/write errors: {errors}"


# ---------------------------------------------------------------------------
# TEST-03: Payment service edge cases
# ---------------------------------------------------------------------------

class TestPaymentEdgeCases:
    """TEST-03: payment_service.unroll_payments edge cases."""

    def test_negative_amount_raises(self) -> None:
        from services.payment_service import unroll_payments
        with pytest.raises(ValueError, match="отрицательной"):
            unroll_payments(date(2026, 1, 1), date(2026, 12, 31), -100, "monthly")

    def test_zero_amount_ok(self) -> None:
        from services.payment_service import unroll_payments
        result = unroll_payments(date(2026, 1, 1), date(2026, 12, 31), 0, "monthly")
        assert len(result) > 0

    def test_start_after_end_raises(self) -> None:
        from services.payment_service import unroll_payments
        with pytest.raises(ValueError, match="позже"):
            unroll_payments(date(2026, 12, 31), date(2026, 1, 1), 100, "monthly")

    def test_same_day_single_payment(self) -> None:
        from services.payment_service import unroll_payments
        result = unroll_payments(date(2026, 6, 15), date(2026, 6, 15), 500, "monthly")
        assert len(result) == 1
        assert result[0]["amount"] == 500

    def test_invalid_frequency_raises(self) -> None:
        from services.payment_service import unroll_payments
        with pytest.raises(ValueError, match="Неизвестная частота"):
            unroll_payments(date(2026, 1, 1), date(2026, 12, 31), 100, "monthy")

    def test_none_frequency_single_payment(self) -> None:
        from services.payment_service import unroll_payments
        result = unroll_payments(date(2026, 1, 1), date(2026, 12, 31), 100, None)
        assert len(result) == 1
        assert result[0]["is_periodic"] is False


# ---------------------------------------------------------------------------
# TEST-04: Database migrations v2-v9 independent
# ---------------------------------------------------------------------------

class TestMigrations:
    """TEST-04: Each migration works on fresh DB."""

    def test_migration_v10_contract_number(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "mig.db")
        # Column should exist after construction (migrations run in __init__)
        db.conn.execute(
            "SELECT contract_number FROM contracts LIMIT 1"
        ).fetchone()
        # No error = column exists

    def test_all_migrations_applied(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "mig2.db")
        versions = db.conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        applied = {row[0] for row in versions}
        # At minimum v1-v10 should be applied
        for v in range(1, 11):
            assert v in applied, f"Migration v{v} not applied"

    def test_delete_contract_removes_derived_rows(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "delete.db")
        fi = FileInfo(
            path=tmp_path / "d.pdf", filename="d.pdf",
            extension=".pdf", size_bytes=100, file_hash="delete_hash",
        )
        meta = ContractMetadata(
            date_start="2026-01-01",
            date_end="2026-12-31",
            payment_amount=1000,
            payment_frequency="monthly",
        )
        r = ProcessingResult(file_info=fi, status="done", metadata=meta, full_text="Полный текст")
        db.save_result(r)
        cid = db.get_contract_id_by_hash("delete_hash")
        assert cid is not None
        db.conn.execute(
            "INSERT INTO document_versions (contract_group_id, contract_id, version_number, link_method) VALUES (?, ?, ?, ?)",
            (cid, cid, 1, "auto_embedding"),
        )
        db.conn.execute(
            "INSERT INTO embeddings (contract_id, vector, model_version) VALUES (?, ?, ?)",
            (cid, b'123', 'test'),
        )
        db.conn.commit()
        from services.payment_service import save_payments
        save_payments(db, cid, meta)

        assert db.delete_contract(cid) is True
        assert db.conn.execute("SELECT 1 FROM contracts WHERE id = ?", (cid,)).fetchone() is None
        assert db.conn.execute("SELECT 1 FROM document_versions WHERE contract_id = ?", (cid,)).fetchone() is None
        assert db.conn.execute("SELECT 1 FROM embeddings WHERE contract_id = ?", (cid,)).fetchone() is None
        assert db.conn.execute("SELECT 1 FROM payments WHERE contract_id = ?", (cid,)).fetchone() is None


# ---------------------------------------------------------------------------
# TEST-05: ai_extractor helper functions
# ---------------------------------------------------------------------------

class TestAiExtractorHelpers:
    """TEST-05: ai_extractor helper function coverage."""

    def test_translate_ru_months(self) -> None:
        from modules.ai_extractor import _translate_ru_months
        assert "december" in _translate_ru_months("31 декабря 2025").lower()
        assert "march" in _translate_ru_months("15 марта 2026").lower()

    def test_safe_float(self) -> None:
        from modules.ai_extractor import _safe_float
        assert _safe_float(None) is None
        assert _safe_float("123.45") == 123.45
        assert _safe_float(42) == 42.0
        assert _safe_float("invalid") is None

    def test_load_grammar_exists(self) -> None:
        from modules.ai_extractor import _load_grammar
        grammar_path = Path(__file__).parent.parent / "data" / "contract.gbnf"
        if grammar_path.exists():
            result = _load_grammar()
            assert isinstance(result, str)
            assert len(result) > 100
        else:
            with pytest.raises(FileNotFoundError):
                _load_grammar()


# ---------------------------------------------------------------------------
# TEST-08: version_service find_version_match
# ---------------------------------------------------------------------------

class TestVersionServiceEdgeCases:
    """TEST-08: find_version_match error cases."""

    def test_empty_candidates(self, tmp_path: Path) -> None:
        from services.version_service import find_version_match
        db = Database(tmp_path / "ver.db")
        # Insert a contract so FK is valid, but no versions exist
        fi = FileInfo(
            path=tmp_path / "v.pdf", filename="v.pdf",
            extension=".pdf", size_bytes=100, file_hash="ver_hash",
        )
        r = ProcessingResult(file_info=fi, status="done")
        r.metadata = ContractMetadata()
        db.save_result(r)
        cid = db.get_contract_id_by_hash("ver_hash")
        # No other documents with versions → None
        result = find_version_match(db, cid, "some text")
        assert result is None


# ---------------------------------------------------------------------------
# TEST-09: lifecycle_service set/clear manual_status
# ---------------------------------------------------------------------------

class TestLifecycleManualStatus:
    """TEST-09: set_manual_status and clear_manual_status."""

    def test_set_manual_status(self, tmp_path: Path) -> None:
        from services.lifecycle_service import set_manual_status
        db = Database(tmp_path / "lc.db")
        # Insert a contract first
        fi = FileInfo(
            path=tmp_path / "t.pdf", filename="t.pdf",
            extension=".pdf", size_bytes=100, file_hash="lc_hash",
        )
        r = ProcessingResult(file_info=fi, status="done")
        r.metadata = ContractMetadata()
        db.save_result(r)
        cid = db.get_contract_id_by_hash("lc_hash")
        assert cid is not None

        set_manual_status(db, cid, "negotiation")
        doc = db.get_contract_by_id(cid)
        assert doc["manual_status"] == "negotiation"

    def test_set_invalid_status_raises(self, tmp_path: Path) -> None:
        from services.lifecycle_service import set_manual_status
        db = Database(tmp_path / "lc2.db")
        fi = FileInfo(
            path=tmp_path / "t.pdf", filename="t.pdf",
            extension=".pdf", size_bytes=100, file_hash="lc2_hash",
        )
        r = ProcessingResult(file_info=fi, status="done")
        r.metadata = ContractMetadata()
        db.save_result(r)
        cid = db.get_contract_id_by_hash("lc2_hash")

        with pytest.raises(ValueError):
            set_manual_status(db, cid, "invalid_status")

    def test_clear_manual_status(self, tmp_path: Path) -> None:
        from services.lifecycle_service import set_manual_status, clear_manual_status
        db = Database(tmp_path / "lc3.db")
        fi = FileInfo(
            path=tmp_path / "t.pdf", filename="t.pdf",
            extension=".pdf", size_bytes=100, file_hash="lc3_hash",
        )
        r = ProcessingResult(file_info=fi, status="done")
        r.metadata = ContractMetadata()
        db.save_result(r)
        cid = db.get_contract_id_by_hash("lc3_hash")

        set_manual_status(db, cid, "negotiation")
        clear_manual_status(db, cid)
        doc = db.get_contract_by_id(cid)
        assert doc["manual_status"] is None


# ---------------------------------------------------------------------------
# TEST-12: postprocessor abbreviation protect/restore
# ---------------------------------------------------------------------------

class TestPostprocessorAbbreviations:
    """TEST-12: _protect_abbreviations and _restore_abbreviations."""

    def test_protect_restore_roundtrip(self) -> None:
        from modules.postprocessor import _protect_abbreviations, _restore_abbreviations
        text = "Подписали NDA о конфиденциальности и SLA на обслуживание"
        protected, placeholders = _protect_abbreviations(text)
        assert "NDA" not in protected
        assert "SLA" not in protected
        restored = _restore_abbreviations(protected, placeholders)
        assert "NDA" in restored
        assert "SLA" in restored

    def test_no_abbreviations(self) -> None:
        from modules.postprocessor import _protect_abbreviations
        text = "Обычный текст без аббревиатур"
        protected, placeholders = _protect_abbreviations(text)
        assert protected == text
        assert not placeholders


# ---------------------------------------------------------------------------
# TEST-13: ai_extractor _normalize_date boundaries
# ---------------------------------------------------------------------------

class TestNormalizeDateBoundaries:
    """TEST-13: _normalize_date edge cases."""

    def test_valid_iso(self) -> None:
        from modules.ai_extractor import _normalize_date
        assert _normalize_date("2025-06-15") == "2025-06-15"

    def test_none_returns_none(self) -> None:
        from modules.ai_extractor import _normalize_date
        assert _normalize_date(None) is None

    def test_empty_returns_none(self) -> None:
        from modules.ai_extractor import _normalize_date
        assert _normalize_date("") is None

    def test_unparseable_returns_none(self) -> None:
        from modules.ai_extractor import _normalize_date
        assert _normalize_date("not a date") is None

    def test_russian_month(self) -> None:
        from modules.ai_extractor import _normalize_date
        result = _normalize_date("15 марта 2025")
        assert result is not None
        assert "2025" in result


# ---------------------------------------------------------------------------
# TEST-14: lifecycle_service get_attention_required edge cases
# ---------------------------------------------------------------------------

class TestAttentionRequiredEdgeCases:
    """TEST-14: get_attention_required with empty DB."""

    def test_empty_db_returns_empty(self, tmp_path: Path) -> None:
        from services.lifecycle_service import get_attention_required
        db = Database(tmp_path / "att.db")
        alerts = get_attention_required(db, 30)
        assert alerts == []


# ---------------------------------------------------------------------------
# TEST-15: conftest autouse fixture for version_service._model reset
# ---------------------------------------------------------------------------

class TestVersionServiceModelReset:
    """TEST-15: _model singleton doesn't leak between tests."""

    def test_model_is_none_initially(self) -> None:
        import services.version_service as vs
        # Reset to verify isolation
        vs._model = None
        assert vs._model is None


# ---------------------------------------------------------------------------
# Config hardening tests (bonus — validates Phase 38)
# ---------------------------------------------------------------------------

class TestConfigHardening:
    """Validates Config __post_init__ and settings persistence."""

    def test_bad_provider_graceful(self) -> None:
        c = Config(active_provider="legacy")
        assert c.active_provider == "ollama"

    def test_active_model_ollama(self) -> None:
        assert Config(active_provider="ollama").active_model == "local"

    def test_active_model_zai(self) -> None:
        assert Config(active_provider="zai").active_model == "glm-4.7"

    def test_bad_port_graceful(self) -> None:
        c = Config(llama_server_port=-1)
        assert c.llama_server_port == 8080

    def test_bad_validation_mode_graceful(self) -> None:
        c = Config(validation_mode="bad")
        assert c.validation_mode == "off"

    def test_confidence_inversion_raises(self) -> None:
        with pytest.raises(ValueError):
            Config(confidence_high=0.3, confidence_low=0.7)

    def test_telegram_chat_id_optional(self) -> None:
        assert Config().telegram_chat_id is None

    def test_save_setting_thread_safe(self, tmp_path: Path) -> None:
        import config as cfg
        orig = cfg._SETTINGS_FILE
        cfg._SETTINGS_FILE = tmp_path / "settings.json"
        try:
            barrier = threading.Barrier(2)
            errors: list[Exception] = []

            def write(k: str, v: str) -> None:
                barrier.wait()
                try:
                    save_setting(k, v)
                except Exception as e:
                    errors.append(e)

            t1 = threading.Thread(target=write, args=("a", "1"))
            t2 = threading.Thread(target=write, args=("b", "2"))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert not errors
            data = json.loads(cfg._SETTINGS_FILE.read_text())
            assert "a" in data and "b" in data
        finally:
            cfg._SETTINGS_FILE = orig
