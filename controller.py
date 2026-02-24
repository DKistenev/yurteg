"""Контроллер пайплайна обработки.

Оркестрирует все модули: сканирование → извлечение текста → анонимизация →
AI-извлечение метаданных → валидация → сохранение в БД → организация файлов →
генерация отчёта. Обеспечивает резюмируемость и устойчивость к ошибкам.

AI-запросы выполняются параллельно через ThreadPoolExecutor (bottleneck ~4 сек/файл).
Извлечение текста и анонимизация — последовательно (быстрые операции <0.1 сек).
"""
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from config import Config
from modules.ai_extractor import extract_metadata, verify_api_key, verify_metadata
from modules.anonymizer import anonymize
from modules.database import Database
from modules.extractor import extract_text
from modules.models import ProcessingResult
from modules.organizer import organize_file, prepare_output_directory
from modules.reporter import generate_report
from modules.scanner import scan_directory
from modules.validator import validate_batch, validate_metadata

logger = logging.getLogger(__name__)


class Controller:
    """Оркестратор пайплайна обработки архива договоров."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def process_archive(
        self,
        source_dir: Path,
        grouping: str = "both",
        force_reprocess: bool = False,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_file_done: Optional[Callable[[ProcessingResult], None]] = None,
        output_dir_override: Optional[Path] = None,
    ) -> dict:
        """Обрабатывает весь архив.

        Args:
            source_dir: папка с договорами
            grouping: режим группировки ("type" | "counterparty" | "both")
            force_reprocess: игнорировать кэш и обработать все файлы заново
            on_progress: callback(current, total, message) для UI
            on_file_done: callback(result) после обработки каждого файла
            output_dir_override: принудительная выходная папка (для облачного режима)

        Returns:
            dict: {total, done, errors, skipped, output_dir, report_path}
        """
        # 1. Подготовить выходную директорию
        if output_dir_override:
            output_dir = output_dir_override
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = prepare_output_directory(source_dir, self.config)
        _notify(on_progress, 0, 0, f"Выходная папка: {output_dir}")

        # 2. Инициализировать БД
        db = Database(output_dir / "yurteg.db")

        try:
            stats = self._run_pipeline(
                source_dir, output_dir, db, grouping, force_reprocess,
                on_progress, on_file_done,
            )
        finally:
            db.close()

        return stats

    def _run_pipeline(
        self,
        source_dir: Path,
        output_dir: Path,
        db: Database,
        grouping: str,
        force_reprocess: bool,
        on_progress: Optional[Callable],
        on_file_done: Optional[Callable],
    ) -> dict:
        """Основная логика пайплайна.

        Этапы:
          A) extract_text + anonymize — последовательно (быстро, <0.1 с/файл)
          B) extract_metadata (AI) — параллельно через ThreadPoolExecutor (~4 с/файл)
          C) validate + organize + save — последовательно (быстро)
        """
        # 3. Сканировать файлы
        _notify(on_progress, 0, 0, "Сканирование файлов...")
        files = scan_directory(source_dir, self.config)
        total = len(files)
        _notify(on_progress, 0, total, f"Найдено {total} файлов")

        if total == 0:
            return {
                "total": 0, "done": 0, "errors": 0, "skipped": 0,
                "output_dir": output_dir, "report_path": None,
            }

        # 4. Отфильтровать уже обработанные (или переобработать все)
        if force_reprocess:
            db.clear_all()
            new_files = files
            skipped = 0
            _notify(on_progress, 0, total, "Режим переобработки: все файлы")
        else:
            new_files = [f for f in files if not db.is_processed(f.file_hash)]
            skipped = total - len(new_files)
            if skipped > 0:
                _notify(on_progress, skipped, total,
                        f"Пропущено {skipped} ранее обработанных")

        results: list[ProcessingResult] = []
        done = 0
        errors = 0

        # ── Этап A: извлечение текста + анонимизация (последовательно) ──
        prepared = []  # (result, anonymized_text)
        for file_info in new_files:
            result = ProcessingResult(file_info=file_info, status="processing")
            try:
                text = extract_text(file_info)
                result.text = text

                if text.extraction_method == "failed" or not text.text.strip():
                    result.status = "error"
                    result.error_message = "Не удалось извлечь текст"
                    db.save_result(result)
                    if on_file_done:
                        on_file_done(result)
                    results.append(result)
                    errors += 1
                    continue

                if text.is_scanned:
                    result.status = "error"
                    result.error_message = "Сканированный PDF — требует OCR"
                    db.save_result(result)
                    if on_file_done:
                        on_file_done(result)
                    results.append(result)
                    errors += 1
                    continue

                anonymized = anonymize(text.text, self.config.anonymize_types)
                result.anonymized = anonymized
                prepared.append((result, anonymized))
            except Exception as e:
                logger.error("Этап A ошибка: %s — %s", file_info.filename, e, exc_info=True)
                result.status = "error"
                result.error_message = str(e)
                db.save_result(result)
                if on_file_done:
                    on_file_done(result)
                results.append(result)
                errors += 1

        # ── Этап B: AI-извлечение метаданных (параллельно) ──────────
        _notify(on_progress, skipped, total, "AI-анализ договоров...")
        completed_count = skipped + errors  # уже посчитанные

        def _ai_task(item):
            result, anonymized = item
            metadata = extract_metadata(anonymized.text, self.config)
            return result, anonymized, metadata

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(_ai_task, item): item for item in prepared}
            for future in as_completed(futures):
                item = futures[future]
                result, anonymized = item
                try:
                    result, anonymized, metadata = future.result()
                    result.metadata = metadata
                    result.model_used = self.config.active_model

                    # Деанонимизация контрагента и сторон
                    if anonymized.replacements:
                        if metadata.counterparty:
                            metadata.counterparty = _deanonymize(
                                metadata.counterparty, anonymized.replacements
                            )
                        if metadata.parties:
                            metadata.parties = [
                                _deanonymize(p, anonymized.replacements)
                                for p in metadata.parties
                            ]
                        else:
                            metadata.parties = []

                    # Валидация L1–L3
                    validation = validate_metadata(metadata, self.config)
                    result.validation = validation

                    # AI-верификация L5 (selective: только для проблемных)
                    if (
                        self.config.validation_mode == "selective"
                        and validation.status in ("warning", "unreliable")
                    ) or self.config.validation_mode == "full":
                        logger.info("L5 верификация: %s", result.file_info.filename)
                        v5 = verify_metadata(
                            anonymized.text, metadata, self.config,
                        )
                        if v5.get("correct", True):
                            validation.warnings.append(
                                "L5: AI подтвердил корректность данных"
                            )
                        else:
                            # AI нашёл проблемы — пробуем применить исправления
                            applied = 0
                            for corr in v5.get("corrections") or []:
                                field = corr.get("field", "")
                                suggested = corr.get("suggested")
                                if field and suggested and hasattr(metadata, field):
                                    old_val = getattr(metadata, field)
                                    setattr(metadata, field, suggested)
                                    validation.warnings.append(
                                        f"L5: AI исправил {field}: "
                                        f"«{old_val}» → «{suggested}»"
                                    )
                                    applied += 1
                            if applied > 0:
                                # Пересчитать валидацию после исправлений
                                l5_warnings = [
                                    w for w in validation.warnings
                                    if w.startswith("L5:")
                                ]
                                validation = validate_metadata(
                                    metadata, self.config,
                                )
                                validation.warnings.extend(l5_warnings)
                                result.validation = validation
                            else:
                                # AI сказал «неправильно», но не предложил
                                # конкретных исправлений
                                reasoning = v5.get("reasoning", "")
                                validation.warnings.append(
                                    f"L5: AI считает данные неточными"
                                    + (f" ({reasoning[:120]})"
                                       if reasoning else "")
                                )

                    # Организация файла
                    organized_path = organize_file(result, output_dir, grouping)
                    result.organized_path = organized_path

                    result.status = "done"
                    result.processed_at = datetime.now()
                    done += 1

                except Exception as e:
                    logger.error("AI ошибка: %s — %s", result.file_info.filename, e, exc_info=True)
                    result.status = "error"
                    result.error_message = str(e)
                    errors += 1

                db.save_result(result)
                if on_file_done:
                    on_file_done(result)
                results.append(result)
                completed_count += 1
                _notify(on_progress, completed_count, total,
                        f"Обработка: {result.file_info.filename}")

        # 6. Перекрёстная валидация L4
        if results:
            _notify(on_progress, total, total, "Перекрёстная валидация...")
            results = validate_batch(results, self.config)
            for r in results:
                if r.status == "done":
                    db.save_result(r)

        # 7. Генерация Excel-реестра
        _notify(on_progress, total, total, "Генерация Excel-реестра...")
        all_data = db.get_all_results()
        report_path = generate_report(all_data, output_dir)

        stats = {
            "total": total,
            "done": done + skipped,
            "errors": errors,
            "skipped": skipped,
            "output_dir": output_dir,
            "report_path": report_path,
        }
        _notify(on_progress, total, total,
                f"Готово! Обработано: {done}, ошибок: {errors}, "
                f"пропущено: {skipped}")
        return stats


def _deanonymize(text: str, replacements: dict[str, str]) -> str:
    """Заменяет маски обратно на оригинальные значения.

    После замены известных масок удаляет оставшиеся маски вида [ТИП_N],
    которые AI мог придумать (например, [ФИО_3] при наличии только [ФИО_1], [ФИО_2]).
    """
    for mask, original in replacements.items():
        text = text.replace(mask, original)
    # Убираем оставшиеся маски, которых не было в replacements
    text = re.sub(r'\[[А-ЯЁA-Z_]+_\d+\]', '', text).strip()
    return text


def _notify(
    callback: Optional[Callable], current: int, total: int, message: str,
) -> None:
    """Вызывает callback и логирует сообщение."""
    if callback:
        callback(current, total, message)
    logger.info(message)
