"""Экспорт датасета для обучения модели: SFT + DPO.

Генерирует:
  training/sft_train.jsonl   — обучающая выборка SFT (ChatML)
  training/sft_val.jsonl     — валидационная выборка SFT
  training/dpo_train.jsonl   — обучающая выборка DPO (chosen/rejected)
  training/dpo_val.jsonl     — валидационная выборка DPO

Запуск:
    cd /path/to/yurteg
    python dataset/export_training.py
"""
import sys
import json
import random
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ai_extractor import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from config import Config

DATASET_DIR = Path(__file__).parent
TRAIN_DIR = DATASET_DIR / "training"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


# ─── Конвертация записей ─────────────────────────────────────────────────────

def _build_user_prompt(record: dict, config: Config) -> str:
    """Формирует user-промпт из записи (точно как в ai_extractor)."""
    types_str = ", ".join(f'"{t}"' for t in config.document_types_hints)
    return USER_PROMPT_TEMPLATE.format(
        document_types=types_str,
        text=record["input_text"],
    )


def _output_json(record: dict) -> str:
    """Компактный JSON из output записи."""
    return json.dumps(record.get("output", {}), ensure_ascii=False)


def make_sft_example(record: dict, config: Config) -> dict:
    """SFT-пример в ChatML формате."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(record, config)},
            {"role": "assistant", "content": _output_json(record)},
        ]
    }


def make_dpo_example(correct: dict, wrong: dict, config: Config) -> dict:
    """DPO-пример: chosen (правильный) vs rejected (неправильный)."""
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(correct, config)},
        ],
        "chosen": [
            {"role": "assistant", "content": _output_json(correct)},
        ],
        "rejected": [
            {"role": "assistant", "content": _output_json(wrong)},
        ],
    }


# ─── Загрузка ────────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    records = []
    if not path.exists():
        logger.warning("Файл не найден: %s", path)
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def write_jsonl(path: Path, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ─── Главная ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Экспорт датасета для обучения (SFT + DPO)")
    parser.add_argument("--reviewed", type=Path, default=DATASET_DIR / "labeled_data_reviewed.jsonl",
                        help="Одобренные записи (основной ревью)")
    parser.add_argument("--reviewed-fixed", type=Path, default=DATASET_DIR / "labeled_data_reviewed_fixed.jsonl",
                        help="Одобренные исправления")
    parser.add_argument("--errors", type=Path, default=DATASET_DIR / "labeled_data_errors.jsonl",
                        help="Ошибочные записи (для DPO-пар)")
    parser.add_argument("--out-dir", type=Path, default=TRAIN_DIR)
    parser.add_argument("--val-split", type=float, default=0.1, help="Доля валидации (по умолчанию 10%%)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    config = Config()

    # ─── SFT: все одобренные записи ──────────────────────────────────────
    reviewed = load_jsonl(args.reviewed)
    reviewed_fixed = load_jsonl(args.reviewed_fixed)
    all_approved = reviewed + reviewed_fixed
    logger.info("Одобренных записей: %d (основных %d + исправленных %d)",
                len(all_approved), len(reviewed), len(reviewed_fixed))

    if not all_approved:
        logger.error("Нет одобренных записей!")
        sys.exit(1)

    sft_data = [make_sft_example(r, config) for r in all_approved]
    random.shuffle(sft_data)

    val_size = max(1, int(len(sft_data) * args.val_split))
    sft_val = sft_data[:val_size]
    sft_train = sft_data[val_size:]

    write_jsonl(args.out_dir / "sft_train.jsonl", sft_train)
    write_jsonl(args.out_dir / "sft_val.jsonl", sft_val)
    logger.info("SFT train: %d примеров", len(sft_train))
    logger.info("SFT val:   %d примеров", len(sft_val))

    # ─── DPO: пары правильный/неправильный ───────────────────────────────
    errors = load_jsonl(args.errors)
    errors_by_id = {r.get("id", ""): r for r in errors}

    dpo_data = []
    for correct in reviewed_fixed:
        rid = correct.get("id", "")
        if rid in errors_by_id:
            dpo_data.append(make_dpo_example(correct, errors_by_id[rid], config))

    if dpo_data:
        random.shuffle(dpo_data)
        dpo_val_size = max(1, int(len(dpo_data) * args.val_split))
        dpo_val = dpo_data[:dpo_val_size]
        dpo_train = dpo_data[dpo_val_size:]

        write_jsonl(args.out_dir / "dpo_train.jsonl", dpo_train)
        write_jsonl(args.out_dir / "dpo_val.jsonl", dpo_val)
        logger.info("DPO train: %d пар", len(dpo_train))
        logger.info("DPO val:   %d пар", len(dpo_val))
    else:
        logger.warning("Нет DPO-пар")

    # ─── Статистика ──────────────────────────────────────────────────────
    total_chars = sum(len(m["content"]) for item in sft_data for m in item["messages"])
    approx_tokens = total_chars // 3  # грубая оценка для русского

    logger.info("─" * 40)
    logger.info("Результат в %s/", args.out_dir)
    logger.info("SFT:    %d примеров (train %d + val %d)", len(sft_data), len(sft_train), len(sft_val))
    if dpo_data:
        logger.info("DPO:    %d пар (train %d + val %d)", len(dpo_data), len(dpo_train), len(dpo_val))
    logger.info("Токенов ≈ %s", f"{approx_tokens:,}")
    logger.info("─" * 40)


if __name__ == "__main__":
    main()
