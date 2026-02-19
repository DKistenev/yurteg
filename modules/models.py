"""Модели данных, общие для всех модулей."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class FileInfo:
    """Информация о найденном файле."""
    path: Path
    filename: str
    extension: str  # ".pdf" или ".docx"
    size_bytes: int
    file_hash: str  # SHA-256


@dataclass
class ExtractedText:
    """Результат извлечения текста."""
    text: str
    page_count: int
    is_scanned: bool  # True если текст почти пустой (сканированный PDF)
    extraction_method: str  # "pdfplumber" | "python-docx" | "ocr" | "failed"


@dataclass
class AnonymizedText:
    """Результат анонимизации."""
    text: str  # Анонимизированный текст
    replacements: dict[str, str]  # маска -> исходное значение
    stats: dict[str, int]  # {"ФИО": 3, "ТЕЛЕФОН": 2, ...}


@dataclass
class ContractMetadata:
    """Метаданные, извлечённые AI из договора."""
    contract_type: Optional[str] = None
    counterparty: Optional[str] = None
    subject: Optional[str] = None
    date_signed: Optional[str] = None  # ISO format YYYY-MM-DD
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    amount: Optional[str] = None
    special_conditions: list[str] = field(default_factory=list)
    parties: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ValidationResult:
    """Результат валидации метаданных."""
    status: str  # "ok" | "warning" | "unreliable" | "error"
    warnings: list[str] = field(default_factory=list)  # Список сработавших правил
    score: float = 1.0  # 0-1, итоговый балл


@dataclass
class ProcessingResult:
    """Полный результат обработки одного файла."""
    file_info: FileInfo
    text: Optional[ExtractedText] = None
    anonymized: Optional[AnonymizedText] = None
    metadata: Optional[ContractMetadata] = None
    validation: Optional[ValidationResult] = None
    organized_path: Optional[Path] = None
    status: str = "pending"  # "pending" | "processing" | "done" | "error"
    error_message: Optional[str] = None
    model_used: Optional[str] = None
    processed_at: Optional[datetime] = None
