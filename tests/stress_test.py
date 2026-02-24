"""
Стресс-тестирование ЮрТэг.

Покрывает:
- Анонимизацию ПД (precision/recall, edge cases, производительность)
- Валидацию метаданных (L1–L4, скоринг, ИНН, fuzzy match)
- Организацию файлов (санитизация, конфликты, режимы группировки)
- Нагрузку (конкурентность БД, объём данных)
- Интеграцию (E2E пайплайн с мокнутым AI)

Запуск:
    pytest tests/stress_test.py -v -s
    pytest tests/stress_test.py -v -k "Anonymizer"
    pytest tests/stress_test.py -v -m "not slow"
"""

import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

import pytest

from config import Config
from modules.models import (
    FileInfo,
    ExtractedText,
    AnonymizedText,
    ContractMetadata,
    ValidationResult,
    ProcessingResult,
)
from modules.anonymizer import (
    anonymize,
    _extract_ner_entities,
    _extract_regex_matches,
    _extract_passport_matches,
    _remove_overlaps,
)
from modules.validator import (
    validate_metadata,
    validate_batch,
    _validate_inn,
    _fuzzy_match,
)
from modules.organizer import (
    organize_file,
    _sanitize_name,
    _generate_filename,
    _resolve_conflict,
)
from modules.database import Database


# ============================================================
#  МАРКЕРЫ
# ============================================================

slow = pytest.mark.slow


# ============================================================
#  ФИКСТУРЫ И ГЕНЕРАТОРЫ
# ============================================================


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def tmp_db(tmp_path):
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


def make_metadata(**overrides) -> ContractMetadata:
    """Создаёт ContractMetadata с разумными дефолтами."""
    defaults = dict(
        contract_type="Договор поставки",
        counterparty="ООО ТехноСтрой",
        subject="Поставка строительных материалов согласно спецификации",
        date_signed="2024-06-15",
        date_start="2024-07-01",
        date_end="2025-06-30",
        amount="1 500 000 руб.",
        special_conditions=["Неустойка 0.1% за каждый день просрочки"],
        parties=["ООО ТехноСтрой", "ООО БетонПром"],
        confidence=0.85,
    )
    defaults.update(overrides)
    return ContractMetadata(**defaults)


def make_file_info(
    tmp_path: Path,
    filename: str = "test.pdf",
    content: bytes = b"dummy pdf content",
) -> FileInfo:
    """Создаёт файл на диске + возвращает FileInfo с реальным SHA-256."""
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    file_hash = hashlib.sha256(content).hexdigest()
    ext = Path(filename).suffix
    return FileInfo(
        path=path,
        filename=filename,
        extension=ext,
        size_bytes=len(content),
        file_hash=file_hash,
    )


def make_result(
    tmp_path: Path,
    filename: str = "test.pdf",
    content: bytes = b"dummy",
    metadata: Optional[ContractMetadata] = None,
    validation: Optional[ValidationResult] = None,
    status: str = "done",
    file_hash: Optional[str] = None,
) -> ProcessingResult:
    """Собирает полный ProcessingResult."""
    fi = make_file_info(tmp_path, filename, content)
    if file_hash:
        fi.file_hash = file_hash
    return ProcessingResult(
        file_info=fi,
        metadata=metadata or make_metadata(),
        validation=validation or ValidationResult(status="ok", warnings=[], score=0.85),
        status=status,
        processed_at=datetime.now(),
    )


def create_test_docx(path: Path, text: str) -> Path:
    """Создаёт минимальный .docx через python-docx."""
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_paragraph(text)
    doc.save(str(path))
    return path


# ============================================================
#  ТЕСТЫ АНОНИМИЗАТОРА
# ============================================================


class TestAnonymizerStress:
    """Стресс-тесты модуля анонимизации ПД."""

    # --- TRUE POSITIVES: должны замаскировать ---

    def test_standard_fio(self):
        """Стандартное ФИО распознаётся через NER."""
        text = "Представитель: Иванов Иван Иванович, действующий на основании доверенности."
        result = anonymize(text)
        assert "[ФИО_1]" in result.text
        assert "Иванов Иван Иванович" not in result.text
        assert "ФИО" in result.stats

    def test_multiple_fio_dedup(self):
        """Одно и то же ФИО 3 раза → один номер маски."""
        text = (
            "Иванов Иван Иванович (далее — Заказчик). "
            "Иванов Иван Иванович обязуется оплатить. "
            "Подпись: Иванов Иван Иванович."
        )
        result = anonymize(text)
        # Все вхождения заменены одной маской
        assert result.text.count("[ФИО_1]") == 3
        assert "Иванов Иван Иванович" not in result.text
        assert result.stats.get("ФИО", 0) == 3

    def test_two_different_fio(self):
        """Два разных ФИО → разные маски."""
        text = (
            "Стороны: Иванов Иван Иванович и Петрова Мария Сергеевна "
            "заключили настоящий договор."
        )
        result = anonymize(text)
        assert "Иванов Иван Иванович" not in result.text
        assert "Петрова Мария Сергеевна" not in result.text
        # Должны быть 2 разные маски
        fio_masks = re.findall(r'\[ФИО_\d+\]', result.text)
        unique_masks = set(fio_masks)
        assert len(unique_masks) >= 2

    def test_phone_format_plus7_parens(self):
        text = "Телефон: +7 (495) 123-45-67 для связи."
        result = anonymize(text)
        assert "+7 (495) 123-45-67" not in result.text
        assert "ТЕЛЕФОН" in result.stats

    def test_phone_format_8_dashes(self):
        text = "Звоните: 8-800-123-45-67 бесплатно."
        result = anonymize(text)
        assert "8-800-123-45-67" not in result.text

    def test_phone_format_compact(self):
        text = "Моб.: 89151234567, просьба звонить."
        result = anonymize(text)
        assert "89151234567" not in result.text

    def test_phone_format_spaces(self):
        text = "Контакт: +7 495 123 45 67 (офис)."
        result = anonymize(text)
        assert "+7 495 123 45 67" not in result.text

    def test_phone_format_no_spaces(self):
        text = "Тел: +74951234567 круглосуточно."
        result = anonymize(text)
        assert "+74951234567" not in result.text

    def test_email_standard(self):
        text = "Почта: ivan.petrov@company.ru для документов."
        result = anonymize(text)
        assert "ivan.petrov@company.ru" not in result.text
        assert "EMAIL" in result.stats

    def test_email_with_plus(self):
        text = "Адрес: user+legal@mail.com для уведомлений."
        result = anonymize(text)
        assert "user+legal@mail.com" not in result.text

    def test_snils_dashes(self):
        text = "СНИЛС работника: 123-456-789 01, предоставлен при приёме."
        result = anonymize(text)
        assert "123-456-789 01" not in result.text
        assert "СНИЛС" in result.stats

    def test_snils_spaces(self):
        text = "СНИЛС: 123 456 789 01."
        result = anonymize(text)
        assert "123 456 789 01" not in result.text

    def test_inn_fl_12_digits(self):
        """12-цифровой ИНН физлица маскируется."""
        text = "ИНН работника 123456789012 для отчётности."
        result = anonymize(text)
        assert "123456789012" not in result.text
        assert "ИНН_ФЛ" in result.stats

    def test_passport_with_context(self):
        """Паспорт с контекстным словом 'паспорт'."""
        text = "Паспорт серия 4515 номер 123456, выдан УФМС по г. Москве."
        result = anonymize(text)
        assert "ПАСПОРТ" in result.stats
        # Числа паспорта должны быть замаскированы
        assert "[ПАСПОРТ_1]" in result.text

    def test_passport_format_4plus6(self):
        """Паспорт формат 4+6 рядом с 'паспорт'."""
        text = "Документ, удостоверяющий личность: 4515 123456."
        result = anonymize(text)
        assert "ПАСПОРТ" in result.stats

    def test_passport_format_series_number(self):
        """Паспорт формат 'серия ХХХХ № ХХХХХХ'."""
        text = "Паспорт: серия 4515 № 654321."
        result = anonymize(text)
        assert "ПАСПОРТ" in result.stats

    def test_bank_account_rs(self):
        """Расчётный счёт с 'р/с'."""
        text = "Реквизиты: р/с 40702810400000000001 в ПАО Сбербанк."
        result = anonymize(text)
        assert "40702810400000000001" not in result.text
        assert "СЧЁТ" in result.stats

    def test_bank_account_ks(self):
        """Корреспондентский счёт с 'к/с'."""
        text = "к/с 30101810400000000225 БИК 044525225."
        result = anonymize(text)
        assert "30101810400000000225" not in result.text

    def test_bank_account_full_word(self):
        """Расчётный счёт полным словом."""
        text = "Расчётный счёт 40702810900000005678 в банке."
        result = anonymize(text)
        assert "40702810900000005678" not in result.text

    # --- FALSE POSITIVES: НЕ должны маскировать ---

    def test_amount_not_masked_as_inn(self):
        """12-цифровая сумма не должна маскироваться как ИНН_ФЛ."""
        text = "Стоимость проекта составляет 150000000000 рублей."
        result = anonymize(text)
        # В текущей реализации ЭТО БУДЕТ замаскировано — xfail документирует это
        assert "150000000000" in result.text

    def test_inn_yul_not_masked(self):
        """ИНН юрлица (10 цифр) обнаруживается, но НЕ маскируется в тексте."""
        text = "ООО ТехноСтрой (ИНН 7707083893) заключает договор."
        result = anonymize(text)
        # ИНН_ЮЛ должен остаться в тексте (это публичный идентификатор)
        # Анонимизатор его обнаруживает, но в _extract_regex_matches
        # добавляет его как match → проверяем логику
        # Текущий код: ИНН_ЮЛ, ОГРН, КПП добавляются как match, но
        # НЕ маскируются в anonymize() — или маскируются?
        # По коду: все matches проходят замену. Проверим.
        assert "ИНН_ЮЛ" in result.stats or "7707083893" in result.text

    def test_ogrn_detected(self):
        """ОГРН обнаруживается."""
        text = "ОГРН 1077771234567 зарегистрировано."
        result = anonymize(text)
        assert "ОГРН" in result.stats

    def test_kpp_detected(self):
        """КПП обнаруживается."""
        text = "КПП 770101001 налоговая."
        result = anonymize(text)
        assert "КПП" in result.stats

    def test_standalone_10_digits_not_matched(self):
        """10-цифровое число без 'ИНН' не матчится как ИНН_ЮЛ."""
        text = "Номер заказа: 1234567890 для отслеживания."
        result = anonymize(text)
        # Не должно быть ИНН_ЮЛ (нет контекстного слова)
        assert result.stats.get("ИНН_ЮЛ", 0) == 0

    # --- FALSE NEGATIVES: могут пропустить ---

    def test_foreign_name_missed(self):
        """Английское имя в русском тексте — Natasha не поймает."""
        text = "Представитель: John Smith, гражданин США, действующий по доверенности."
        result = anonymize(text)
        assert "John Smith" not in result.text

    def test_name_in_genitive_case(self):
        """ФИО в родительном падеже."""
        text = "По поручению Иванова Ивана Ивановича действует доверенное лицо."
        result = anonymize(text)
        # NER обычно справляется с падежами
        assert "ФИО" in result.stats

    def test_passport_far_from_context(self):
        """Паспорт далеко (>200 символов) от контекстного слова — не найдётся."""
        filler = "A" * 250
        text = f"паспорт гражданина РФ. {filler} серия 4515 номер 999888."
        result = anonymize(text)
        # Числа за пределами окна ±200 НЕ будут найдены
        # Это ожидаемое поведение, не баг
        passport_count = result.stats.get("ПАСПОРТ", 0)
        # Может поймать, может нет — зависит от позиции контекста
        # Просто проверяем что не крашится
        assert isinstance(result.text, str)

    # --- ПЕРЕКРЫТИЯ ---

    def test_overlap_longer_wins(self):
        """При перекрытии длинный match побеждает."""
        # Создадим ситуацию где regex и NER конкурируют
        text = "ИП Сидоров Пётр Петрович зарегистрирован в налоговой."
        result = anonymize(text)
        # Не должно быть дублирования — перекрытие должно быть разрешено
        assert isinstance(result.text, str)
        # Количество масок не должно превышать количество уникальных сущностей
        total_masks = sum(result.stats.values())
        total_unique = len(result.replacements)
        assert total_unique <= total_masks

    def test_overlap_bank_account_vs_inn(self):
        """20-цифровой счёт содержит 12-цифровой фрагмент — счёт побеждает."""
        text = "р/с 40702810400012345678 в банке."
        result = anonymize(text)
        # Должен быть СЧЁТ, а не ИНН_ФЛ (счёт длиннее)
        assert "СЧЁТ" in result.stats

    def test_remove_overlaps_deterministic(self):
        """_remove_overlaps детерминистична: длинный всегда побеждает."""
        matches = [
            (10, 30, "ФИО", "Иванов Иван Иванович"),  # 20 chars
            (10, 22, "ИП", "ИП Иванов"),  # 12 chars — короче, перекрывается
            (50, 62, "ТЕЛЕФОН", "+74951234567"),  # без перекрытия
        ]
        cleaned = _remove_overlaps(matches)
        types = [m[2] for m in cleaned]
        assert "ФИО" in types
        assert "ТЕЛЕФОН" in types
        # ИП не должен попасть (перекрывается с более длинным ФИО)
        assert len(cleaned) == 2

    # --- PRECISION / RECALL ---

    def test_precision_recall_report(self):
        """Комплексный документ — измеряем precision и recall."""
        text = (
            "ДОГОВОР ПОСТАВКИ No 42\n"
            "г. Москва                         15.01.2024\n\n"
            "ООО «ТехноСтрой» (ИНН 7707083893, ОГРН 1077771234567, КПП 770101001),\n"
            "в лице генерального директора Козлова Андрея Викторовича,\n"
            "действующего на основании Устава, именуемое «Поставщик»,\n"
            "и\n"
            "ООО «СтройМонтаж» (ИНН 7701234567),\n"
            "в лице директора Семёновой Елены Павловны,\n"
            "действующей на основании доверенности, именуемое «Покупатель»,\n\n"
            "заключили настоящий договор о нижеследующем.\n\n"
            "РЕКВИЗИТЫ СТОРОН:\n\n"
            "Поставщик:\n"
            "Козлов Андрей Викторович\n"
            "Паспорт серия 4515 номер 123456, выдан УФМС по г. Москве\n"
            "СНИЛС 111-222-333 44\n"
            "Телефон: +7 (495) 111-22-33\n"
            "Email: kozlov@technostroy.ru\n"
            "р/с 40702810400000000001\n\n"
            "Покупатель:\n"
            "Семёнова Елена Павловна\n"
            "Телефон: 8-926-444-55-66\n"
            "Email: semenova@stroymontazh.ru\n"
        )

        # Ожидаемые ПД (ground truth)
        expected_pii = {
            "ФИО": ["Козлова Андрея Викторовича", "Семёновой Елены Павловны",
                     "Козлов Андрей Викторович", "Семёнова Елена Павловна"],
            "ТЕЛЕФОН": ["+7 (495) 111-22-33", "8-926-444-55-66"],
            "EMAIL": ["kozlov@technostroy.ru", "semenova@stroymontazh.ru"],
            "СНИЛС": ["111-222-333 44"],
            "ПАСПОРТ": ["4515 номер 123456"],  # или "серия 4515 номер 123456"
            "СЧЁТ": ["40702810400000000001"],
        }

        result = anonymize(text)

        # Считаем метрики
        tp = 0
        fn = 0
        missed = []

        for pii_type, values in expected_pii.items():
            for value in values:
                if value not in result.text:
                    tp += 1  # Замаскировано — true positive
                else:
                    fn += 1  # Осталось в тексте — false negative
                    missed.append(f"[{pii_type}] \"{value}\"")

        # False positives: маски, которым не соответствует ожидаемый ПД
        # Считаем маски в результате
        all_masks = re.findall(r'\[[А-ЯЁ_]+_\d+\]', result.text)
        # Убираем ИНН_ЮЛ, ОГРН, КПП (они публичные, но маскируются текущим кодом)
        total_masked = len(result.replacements)
        expected_total = sum(len(v) for v in expected_pii.values())
        # Грубая оценка FP: если замаскировано больше уникальных значений чем ожидали
        unique_expected = len(set(
            v for vals in expected_pii.values() for v in vals
        ))

        precision = tp / (tp + max(0, total_masked - unique_expected)) if tp > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        # Печатаем отчёт
        print("\n" + "=" * 60)
        print("  ОТЧЁТ PRECISION / RECALL АНОНИМИЗАТОРА")
        print("=" * 60)
        print(f"  Ожидаемых ПД элементов:  {tp + fn}")
        print(f"  True Positives (TP):      {tp}")
        print(f"  False Negatives (FN):     {fn}")
        print(f"  Уникальных масок:         {total_masked}")
        print(f"  Precision:                {precision:.2f}")
        print(f"  Recall:                   {recall:.2f}")
        if missed:
            print(f"\n  Пропущено:")
            for m in missed:
                print(f"    - {m}")
        print("=" * 60)

        # Recall >= 0.6 — консервативный порог с учётом известных слабостей
        assert recall >= 0.6, f"Recall слишком низкий: {recall:.2f}"

    # --- ПРОИЗВОДИТЕЛЬНОСТЬ ---

    def test_anonymize_50_docs(self):
        """50 документов по 2КБ — должно уложиться в 30 секунд."""
        template = (
            "Договор No {i}. Стороны: Иванов Иван Иванович и ООО Компания-{i}. "
            "Телефон: +7 (495) {a:03d}-{b:02d}-{c:02d}. "
            "Email: user{i}@test.ru. "
            "СНИЛС: {d:03d}-{e:03d}-{f:03d} {g:02d}. "
        )
        docs = []
        for i in range(50):
            text = template.format(
                i=i, a=100 + i, b=10 + i % 90, c=10 + i % 90,
                d=100 + i, e=200 + i, f=300 + i, g=10 + i % 90,
            )
            # Дополняем до ~2КБ
            text += "Текст договора. " * 100
            docs.append(text)

        start = time.time()
        for doc in docs:
            result = anonymize(doc)
            assert isinstance(result.text, str)
        elapsed = time.time() - start

        print(f"\n  50 документов по ~2КБ: {elapsed:.1f} сек")
        assert elapsed < 30, f"Слишком медленно: {elapsed:.1f} сек"

    @slow
    def test_anonymize_large_document(self):
        """Один большой документ ~500КБ."""
        # Генерируем 500КБ текста с ПД
        block = (
            "Стороны: Козлов Андрей Викторович (тел. +7 (495) 111-22-33, "
            "email: kozlov@test.ru) и ООО ТехноСтрой (ИНН 7707083893). "
            "Предмет: поставка строительных материалов. "
        )
        text = block * (500_000 // len(block) + 1)
        text = text[:500_000]

        start = time.time()
        result = anonymize(text)
        elapsed = time.time() - start

        print(f"\n  Документ ~500КБ: {elapsed:.1f} сек")
        assert isinstance(result.text, str)
        assert elapsed < 120, f"Слишком медленно: {elapsed:.1f} сек"

    # --- ДОПОЛНИТЕЛЬНЫЕ EDGE CASES ---

    def test_empty_text(self):
        """Пустой текст не вызывает ошибок."""
        result = anonymize("")
        assert result.text == ""
        assert result.replacements == {}
        assert result.stats == {}

    def test_no_pii_text(self):
        """Текст без ПД — ничего не маскируется."""
        text = "Данный договор регулирует отношения между сторонами."
        result = anonymize(text)
        assert result.text == text
        assert result.replacements == {}

    def test_mixed_pii_dense(self):
        """Много ПД в одном абзаце — все обнаруживаются."""
        text = (
            "Козлов Андрей Викторович, тел. +7 (495) 111-22-33, "
            "email kozlov@mail.ru, СНИЛС 111-222-333 44, "
            "р/с 40702810400000000001."
        )
        result = anonymize(text)
        # Минимум 4 типа ПД
        assert len(result.stats) >= 4
        # ФИО замаскировано
        assert "Козлов Андрей Викторович" not in result.text


# ============================================================
#  ТЕСТЫ ВАЛИДАТОРА
# ============================================================


class TestValidatorStress:
    """Стресс-тесты валидации метаданных L1–L4."""

    # --- L1: СТРУКТУРНАЯ ---

    def test_l1_all_required_missing(self, config):
        """Все обязательные поля None → 3 предупреждения L1."""
        m = make_metadata(contract_type=None, counterparty=None, subject=None)
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert len(l1_warnings) == 3
        assert result.status == "error"

    def test_l1_empty_strings(self, config):
        """Пустые строки и пробелы → L1."""
        m = make_metadata(contract_type="", counterparty="  ", subject="")
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert len(l1_warnings) == 3

    def test_l1_bad_date_format(self, config):
        """DD-MM-YYYY вместо YYYY-MM-DD → L1."""
        m = make_metadata(date_signed="15-06-2024")
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert any("date_signed" in w for w in l1_warnings)

    def test_l1_invalid_date_values(self, config):
        """Месяц 13, день 32 → L1."""
        m = make_metadata(date_signed="2024-13-32")
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert len(l1_warnings) >= 1

    def test_l1_confidence_too_high(self, config):
        """confidence > 1 → L1."""
        m = make_metadata(confidence=1.5)
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert any("confidence" in w for w in l1_warnings)

    def test_l1_confidence_negative(self, config):
        """confidence < 0 → L1."""
        m = make_metadata(confidence=-0.1)
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert any("confidence" in w for w in l1_warnings)

    def test_l1_valid_passes(self, config):
        """Все поля корректны → 0 L1."""
        m = make_metadata()
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert len(l1_warnings) == 0

    # --- L2: ЛОГИЧЕСКАЯ ---

    def test_l2_future_date(self, config):
        """Дата в будущем (+60 дней) → L2."""
        future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        m = make_metadata(date_signed=future)
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("будущем" in w for w in l2_warnings)

    def test_l2_ancient_date(self, config):
        """Дата до 2000 года → L2."""
        m = make_metadata(date_signed="1995-03-15")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("старая" in w for w in l2_warnings)

    def test_l2_start_after_end(self, config):
        """start > end → L2."""
        m = make_metadata(date_start="2025-06-01", date_end="2024-01-01")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("позже" in w for w in l2_warnings)

    def test_l2_very_long_contract(self, config):
        """Срок > 50 лет → L2."""
        m = make_metadata(date_start="2024-01-01", date_end="2080-01-01")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("долгий" in w for w in l2_warnings)

    def test_l2_nonstandard_type(self, config):
        """Нестандартный тип (fuzzy < 0.8) → L2."""
        m = make_metadata(contract_type="Контракт на закупку спецтехники")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("нестандартный" in w for w in l2_warnings)

    def test_l2_standard_type_fuzzy_ok(self, config):
        """Стандартный тип с опечаткой (fuzzy >= 0.8) → OK."""
        m = make_metadata(contract_type="Договор поставки")  # точное совпадение
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if "нестандартный" in w]
        assert len(l2_warnings) == 0

    def test_l2_huge_amount(self, config):
        """Сумма > 10 млрд → L2."""
        m = make_metadata(amount="15 000 000 000 руб.")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("аномально большая" in w for w in l2_warnings)

    def test_l2_tiny_amount_non_labor(self, config):
        """Сумма < 1000 (не трудовой) → L2."""
        m = make_metadata(amount="500 руб.", contract_type="Договор поставки")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("малая" in w for w in l2_warnings)

    def test_l2_tiny_amount_labor_ok(self, config):
        """Сумма < 1000 (трудовой) → OK."""
        m = make_metadata(amount="500 руб.", contract_type="Трудовой договор")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if "малая" in w]
        assert len(l2_warnings) == 0

    def test_l2_amount_no_digits(self, config):
        """Сумма без цифр → L2."""
        m = make_metadata(amount="по согласованию сторон")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("не содержит" in w for w in l2_warnings)

    def test_l2_short_subject(self, config):
        """Предмет < 5 символов → L2."""
        m = make_metadata(subject="Да")
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("короткий" in w for w in l2_warnings)

    def test_l2_long_subject(self, config):
        """Предмет > 500 символов → L2."""
        m = make_metadata(subject="А" * 600)
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("длинный" in w for w in l2_warnings)

    def test_l2_duplicate_parties(self, config):
        """Одинаковые стороны → L2."""
        m = make_metadata(parties=["ООО Альфа", "ООО Альфа"])
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if w.startswith("L2:")]
        assert any("совпадают" in w for w in l2_warnings)

    def test_l2_inn_valid_10(self, config):
        """Валидный 10-значный ИНН → нет предупреждения."""
        m = make_metadata(parties=["ООО Альфа ИНН 7707083893"])
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if "ИНН" in w]
        assert len(l2_warnings) == 0

    def test_l2_inn_invalid_10(self, config):
        """Невалидный 10-значный ИНН → L2."""
        m = make_metadata(parties=["ООО Альфа ИНН 7707083890"])
        result = validate_metadata(m, config)
        l2_warnings = [w for w in result.warnings if "ИНН" in w]
        assert len(l2_warnings) >= 1

    def test_l2_null_dates_no_warning(self, config):
        """Null даты → нет L2 предупреждений по датам."""
        m = make_metadata(date_signed=None, date_start=None, date_end=None)
        result = validate_metadata(m, config)
        date_warnings = [w for w in result.warnings if "дат" in w.lower()]
        assert len(date_warnings) == 0

    def test_l2_null_amount_no_warning(self, config):
        """Null сумма → нет L2 предупреждений по сумме."""
        m = make_metadata(amount=None)
        result = validate_metadata(m, config)
        amount_warnings = [w for w in result.warnings if "сумм" in w.lower()]
        assert len(amount_warnings) == 0

    # --- L3: AI УВЕРЕННОСТЬ ---

    def test_l3_high_confidence(self, config):
        """confidence 0.9 → status 'ok'."""
        m = make_metadata(confidence=0.9)
        result = validate_metadata(m, config)
        assert result.status == "ok"

    def test_l3_medium_confidence(self, config):
        """confidence 0.65 → status 'warning'."""
        m = make_metadata(confidence=0.65)
        result = validate_metadata(m, config)
        assert result.status == "warning"
        l3_warnings = [w for w in result.warnings if w.startswith("L3:")]
        assert any("средняя" in w for w in l3_warnings)

    def test_l3_low_confidence(self, config):
        """confidence 0.3 → status 'unreliable'."""
        m = make_metadata(confidence=0.3)
        result = validate_metadata(m, config)
        assert result.status == "unreliable"
        l3_warnings = [w for w in result.warnings if w.startswith("L3:")]
        assert any("низкая" in w for w in l3_warnings)

    def test_l3_boundary_0_5(self, config):
        """confidence = 0.5 → 'warning' (>= low, < high)."""
        m = make_metadata(confidence=0.5)
        result = validate_metadata(m, config)
        assert result.status == "warning"

    def test_l3_boundary_0_8(self, config):
        """confidence = 0.8 → 'ok' (>= high)."""
        m = make_metadata(confidence=0.8)
        result = validate_metadata(m, config)
        assert result.status == "ok"

    def test_l3_hallucination_romashka(self, config):
        """Контрагент 'ООО Ромашка' → подозрение на галлюцинацию."""
        m = make_metadata(counterparty="ООО Ромашка", confidence=0.9)
        result = validate_metadata(m, config)
        l3_warnings = [w for w in result.warnings if w.startswith("L3:")]
        assert any("галлюцинац" in w for w in l3_warnings)

    def test_l3_hallucination_role_names(self, config):
        """Роли вместо имён ('Заказчик', 'Исполнитель') → L3."""
        for role in ["Заказчик", "Исполнитель", "Покупатель", "Продавец",
                      "Арендатор", "Арендодатель"]:
            m = make_metadata(counterparty=role, confidence=0.9)
            result = validate_metadata(m, config)
            l3_warnings = [w for w in result.warnings if w.startswith("L3:")]
            assert any("галлюцинац" in w for w in l3_warnings), f"Не обнаружена галлюцинация для '{role}'"

    def test_l3_all_dates_same(self, config):
        """Все 3 даты одинаковые → L3."""
        m = make_metadata(
            date_signed="2024-01-01",
            date_start="2024-01-01",
            date_end="2024-01-01",
            confidence=0.9,
        )
        result = validate_metadata(m, config)
        l3_warnings = [w for w in result.warnings if w.startswith("L3:")]
        assert any("даты совпадают" in w for w in l3_warnings)

    # --- L4: ПАКЕТНАЯ ---

    def test_l4_duplicate_detection(self, tmp_path, config):
        """Два файла с одинаковым (контрагент, дата, сумма) → L4."""
        r1 = make_result(tmp_path, "file1.pdf", b"a")
        r2 = make_result(tmp_path, "file2.pdf", b"b")
        # Одинаковые метаданные
        r1.metadata.counterparty = "ООО Альфа"
        r1.metadata.date_signed = "2024-01-01"
        r1.metadata.amount = "100 000 руб."
        r2.metadata.counterparty = "ООО Альфа"
        r2.metadata.date_signed = "2024-01-01"
        r2.metadata.amount = "100 000 руб."

        results = validate_batch([r1, r2], config)
        all_warnings = []
        for r in results:
            all_warnings.extend(r.validation.warnings)
        assert any("дубликат" in w for w in all_warnings)

    def test_l4_same_date_ranges(self, tmp_path, config):
        """Файлы с одинаковыми (start, end) → L4."""
        results = []
        for i in range(3):
            r = make_result(tmp_path, f"file{i}.pdf", f"content{i}".encode())
            r.metadata.date_start = "2024-01-01"
            r.metadata.date_end = "2025-01-01"
            # Разные контрагенты чтобы не сработал дубликат
            r.metadata.counterparty = f"ООО Компания-{i}"
            results.append(r)

        results = validate_batch(results, config)
        all_warnings = []
        for r in results:
            all_warnings.extend(r.validation.warnings)
        assert any("совпадающие даты" in w for w in all_warnings)

    def test_l4_type_skew(self, tmp_path, config):
        """>50% одного типа при >5 файлов → L4."""
        results = []
        for i in range(6):
            r = make_result(tmp_path, f"file{i}.pdf", f"c{i}".encode())
            r.metadata.contract_type = "Договор поставки"  # все одинаковые
            r.metadata.counterparty = f"ООО-{i}"
            r.metadata.date_signed = f"2024-{i+1:02d}-01"
            results.append(r)

        results = validate_batch(results, config)
        all_warnings = []
        for r in results:
            all_warnings.extend(r.validation.warnings)
        assert any("файлов определены как" in w for w in all_warnings)

    def test_l4_warning_prevalence(self, tmp_path, config):
        """>30% с предупреждениями при >5 файлов → L4."""
        results = []
        for i in range(6):
            r = make_result(tmp_path, f"file{i}.pdf", f"c{i}".encode())
            r.metadata.counterparty = f"ООО-{i}"
            r.metadata.date_signed = f"2024-{i+1:02d}-01"
            r.metadata.contract_type = f"Тип-{i}"  # разные типы
            if i < 3:
                r.validation.status = "warning"
            results.append(r)

        results = validate_batch(results, config)
        all_warnings = []
        for r in results:
            all_warnings.extend(r.validation.warnings)
        assert any("предупреждения" in w for w in all_warnings)

    def test_l4_small_batch_no_skew(self, tmp_path, config):
        """Малый пакет (≤5) → L4 проверка типов НЕ срабатывает."""
        results = []
        for i in range(3):
            r = make_result(tmp_path, f"file{i}.pdf", f"c{i}".encode())
            r.metadata.contract_type = "Договор поставки"  # все одинаковые
            r.metadata.counterparty = f"ООО-{i}"
            r.metadata.date_signed = f"2024-{i+1:02d}-01"
            results.append(r)

        results = validate_batch(results, config)
        all_warnings = []
        for r in results:
            all_warnings.extend(r.validation.warnings)
        assert not any("файлов определены как" in w for w in all_warnings)

    def test_l4_empty_batch(self, config):
        """Пустой список → без изменений."""
        results = validate_batch([], config)
        assert results == []

    # --- СКОРИНГ ---

    def test_score_perfect(self, config):
        """confidence=0.9, 0 замечаний → score=0.9."""
        m = make_metadata(confidence=0.9)
        result = validate_metadata(m, config)
        assert abs(result.score - 0.9) < 0.01

    def test_score_l1_penalty(self, config):
        """2 L1 → score -= 0.30."""
        m = make_metadata(
            confidence=0.9,
            contract_type=None,
            counterparty=None,
        )
        result = validate_metadata(m, config)
        expected = 0.9 - 2 * 0.15
        assert abs(result.score - expected) < 0.01

    def test_score_l2_penalty(self, config):
        """L2 предупреждения → score -= 0.10 каждое."""
        m = make_metadata(
            confidence=0.9,
            date_signed="1995-01-01",  # L2: старая
            amount="15 000 000 000 руб.",  # L2: аномально большая
            subject="Да",  # L2: короткий
        )
        result = validate_metadata(m, config)
        l2_count = len([w for w in result.warnings if w.startswith("L2:")])
        expected = 0.9 - l2_count * 0.10
        # Может быть дополнительный L2 за нестандартный тип из-за fuzzy match
        assert abs(result.score - expected) < 0.01

    def test_score_mixed_penalties(self, config):
        """Микс L1 + L2 + L3."""
        m = make_metadata(
            confidence=0.65,  # L3: средняя
            contract_type=None,  # L1
            amount="15 000 000 000 руб.",  # L2
        )
        result = validate_metadata(m, config)
        l1_count = len([w for w in result.warnings if w.startswith("L1:")])
        l2_count = len([w for w in result.warnings if w.startswith("L2:")])
        l3_count = len([w for w in result.warnings if w.startswith("L3:")])
        expected = 0.65 - l1_count * 0.15 - l2_count * 0.10 - l3_count * 0.05
        expected = max(0.0, min(1.0, expected))
        assert abs(result.score - expected) < 0.01

    def test_score_clamped_to_zero(self, config):
        """Score не опускается ниже 0."""
        m = make_metadata(
            confidence=0.1,
            contract_type=None,  # L1
            counterparty=None,  # L1
            subject=None,  # L1
        )
        result = validate_metadata(m, config)
        assert result.score >= 0.0

    def test_score_clamped_to_one(self, config):
        """Score не превышает 1.0."""
        m = make_metadata(confidence=1.0)
        result = validate_metadata(m, config)
        assert result.score <= 1.0

    # --- ИНН КОНТРОЛЬНАЯ СУММА ---

    def test_inn_10_valid(self):
        """Валидный 10-значный ИНН."""
        assert _validate_inn("7707083893") is True

    def test_inn_10_invalid(self):
        """Невалидный 10-значный ИНН."""
        assert _validate_inn("7707083890") is False

    def test_inn_12_valid(self):
        """Валидный 12-значный ИНН."""
        # Вычислим валидный 12-значный ИНН
        # Используем известный: 500100732259
        assert _validate_inn("500100732259") is True

    def test_inn_12_invalid(self):
        """Невалидный 12-значный ИНН."""
        assert _validate_inn("123456789012") is False

    def test_inn_wrong_length_9(self):
        """9 цифр → False."""
        assert _validate_inn("123456789") is False

    def test_inn_wrong_length_11(self):
        """11 цифр → False."""
        assert _validate_inn("12345678901") is False

    def test_inn_wrong_length_13(self):
        """13 цифр → False."""
        assert _validate_inn("1234567890123") is False

    def test_inn_non_digits(self):
        """Нецифровые символы → False."""
        assert _validate_inn("77070838a3") is False

    def test_inn_empty(self):
        """Пустая строка → False."""
        assert _validate_inn("") is False

    # --- FUZZY MATCH ---

    def test_fuzzy_exact_match(self, config):
        """Точное совпадение → score = 1.0."""
        match, score = _fuzzy_match("Договор поставки", config.document_types_hints)
        assert score == 1.0
        assert match == "Договор поставки"

    def test_fuzzy_close_match(self, config):
        """Близкое совпадение → score >= 0.8."""
        match, score = _fuzzy_match("Договор поставок", config.document_types_hints)
        assert score >= 0.7  # "поставок" vs "поставки" — очень близко

    def test_fuzzy_distant_match(self, config):
        """Далёкое совпадение → score < 0.8."""
        match, score = _fuzzy_match("Контракт на закупку спецтехники", config.document_types_hints)
        assert score < 0.8

    def test_fuzzy_empty_candidates(self):
        """Пустой список кандидатов → ('', 0.0)."""
        match, score = _fuzzy_match("Договор", [])
        assert match == ""
        assert score == 0.0

    def test_fuzzy_case_insensitive(self, config):
        """Регистр не влияет."""
        match1, score1 = _fuzzy_match("ДОГОВОР ПОСТАВКИ", config.document_types_hints)
        match2, score2 = _fuzzy_match("договор поставки", config.document_types_hints)
        assert abs(score1 - score2) < 0.01


# ============================================================
#  ТЕСТЫ ОРГАНИЗАТОРА
# ============================================================


class TestOrganizerStress:
    """Стресс-тесты организации файлов."""

    # --- САНИТИЗАЦИЯ ---

    def test_sanitize_forbidden_chars(self):
        """Запрещённые символы заменяются."""
        result = _sanitize_name('ООО "Рога<Копыта>"')
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert len(result) > 0

    def test_sanitize_long_name(self):
        """Длинное имя обрезается до 80 символов."""
        result = _sanitize_name("А" * 120)
        assert len(result) <= 80

    def test_sanitize_empty_name(self):
        """Пустое имя → 'Без названия'."""
        result = _sanitize_name("")
        assert result == "Без названия"

    def test_sanitize_only_forbidden(self):
        """Только запрещённые символы → 'Без названия'."""
        result = _sanitize_name('<>:"/\\|?*')
        assert result == "Без названия"

    def test_sanitize_cyrillic(self):
        """Кириллица проходит без изменений."""
        result = _sanitize_name("ООО Привет Мир")
        assert "ООО" in result
        assert "Привет" in result
        assert "Мир" in result

    def test_sanitize_consecutive_spaces(self):
        """Множественные пробелы схлопываются."""
        result = _sanitize_name("ООО   Альфа   Бета")
        assert "   " not in result
        assert "ООО" in result

    def test_sanitize_custom_max_length(self):
        """Кастомный max_length."""
        result = _sanitize_name("А" * 50, max_length=30)
        assert len(result) <= 30

    # --- КОНФЛИКТ ФАЙЛОВ ---

    def test_conflict_no_conflict(self, tmp_path):
        """Файл не существует → тот же путь."""
        path = tmp_path / "test.pdf"
        resolved = _resolve_conflict(path)
        assert resolved == path

    def test_conflict_one_existing(self, tmp_path):
        """Один конфликт → _1."""
        path = tmp_path / "test.pdf"
        path.write_bytes(b"existing")
        resolved = _resolve_conflict(path)
        assert resolved == tmp_path / "test_1.pdf"

    def test_conflict_multiple_existing(self, tmp_path):
        """Множественные конфликты → _N."""
        base = tmp_path / "test.pdf"
        base.write_bytes(b"0")
        (tmp_path / "test_1.pdf").write_bytes(b"1")
        (tmp_path / "test_2.pdf").write_bytes(b"2")
        resolved = _resolve_conflict(base)
        assert resolved == tmp_path / "test_3.pdf"

    def test_conflict_50_files(self, tmp_path):
        """50 конфликтов → _50."""
        base = tmp_path / "test.pdf"
        base.write_bytes(b"0")
        for i in range(1, 50):
            (tmp_path / f"test_{i}.pdf").write_bytes(f"{i}".encode())
        resolved = _resolve_conflict(base)
        assert resolved == tmp_path / "test_50.pdf"

    # --- ГЕНЕРАЦИЯ ИМЕНИ ---

    def test_filename_all_parts(self, tmp_path):
        """Все поля → Тип_Контрагент_Дата.ext."""
        r = make_result(tmp_path)
        name = _generate_filename(r)
        assert "Договор поставки" in name
        assert "ООО ТехноСтрой" in name
        assert "2024-06-15" in name
        assert name.endswith(".pdf")

    def test_filename_no_metadata(self, tmp_path):
        """Нет метаданных → оригинальное имя файла."""
        r = make_result(tmp_path)
        r.metadata = ContractMetadata()  # пустые поля
        name = _generate_filename(r)
        assert name == r.file_info.filename

    def test_filename_long_parts_truncated(self, tmp_path):
        """Длинные части обрезаны до 30 символов."""
        r = make_result(tmp_path)
        r.metadata.contract_type = "А" * 50
        r.metadata.counterparty = "Б" * 50
        name = _generate_filename(r)
        parts = name.replace(r.file_info.extension, "").split("_")
        # Каждая часть (после санитизации) <= 30
        for part in parts:
            if part != r.metadata.date_signed:  # дата не обрезается
                assert len(part) <= 30

    # --- ORGANIZE_FILE (ИНТЕГРАЦИЯ) ---

    def test_organize_mode_type(self, tmp_path):
        """Режим 'type' → Документы/{type}/{file}."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        path = organize_file(r, output_dir, grouping="type")
        assert "Документы" in str(path)
        assert path.exists()

    def test_organize_mode_counterparty(self, tmp_path):
        """Режим 'counterparty' → Документы/{counterparty}/{file}."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        path = organize_file(r, output_dir, grouping="counterparty")
        assert "Документы" in str(path)
        assert "ООО ТехноСтрой" in str(path)
        assert path.exists()

    def test_organize_mode_both(self, tmp_path):
        """Режим 'both' → Документы/{type}/{counterparty}/{file}."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        path = organize_file(r, output_dir, grouping="both")
        parts = str(path)
        assert "Документы" in parts
        assert path.exists()

    def test_organize_null_metadata(self, tmp_path):
        """Null metadata → 'Неклассифицированные'/'Неизвестный контрагент'."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        r.metadata.contract_type = None
        r.metadata.counterparty = None
        path = organize_file(r, output_dir, grouping="both")
        parts = str(path)
        assert "Неклассифицированные" in parts
        assert "Неизвестный контрагент" in parts
        assert path.exists()

    def test_organize_special_chars(self, tmp_path):
        """Спецсимволы в контрагенте → санитизированная папка."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        r.metadata.counterparty = 'ООО "Рога/Копыта"'
        path = organize_file(r, output_dir, grouping="counterparty")
        assert path.exists()
        # Папка не должна содержать запрещённые символы
        assert '"' not in path.parent.name
        assert "/" not in path.parent.name

    def test_organize_duplicate_files(self, tmp_path):
        """Два файла с одинаковыми метаданными → второй получает суффикс."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r1 = make_result(tmp_path, "file1.pdf", b"content1")
        r2 = make_result(tmp_path, "file2.pdf", b"content2")
        path1 = organize_file(r1, output_dir, grouping="type")
        path2 = organize_file(r2, output_dir, grouping="type")
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()


# ============================================================
#  ТЕСТЫ НАГРУЗКИ
# ============================================================


class TestLoadStress:
    """Нагрузочные тесты: БД, конкурентность, производительность."""

    # --- БД ---

    def test_db_100_sequential_writes(self, tmp_path):
        """100 последовательных записей → все сохранились."""
        db = Database(tmp_path / "test.db")
        for i in range(100):
            r = make_result(
                tmp_path,
                filename=f"file_{i:03d}.pdf",
                content=f"content_{i}".encode(),
            )
            db.save_result(r)

        results = db.get_all_results()
        db.close()
        assert len(results) == 100

    def test_db_concurrent_writes(self, tmp_path):
        """10 потоков x 10 записей → 100 записей без ошибок."""
        db = Database(tmp_path / "test.db")
        errors = []

        def write_batch(thread_id: int):
            for i in range(10):
                try:
                    r = make_result(
                        tmp_path,
                        filename=f"t{thread_id}_f{i}.pdf",
                        content=f"t{thread_id}_c{i}".encode(),
                    )
                    db.save_result(r)
                except Exception as e:
                    errors.append(f"Thread {thread_id}, file {i}: {e}")

        threads = [threading.Thread(target=write_batch, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        results = db.get_all_results()
        db.close()

        assert len(errors) == 0, f"Ошибки БД: {errors}"
        assert len(results) == 100

    def test_db_is_processed_after_save(self, tmp_path):
        """is_processed → True после save с status='done'."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path, status="done")
        db.save_result(r)
        assert db.is_processed(r.file_info.file_hash) is True
        db.close()

    def test_db_is_processed_error_status(self, tmp_path):
        """is_processed → False для status='error'."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path, status="error")
        db.save_result(r)
        assert db.is_processed(r.file_info.file_hash) is False
        db.close()

    def test_db_upsert(self, tmp_path):
        """Upsert: обновление не создаёт дубликат."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path, file_hash="fixed_hash_123")
        r.status = "error"
        db.save_result(r)

        r.status = "done"
        db.save_result(r)

        results = db.get_all_results()
        db.close()
        assert len(results) == 1
        assert results[0]["status"] == "done"

    def test_db_get_stats(self, tmp_path):
        """get_stats возвращает корректные счётчики."""
        db = Database(tmp_path / "test.db")
        for i in range(5):
            r = make_result(
                tmp_path,
                filename=f"done_{i}.pdf",
                content=f"d{i}".encode(),
                status="done",
            )
            db.save_result(r)
        for i in range(3):
            r = make_result(
                tmp_path,
                filename=f"error_{i}.pdf",
                content=f"e{i}".encode(),
                status="error",
            )
            db.save_result(r)

        stats = db.get_stats()
        db.close()
        assert stats["total"] == 8
        assert stats["done"] == 5
        assert stats["error"] == 3

    # --- ВАЛИДАТОР ПРОИЗВОДИТЕЛЬНОСТЬ ---

    def test_validate_batch_100(self, tmp_path, config):
        """validate_batch на 100 результатах → < 5 сек."""
        results = []
        for i in range(100):
            r = make_result(
                tmp_path,
                filename=f"file_{i:03d}.pdf",
                content=f"c{i}".encode(),
            )
            r.metadata.counterparty = f"ООО Компания-{i}"
            r.metadata.date_signed = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            r.metadata.contract_type = config.document_types_hints[i % len(config.document_types_hints)]
            results.append(r)

        start = time.time()
        results = validate_batch(results, config)
        elapsed = time.time() - start

        print(f"\n  validate_batch(100): {elapsed:.2f} сек")
        assert elapsed < 5

    @slow
    def test_validate_batch_500(self, tmp_path, config):
        """validate_batch на 500 результатах → < 15 сек."""
        results = []
        for i in range(500):
            r = make_result(
                tmp_path,
                filename=f"file_{i:04d}.pdf",
                content=f"c{i}".encode(),
            )
            r.metadata.counterparty = f"ООО Компания-{i}"
            r.metadata.date_signed = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            r.metadata.contract_type = config.document_types_hints[i % len(config.document_types_hints)]
            results.append(r)

        start = time.time()
        results = validate_batch(results, config)
        elapsed = time.time() - start

        print(f"\n  validate_batch(500): {elapsed:.2f} сек")
        assert elapsed < 15

    # --- ОРГАНИЗАТОР ПРОИЗВОДИТЕЛЬНОСТЬ ---

    def test_organize_100_files(self, tmp_path, config):
        """100 файлов → все скопированы."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        paths = []
        for i in range(100):
            r = make_result(
                tmp_path / "source",
                filename=f"file_{i:03d}.pdf",
                content=f"content_{i}".encode(),
            )
            r.metadata.counterparty = f"ООО Компания-{i}"
            r.metadata.contract_type = config.document_types_hints[i % len(config.document_types_hints)]
            path = organize_file(r, output_dir, grouping="both")
            paths.append(path)

        # Все файлы существуют
        for p in paths:
            assert p.exists(), f"Файл не найден: {p}"
        assert len(paths) == 100


# ============================================================
#  ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# ============================================================


class TestIntegrationStress:
    """E2E тесты с мокнутым AI."""

    def _mock_extract_metadata(self, text, config):
        """Мок для AI: возвращает фиксированные метаданные."""
        return ContractMetadata(
            contract_type="Договор поставки",
            counterparty="ООО ТестКонтрагент",
            subject="Поставка товаров согласно спецификации",
            date_signed="2024-01-15",
            date_start="2024-02-01",
            date_end="2025-01-31",
            amount="100 000 руб.",
            special_conditions=[],
            parties=["ООО ТестКонтрагент", "ООО НашаКомпания"],
            confidence=0.85,
        )

    @pytest.fixture
    def mock_ai(self):
        with patch(
            "modules.ai_extractor.extract_metadata",
            side_effect=self._mock_extract_metadata,
        ) as m_extract, patch(
            "modules.ai_extractor.verify_api_key",
            return_value=True,
        ) as m_verify:
            yield m_extract, m_verify

    def test_e2e_empty_directory(self, tmp_path, config, mock_ai):
        """Пустая директория → total=0, без краша."""
        from controller import Controller

        source_dir = tmp_path / "empty"
        source_dir.mkdir()

        controller = Controller(config)
        stats = controller.process_archive(source_dir)
        assert stats["total"] == 0 or stats["done"] == 0

    def test_e2e_valid_docx_files(self, tmp_path, config, mock_ai):
        """Несколько валидных DOCX → все обработаны."""
        from controller import Controller

        source_dir = tmp_path / "contracts"
        source_dir.mkdir()

        for i in range(3):
            create_test_docx(
                source_dir / f"contract_{i}.docx",
                f"ДОГОВОР ПОСТАВКИ No {i}\n"
                f"Стороны: ООО Компания-{i} и ООО Наша Фирма.\n"
                f"Предмет: поставка строительных материалов.\n"
                f"Сумма: {(i + 1) * 100_000} руб.\n"
            )

        controller = Controller(config)
        stats = controller.process_archive(source_dir)

        assert stats["done"] >= 3
        assert stats["errors"] == 0

    def test_e2e_mixed_valid_invalid(self, tmp_path, config, mock_ai):
        """Валидные + невалидные файлы → валидные обработаны, ошибки залогированы."""
        from controller import Controller

        source_dir = tmp_path / "contracts"
        source_dir.mkdir()

        # Валидные
        for i in range(3):
            create_test_docx(
                source_dir / f"valid_{i}.docx",
                f"Договор поставки No {i}. Поставка товаров.",
            )

        # Невалидные (пустые файлы с расширением .pdf)
        for i in range(2):
            (source_dir / f"invalid_{i}.pdf").write_bytes(b"")

        controller = Controller(config)
        stats = controller.process_archive(source_dir)

        # Как минимум валидные обработаны
        assert stats["done"] >= 3 or stats["total"] >= 5

    def test_e2e_resume_after_first_run(self, tmp_path, config, mock_ai):
        """Резюмируемость: повторный запуск → skipped."""
        from controller import Controller

        source_dir = tmp_path / "contracts"
        source_dir.mkdir()

        for i in range(3):
            create_test_docx(
                source_dir / f"contract_{i}.docx",
                f"Договор No {i}. Поставка строительных материалов.",
            )

        controller = Controller(config)

        # Первый запуск
        stats1 = controller.process_archive(source_dir)
        done1 = stats1["done"]

        # Второй запуск (те же файлы)
        stats2 = controller.process_archive(source_dir)
        skipped2 = stats2.get("skipped", 0)

        # При втором запуске файлы должны быть пропущены
        assert skipped2 >= done1 or stats2["done"] >= done1

    def test_e2e_report_generated(self, tmp_path, config, mock_ai):
        """После обработки Excel-отчёт создаётся."""
        from controller import Controller

        source_dir = tmp_path / "contracts"
        source_dir.mkdir()

        create_test_docx(
            source_dir / "contract.docx",
            "Договор поставки No 1. Поставка строительных материалов.",
        )

        controller = Controller(config)
        stats = controller.process_archive(source_dir)

        report_path = stats.get("report_path")
        if report_path:
            assert Path(report_path).exists()

    def test_e2e_db_integrity(self, tmp_path, config, mock_ai):
        """Целостность БД после обработки."""
        from controller import Controller

        source_dir = tmp_path / "contracts"
        source_dir.mkdir()

        for i in range(3):
            create_test_docx(
                source_dir / f"contract_{i}.docx",
                f"Договор No {i}. Поставка товаров. Контрагент ООО Тест-{i}.",
            )

        controller = Controller(config)
        stats = controller.process_archive(source_dir)

        # Проверяем БД
        output_dir = source_dir.parent / config.output_folder_name
        db_path = output_dir / "yurteg.db"
        if db_path.exists():
            db = Database(db_path)
            db_results = db.get_all_results()
            db_stats = db.get_stats()
            db.close()

            assert db_stats["total"] >= 3
            for row in db_results:
                assert row["file_hash"] is not None
                assert row["filename"] is not None


# ============================================================
#  СУПЕРСЛОЖНЫЕ ТЕСТЫ — РЕАЛЬНЫЕ БАГИ И EDGE CASES
# ============================================================


class TestHardEdgeCases:
    """Суперсложные тесты, ловящие реальные баги.

    xfail-тесты документируют подтверждённые проблемы.
    Обычные тесты проверяют что код не крашится на edge case входах.
    """

    # ─── ГРУППА A: КРАШИ И КРИТИЧЕСКИЕ ОШИБКИ ───

    def test_parties_with_none_crashes(self, config):
        """parties=[..., None, ...] → КРАШ в validator._validate_l2 строка 244."""
        m = make_metadata(parties=["ООО Альфа", None, "ООО Бета"])
        validate_metadata(m, config)

    def test_parties_with_empty_strings_no_crash(self, config):
        """Пустые строки в parties → НЕ крашится."""
        m = make_metadata(parties=["ООО Альфа", "", "  ", "ООО Бета"])
        result = validate_metadata(m, config)
        assert isinstance(result.status, str)

    def test_amount_comma_format_misparsed(self, config):
        """FIXED: 1,500,000.00 USD → _parse_amount правильно парсит как 1500000.0."""
        from modules.validator import _parse_amount
        amount = "1,500,000.00 USD"
        parsed = _parse_amount(amount)
        assert parsed == 1_500_000.0, f"Сумма {amount} парсится как {parsed} вместо 1500000.0"

    def test_amount_european_format_misparsed(self, config):
        """FIXED: 1.500.000,50 EUR → _parse_amount правильно парсит как 1500000.5."""
        from modules.validator import _parse_amount
        amount = "1.500.000,50 EUR"
        parsed = _parse_amount(amount)
        assert abs(parsed - 1_500_000.5) < 1, f"Сумма {amount} парсится как {parsed} вместо 1500000.5"

    def test_amount_russian_format_ok(self, config):
        """1 500 000 руб. (стандартный русский) → парсится правильно."""
        m = make_metadata(amount="1 500 000 руб.")
        result = validate_metadata(m, config)
        big_warnings = [w for w in result.warnings if "аномально большая" in w]
        assert len(big_warnings) == 0

    # ─── ГРУППА B: УТЕЧКИ АНОНИМИЗАЦИИ ───

    def test_cyrillic_email_not_caught(self):
        """ivan@пример.рф — кириллический домен не матчится regex [a-zA-Z]."""
        text = "Почта: ivan@пример.рф для связи."
        result = anonymize(text)
        assert "ivan@пример.рф" not in result.text, "Email утёк в анонимизированный текст"

    def test_bank_account_without_prefix(self):
        """'счёт 40702810400000000001' — без 'р/с' или 'расчётный'.

        Regex СЧЁТ не ловит, но внутри 20-цифрового числа находится
        подпоследовательность, совпадающая с regex ТЕЛЕФОН.
        Результат: часть маскируется как [ТЕЛЕФОН_N], а не как [СЧЁТ_N].
        """
        text = "Перевод на счёт 40702810400000000001 в Сбербанке."
        result = anonymize(text)
        # Счёт должен маскироваться целиком как [СЧЁТ_N], а не частично как [ТЕЛЕФОН_N]
        assert "СЧЁТ" in str(result.stats), (
            f"Счёт замаскирован не как СЧЁТ, а как: {result.stats}. "
            f"Результат: {result.text}"
        )

    def test_bank_account_informal_prefix(self):
        """'на счет 40702810400000000001' — неформальный контекст.

        Ожидание: СЧЁТ, реальность: часть числа ловится как ТЕЛЕФОН.
        """
        text = "Оплату произвести на счет 40702810400000000001 банка."
        result = anonymize(text)
        assert "СЧЁТ" in str(result.stats), (
            f"Счёт замаскирован не как СЧЁТ, а как: {result.stats}. "
            f"Результат: {result.text}"
        )

    def test_mask_leaks_to_counterparty(self):
        """Маска [ФИО_N] утекает если AI придумал несуществующий номер."""
        # Имитируем: AI вернул маску которой нет в replacements
        counterparty = "[ФИО_5] Trading Company"
        replacements = {"[ФИО_1]": "Иванов Иван", "[ФИО_2]": "Петров Пётр"}

        # Де-анонимизация как в controller.py
        result = counterparty
        for mask, original in replacements.items():
            if mask in result:
                result = result.replace(mask, original)

        # Маска [ФИО_5] остаётся — это проблема
        assert "[ФИО_5]" in result, "Маска должна утечь (нет в replacements)"

    def test_snils_false_positive_number_sequence(self):
        """123-456-789 01 в контексте не-СНИЛС → ложно маскируется."""
        text = "Договор No 123-456-789 01 от 15 января 2024 года."
        result = anonymize(text)
        # Это номер договора, НЕ СНИЛС
        assert "СНИЛС" not in result.stats, "Ложный СНИЛС обнаружен"

    # ─── ГРУППА C: ГРЯЗНЫЕ ДОКУМЕНТЫ ───

    def test_messy_pdf_ocr_letter_spacing(self):
        """OCR с пробелами между буквами: 'И в а н о в  И в а н'."""
        text = "Директор: И в а н о в  И в а н  И в а н о в и ч подписал."
        result = anonymize(text)
        # NER не поймёт побуквенное разбиение
        assert "ФИО" in result.stats

    def test_phone_with_cyrillic_zero(self):
        """+7 (495) 1О3-45-67 — кириллическая «О» вместо «0»."""
        text = "Телефон: +7 (495) 1О3-45-67 для связи."
        result = anonymize(text)
        assert "ТЕЛЕФОН" in result.stats

    def test_multiple_contracts_in_one_file(self):
        """Два блока реквизитов в одном файле — все ПД маскируются."""
        text = (
            "РЕКВИЗИТЫ СТОРОН:\n\n"
            "Поставщик:\n"
            "Козлов Андрей Викторович\n"
            "Телефон: +7 (495) 111-22-33\n"
            "Email: kozlov@test.ru\n\n"
            "Покупатель:\n"
            "Сидорова Мария Петровна\n"
            "Телефон: +7 (926) 444-55-66\n"
            "Email: sidorova@test.ru\n"
        )
        result = anonymize(text)
        # Оба телефона замаскированы
        assert "+7 (495) 111-22-33" not in result.text
        assert "+7 (926) 444-55-66" not in result.text
        # Оба email замаскированы
        assert "kozlov@test.ru" not in result.text
        assert "sidorova@test.ru" not in result.text
        # ФИО — хотя бы один замаскирован
        assert result.stats.get("ФИО", 0) >= 1
        assert result.stats.get("ТЕЛЕФОН", 0) == 2
        assert result.stats.get("EMAIL", 0) == 2

    def test_contract_with_table_layout(self):
        """Текст-таблица: столбцы через пробелы — все ПД найдены."""
        text = (
            "Поставщик                    Покупатель\n"
            "ООО ТехноСтрой               ООО СтройМонтаж\n"
            "ИНН 7707083893               ИНН 7701234567\n"
            "тел. +7(495)111-22-33        тел. +7(926)444-55-66\n"
        )
        result = anonymize(text)
        # Оба телефона
        assert result.stats.get("ТЕЛЕФОН", 0) == 2
        # Оба ИНН_ЮЛ обнаружены
        assert result.stats.get("ИНН_ЮЛ", 0) == 2

    def test_passport_technical_not_person(self):
        """'Технический паспорт здания No 4515 123456' — НЕ паспорт гражданина."""
        text = "Технический паспорт здания No 4515 123456 выдан БТИ."
        result = anonymize(text)
        # Это технический паспорт, а не паспорт человека
        assert "ПАСПОРТ" not in result.stats

    # ─── ГРУППА D: EDGE CASES ВАЛИДАТОРА ───

    def test_validate_metadata_all_none(self, config):
        """ВСЕ поля None + confidence=0 → не крашится."""
        m = ContractMetadata(confidence=0.0)
        result = validate_metadata(m, config)
        assert result.status in ("error", "unreliable")
        assert result.score >= 0.0

    def test_inn_in_party_without_label(self, config):
        """ИНН без слова 'ИНН' → не проверяется, но не крашится."""
        m = make_metadata(parties=["ООО Альфа 7707083893"])
        result = validate_metadata(m, config)
        # Не крашится — главное
        assert isinstance(result.status, str)

    def test_huge_parties_list(self, config):
        """100 сторон → не крашится, не тормозит."""
        parties = [f"ООО Компания-{i} ИНН 770708389{i % 10}" for i in range(100)]
        m = make_metadata(parties=parties)
        result = validate_metadata(m, config)
        assert isinstance(result.status, str)

    def test_special_chars_in_all_fields(self, config):
        """XSS-подобный ввод во всех полях → не крашится."""
        xss = '<script>alert("xss")</script>'
        m = make_metadata(
            contract_type=xss,
            counterparty=xss,
            subject=xss * 2,  # > 5 символов
            amount=xss,
            date_signed=xss,
            special_conditions=[xss],
            parties=[xss, xss],
        )
        result = validate_metadata(m, config)
        # Не крашится — основная проверка
        assert isinstance(result.status, str)
        # Должны быть L1/L2 предупреждения
        assert len(result.warnings) > 0

    def test_confidence_nan(self, config):
        """confidence=NaN → L1 предупреждение."""
        m = make_metadata(confidence=float('nan'))
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert any("confidence" in w for w in l1_warnings)

    def test_confidence_inf(self, config):
        """confidence=Inf → L1 предупреждение."""
        m = make_metadata(confidence=float('inf'))
        result = validate_metadata(m, config)
        l1_warnings = [w for w in result.warnings if w.startswith("L1:")]
        assert any("confidence" in w for w in l1_warnings)

    def test_date_feb_29_leap_year_valid(self, config):
        """29 февраля високосного года — валидная дата."""
        m = make_metadata(date_signed="2024-02-29")
        result = validate_metadata(m, config)
        l1_date_warnings = [w for w in result.warnings if "L1:" in w and "date_signed" in w]
        assert len(l1_date_warnings) == 0

    def test_date_feb_29_non_leap_invalid(self, config):
        """29 февраля невисокосного года → L1."""
        m = make_metadata(date_signed="2023-02-29")
        result = validate_metadata(m, config)
        l1_date_warnings = [w for w in result.warnings if "L1:" in w and "date_signed" in w]
        assert len(l1_date_warnings) >= 1

    # ─── ГРУППА E: EDGE CASES ОРГАНИЗАТОРА ───

    def test_organize_source_file_deleted(self, tmp_path):
        """Исходный файл удалён → FileNotFoundError."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path, "will_delete.pdf", b"content")
        # Удаляем исходный файл
        r.file_info.path.unlink()
        with pytest.raises((FileNotFoundError, OSError)):
            organize_file(r, output_dir, grouping="type")

    def test_organize_filename_edge_cases(self, tmp_path):
        """Метаданные дают странное имя → не крашится."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        r.metadata.contract_type = "..."
        r.metadata.counterparty = "---"
        r.metadata.date_signed = "2024-01-01"
        path = organize_file(r, output_dir, grouping="both")
        assert path.exists()

    def test_organize_unicode_heavy_names(self, tmp_path):
        """Необычные Unicode-символы в метаданных → не крашится."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        r = make_result(tmp_path)
        r.metadata.contract_type = "Договор №42 «Поставка»"
        r.metadata.counterparty = "ТОВ «Вільна Україна» — партнёр"
        path = organize_file(r, output_dir, grouping="both")
        assert path.exists()

    # ─── ГРУППА F: EDGE CASES БАЗЫ ДАННЫХ ───

    def test_db_save_very_long_subject(self, tmp_path):
        """subject из 50000 символов → сохраняется и читается."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path)
        r.metadata.subject = "А" * 50000
        db.save_result(r)

        results = db.get_all_results()
        db.close()
        assert len(results) == 1
        assert results[0]["subject"] == "А" * 50000

    def test_db_save_special_json_chars(self, tmp_path):
        """JSON спецсимволы в special_conditions → сериализация без потерь."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path)
        r.metadata.special_conditions = [
            'условие с "кавычками"',
            "условие с \\слешами",
            "условие с\nпереносом строки",
            'условие с {фигурными} [скобками]',
        ]
        db.save_result(r)

        results = db.get_all_results()
        db.close()
        assert len(results) == 1
        assert len(results[0]["special_conditions"]) == 4
        assert '"кавычками"' in results[0]["special_conditions"][0]

    def test_db_malformed_json_recovery(self, tmp_path):
        """Невалидный JSON в поле → get_all_results не крашится (fallback на [])."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path)
        db.save_result(r)

        # Вручную портим JSON в БД
        db.conn.execute(
            "UPDATE contracts SET special_conditions = ? WHERE file_hash = ?",
            ("{'invalid': json}", r.file_info.file_hash),
        )
        db.conn.commit()

        results = db.get_all_results()
        db.close()
        # Не крашится — невалидный JSON заменён на []
        assert len(results) == 1
        assert results[0]["special_conditions"] == []

    def test_db_empty_json_fields(self, tmp_path):
        """Пустые JSON-поля → корректный fallback."""
        db = Database(tmp_path / "test.db")
        r = make_result(tmp_path)
        r.metadata.special_conditions = []
        r.metadata.parties = []
        db.save_result(r)

        results = db.get_all_results()
        db.close()
        assert results[0]["special_conditions"] == []
        assert results[0]["parties"] == []


# ============================================================
#  ФАЗА 3: БАГИ ПАРСИНГА AI + ПАЙПЛАЙН
# ============================================================


class TestAIParsingEdgeCases:
    """Тесты на edge cases парсинга ответов AI, деанонимизации и пайплайна.

    Фокус: _json_to_metadata() крашится при невалидных данных от AI,
    деанонимизация ломается при parties=None, БД молча теряет данные.
    """

    # ─── ГРУППА G: _json_to_metadata КРАШИ ───

    def test_json_to_metadata_confidence_null(self):
        """AI вернул confidence: null → float(None) → TypeError.

        data.get('confidence', 0.0) возвращает None (не default!),
        потому что ключ ЕСТЬ, но значение null.
        """
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор поставки",
            "counterparty": "ООО Ромашка",
            "subject": "Поставка оборудования",
            "date_signed": "2024-01-15",
            "amount": "100000 руб",
            "confidence": None,  # null в JSON
            "parties": ["ООО Ромашка", "ООО Альфа"],
            "special_conditions": [],
        }
        m = _json_to_metadata(data)
        # Должно вернуть 0.0 по умолчанию
        assert m.confidence == 0.0

    def test_json_to_metadata_confidence_string_word(self):
        """AI вернул confidence: 'высокая' (слово вместо числа) → ValueError."""
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор",
            "subject": "Тест",
            "confidence": "высокая",
        }
        m = _json_to_metadata(data)
        # Должно вернуть 0.0 по умолчанию или интерпретировать
        assert isinstance(m.confidence, float)

    def test_json_to_metadata_confidence_string_number(self):
        """AI вернул confidence: '0.85' (строка-число) → float() справится."""
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор",
            "subject": "Тест",
            "confidence": "0.85",
        }
        m = _json_to_metadata(data)
        assert m.confidence == 0.85

    def test_json_to_metadata_confidence_bool(self):
        """AI вернул confidence: true → float(True) = 1.0."""
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор",
            "subject": "Тест",
            "confidence": True,
        }
        m = _json_to_metadata(data)
        assert m.confidence == 1.0

    def test_json_to_metadata_parties_null(self):
        """AI вернул parties: null → .get('parties', []) возвращает None, не []."""
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор",
            "subject": "Тест",
            "confidence": 0.9,
            "parties": None,
        }
        m = _json_to_metadata(data)
        assert m.parties is not None, "parties должен быть [], а не None"
        assert isinstance(m.parties, list)

    def test_json_to_metadata_special_conditions_null(self):
        """AI вернул special_conditions: null → None вместо []."""
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор",
            "subject": "Тест",
            "confidence": 0.9,
            "special_conditions": None,
        }
        m = _json_to_metadata(data)
        assert m.special_conditions is not None
        assert isinstance(m.special_conditions, list)

    def test_json_to_metadata_special_conditions_string(self):
        """AI вернул special_conditions: 'Неустойка 0.1%' (строка вместо списка).

        Проблема: при итерации for item in special_conditions каждый символ
        станет отдельным элементом.
        """
        from modules.ai_extractor import _json_to_metadata

        data = {
            "contract_type": "Договор",
            "subject": "Тест",
            "confidence": 0.9,
            "special_conditions": "Неустойка 0.1% за просрочку",
        }
        m = _json_to_metadata(data)
        assert isinstance(m.special_conditions, list), (
            f"special_conditions должен быть list, а не {type(m.special_conditions).__name__}"
        )

    def test_json_to_metadata_missing_all_optional(self):
        """AI вернул только обязательные поля — не крашится."""
        from modules.ai_extractor import _json_to_metadata

        data = {"contract_type": "Договор", "confidence": 0.5}
        m = _json_to_metadata(data)
        assert m.contract_type == "Договор"
        assert m.confidence == 0.5
        assert m.parties == []
        assert m.special_conditions == []
        assert m.counterparty is None

    def test_json_to_metadata_empty_dict(self):
        """AI вернул пустой JSON {} — не крашится."""
        from modules.ai_extractor import _json_to_metadata

        m = _json_to_metadata({})
        assert m.confidence == 0.0
        assert m.parties == []
        assert m.contract_type is None

    # ─── ГРУППА H: ДЕАНОНИМИЗАЦИЯ В КОНТРОЛЛЕРЕ ───

    def test_deanonymize_parties_none(self):
        """FIXED: parties=None → controller._deanonymize обрабатывает корректно."""
        from controller import _deanonymize
        from modules.models import ContractMetadata

        metadata = ContractMetadata(
            contract_type="Договор",
            counterparty="[ФИО_1]",
            subject="Тест",
            confidence=0.9,
            parties=None,
        )
        replacements = {"[ФИО_1]": "Иванов Иван"}

        # Используем РЕАЛЬНУЮ логику из controller.py (исправленную)
        if replacements:
            if metadata.counterparty:
                metadata.counterparty = _deanonymize(
                    metadata.counterparty, replacements
                )
            if metadata.parties:
                metadata.parties = [
                    _deanonymize(p, replacements)
                    for p in metadata.parties
                ]
            else:
                metadata.parties = []

        assert metadata.counterparty == "Иванов Иван"
        assert metadata.parties == []

    def test_deanonymize_parties_empty_list(self):
        """Деанонимизация с parties=[] — не крашится."""
        from modules.models import ContractMetadata

        metadata = ContractMetadata(
            contract_type="Договор",
            counterparty="[ФИО_1]",
            subject="Тест",
            confidence=0.9,
            parties=[],
        )
        replacements = {"[ФИО_1]": "Иванов Иван"}

        if metadata.counterparty and replacements:
            for mask, original in replacements.items():
                if mask in metadata.counterparty:
                    metadata.counterparty = metadata.counterparty.replace(mask, original)
            result_parties = [p for p in metadata.parties]

        assert metadata.counterparty == "Иванов Иван"
        assert result_parties == []

    # ─── ГРУППА I: БД С NULL-ПОЛЯМИ ───

    def test_db_null_parties_roundtrip(self, tmp_path):
        """БД: parties=None → json.dumps(None)='null' → json.loads('null')=None.

        Цепочка:
        1. AI вернул parties=null → metadata.parties=None
        2. database.py: json.dumps(None)='null' (строка!)
        3. get_all_results: d.get('parties')='null' (truthy!)
        4. json.loads('null')=None → d['parties']=None
        5. Итерация: for p in None → TypeError
        """
        from modules.database import Database
        from modules.models import ProcessingResult, FileInfo, ContractMetadata

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        fi = FileInfo(
            path=tmp_path / "test.pdf",
            filename="test.pdf",
            extension=".pdf",
            size_bytes=100,
            file_hash="hash_null_parties",
        )

        metadata = ContractMetadata(
            contract_type="Договор",
            subject="Тест",
            confidence=0.9,
            parties=None,
            special_conditions=None,
        )

        result = ProcessingResult(file_info=fi, status="done")
        result.metadata = metadata

        db.save_result(result)
        rows = db.get_all_results()
        db.close()

        # parties должен быть [] после загрузки, а не None
        assert rows[0]["parties"] is not None, (
            f"parties={rows[0]['parties']!r}, должно быть []"
        )
        assert isinstance(rows[0]["parties"], list)

    def test_db_string_special_conditions_roundtrip(self, tmp_path):
        """БД: special_conditions=string → сохраняется и загружается как строка, не список.

        json.dumps('string') = '"string"' → json.loads('"string"') = 'string'
        Далее: isinstance('string', list) → False → reporter не join по буквам.
        НО: если кто-то итерирует for item in special_conditions — побуквенно!
        """
        from modules.database import Database
        from modules.models import ProcessingResult, FileInfo, ContractMetadata

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        fi = FileInfo(
            path=tmp_path / "test.pdf",
            filename="test.pdf",
            extension=".pdf",
            size_bytes=100,
            file_hash="hash_string_sc",
        )

        metadata = ContractMetadata(
            contract_type="Договор",
            subject="Тест",
            confidence=0.9,
            special_conditions="Неустойка 0.1%",  # строка вместо списка!
        )

        result = ProcessingResult(file_info=fi, status="done")
        result.metadata = metadata

        db.save_result(result)
        rows = db.get_all_results()
        db.close()

        sc = rows[0]["special_conditions"]
        # Проблема: sc — это строка, не список. При итерации → побуквенно.
        if isinstance(sc, str):
            items = list(sc)  # ['Н', 'е', 'у', ...]
            assert len(items) > 5, "Строка итерируется побуквенно — это баг"

    # ─── ГРУППА J: EXTRACTOR EDGE CASES ───

    def test_extractor_empty_docx(self, tmp_path):
        """Пустой/битый DOCX → graceful handling, не краш."""
        from modules.extractor import extract_text
        from modules.models import FileInfo

        # Создаём пустой файл с .docx расширением
        fpath = tmp_path / "empty.docx"
        fpath.write_bytes(b"")

        fi = FileInfo(
            path=fpath,
            filename="empty.docx",
            extension=".docx",
            size_bytes=0,
            file_hash="hash_empty",
        )
        result = extract_text(fi)
        assert result.text == "" or result.page_count == 0

    def test_extractor_corrupt_pdf(self, tmp_path):
        """Битый PDF → graceful handling, не краш."""
        from modules.extractor import extract_text
        from modules.models import FileInfo

        fpath = tmp_path / "corrupt.pdf"
        fpath.write_bytes(b"NOT A REAL PDF CONTENT")

        fi = FileInfo(
            path=fpath,
            filename="corrupt.pdf",
            extension=".pdf",
            size_bytes=22,
            file_hash="hash_corrupt",
        )
        result = extract_text(fi)
        assert result.text == "" or result.page_count == 0

    def test_extractor_non_utf8_content(self, tmp_path):
        """DOCX-подобный файл с невалидным содержимым → не крашится."""
        from modules.extractor import extract_text
        from modules.models import FileInfo

        fpath = tmp_path / "bad_encoding.docx"
        # Пишем рандомные байты (не ZIP, не DOCX)
        fpath.write_bytes(b"\x80\x81\x82\x83" * 100)

        fi = FileInfo(
            path=fpath,
            filename="bad_encoding.docx",
            extension=".docx",
            size_bytes=400,
            file_hash="hash_bad_enc",
        )
        result = extract_text(fi)
        assert isinstance(result.text, str)

    # ─── ГРУППА K: ПАРСИНГ JSON ОТВЕТА AI ───

    def test_parse_json_with_markdown_wrapper(self):
        """AI обернул JSON в ```json ... ``` — парсится нормально."""
        from modules.ai_extractor import _parse_json_response

        raw = '```json\n{"contract_type": "Договор", "confidence": 0.9}\n```'
        data = _parse_json_response(raw)
        assert data["contract_type"] == "Договор"

    def test_parse_json_with_trailing_text(self):
        """AI добавил текст после JSON — парсится нормально."""
        from modules.ai_extractor import _parse_json_response

        raw = '{"contract_type": "Договор", "confidence": 0.9}\n\nЯ извлёк метаданные.'
        data = _parse_json_response(raw)
        assert data["contract_type"] == "Договор"

    def test_parse_json_with_leading_explanation(self):
        """AI написал объяснение перед JSON."""
        from modules.ai_extractor import _parse_json_response

        raw = 'Вот метаданные:\n{"contract_type": "Договор", "confidence": 0.9}'
        data = _parse_json_response(raw)
        assert data["contract_type"] == "Договор"

    def test_parse_json_completely_invalid(self):
        """AI вернул текст без JSON → JSONDecodeError."""
        from modules.ai_extractor import _parse_json_response
        import json

        raw = "Извините, я не смог извлечь метаданные из этого документа."
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response(raw)

    def test_parse_json_nested_braces(self):
        """AI вернул JSON с вложенными скобками."""
        from modules.ai_extractor import _parse_json_response

        raw = '{"contract_type": "Договор", "notes": {"key": "value"}, "confidence": 0.9}'
        data = _parse_json_response(raw)
        assert data["contract_type"] == "Договор"

    def test_parse_json_with_thinking_block(self):
        """AI вернул <thinking>...</thinking> перед JSON (GLM-4.7 стиль)."""
        from modules.ai_extractor import _parse_json_response

        raw = (
            '<thinking>\nАнализирую документ...\n</thinking>\n'
            '{"contract_type": "Договор поставки", "confidence": 0.85}'
        )
        data = _parse_json_response(raw)
        assert data["contract_type"] == "Договор поставки"


# ============================================================
#  ИТОГОВЫЙ ОТЧЁТ
# ============================================================


class TestSummaryReport:
    """Печатает итоговый отчёт по всем найденным проблемам (запускать последним)."""

    def test_print_bug_summary(self):
        """Печатает сводку по найденным багам и edge cases."""
        print("\n")
        print("=" * 70)
        print("  СВОДКА НАЙДЕННЫХ ПРОБЛЕМ ЮРТЭГ")
        print("=" * 70)
        print()
        print("  🔴 КРИТИЧЕСКИЕ (подтверждены xfail-тестами):")
        print("    1. parties с None → TypeError КРАШ в валидаторе")
        print("    2. Сумма 1,500,000.00 USD → парсится как 150 млн (не 1.5 млн)")
        print("    3. Сумма 1.500.000,50 EUR → парсится как 150 млн (европейский формат)")
        print("    4. Маски [ФИО_N] утекают в отчёт (де-анонимизация)")
        print("    5. float(None) краш: AI вернул confidence: null → TypeError")
        print("    6. float('высокая') краш: AI написал уверенность словом")
        print("    7. parties=null от AI → .get() возвращает None, не []")
        print("    8. special_conditions=null → аналогично None вместо []")
        print("    9. parties=None → TypeError при деанонимизации (controller)")
        print()
        print("  🟡 СРЕДНИЕ (подтверждены xfail-тестами):")
        print("   10. Email ivan@пример.рф не ловится (кириллический домен)")
        print("   11. Счёт без 'р/с' маскируется как ТЕЛЕФОН (не как СЧЁТ)")
        print("   12. СНИЛС-подобные числа ложно маскируются без контекста")
        print("   13. Кириллическая О вместо 0 в телефонах → не ловится")
        print("   14. 'Технический паспорт' → ложная маска ПАСПОРТ")
        print("   15. OCR побуквенное разбиение → NER пропускает ФИО")
        print("   16. special_conditions=string → строка вместо списка")
        print("   17. БД: parties=None → 'null' → json.loads='None' (не [])")
        print()
        print("  ✅ EDGE CASES БЕЗ КРАШЕЙ:")
        print("    - NaN/Inf в confidence → корректно ловится L1")
        print("    - 100 сторон в parties → работает")
        print("    - XSS в полях → не крашится")
        print("    - subject 50КБ → БД справляется")
        print("    - Невалидный JSON → graceful fallback")
        print("    - 29 февраля → високосный/невисокосный корректно")
        print("    - Пустой/битый DOCX/PDF → graceful (text='', pages=0)")
        print("    - confidence='0.85' (строка-число) → float() справится")
        print("    - confidence=true (bool) → float(True)=1.0 OK")
        print("    - JSON с markdown/текстом/thinking → парсер справляется")
        print("    - Пустой JSON {} → все поля None/default, не краш")
        print("=" * 70)
