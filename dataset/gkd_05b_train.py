#!/usr/bin/env python3
"""
ЮрТэг — GKD дистилляция Qwen 1.5B → 0.5B (Этап 2 из 2)

Запуск на RunPod после SFT:
  pip install trl>=0.12.0 transformers accelerate peft bitsandbytes
  python gkd_05b_train.py --teacher_model ./yurteg-1.5b-merged --sft_model ./yurteg-0.5b-sft-merged

Требования: GPU 16GB+ (оба модели в bf16 + LoRA на студенте)
"""

import argparse
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig


def main():
    parser = argparse.ArgumentParser(description="GKD distillation 1.5B → 0.5B")
    parser.add_argument(
        "--teacher_model",
        type=str,
        required=True,
        help="Путь к дообученной 1.5B (merged HF формат, НЕ GGUF!)",
    )
    parser.add_argument(
        "--sft_model",
        type=str,
        default="./outputs/yurteg-qwen2.5-0.5b-sft",
        help="Путь к SFT'd 0.5B (результат этапа 1)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./outputs/yurteg-qwen2.5-0.5b-gkd",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-5)
    args = parser.parse_args()

    # Импорт GKD (experimental в TRL)
    try:
        from trl import GKDConfig, GKDTrainer
    except ImportError:
        from trl.experimental.gkd import GKDConfig, GKDTrainer

    print("=" * 60)
    print("  ЮрТэг GKD: Qwen 1.5B → 0.5B")
    print("=" * 60)

    # --- Токенизатор ---
    print("\n  Загрузка токенизатора...")
    tokenizer = AutoTokenizer.from_pretrained(args.sft_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- Датасет ---
    print("  Загрузка датасета...")
    dataset = load_dataset(
        "SuperPuperD/yurteg-legal-sft",
        data_files={"train": "05b_sft_train.jsonl", "test": "05b_sft_val.jsonl"},
    )
    train_dataset = dataset["train"]
    eval_dataset = dataset["test"]
    print(f"  Train: {len(train_dataset)}, Val: {len(eval_dataset)}")

    # --- LoRA на студенте ---
    peft_config = LoraConfig(
        r=32,
        lora_alpha=64,
        lora_dropout=0.0,  # GKD отключает dropout
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    # --- GKD конфиг ---
    training_args = GKDConfig(
        output_dir=args.output_dir,

        # GKD-специфичные параметры
        lmbda=1.0,              # чисто on-policy (студент генерирует сам)
        beta=0.1,               # forward KL (покрытие распределения учителя)
        temperature=0.9,        # температура генерации
        max_new_tokens=512,     # макс длина JSON ответа

        # Обучение
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        weight_decay=0.01,

        # Точность
        bf16=True,

        # Логирование
        logging_steps=5,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="epoch",
        save_total_limit=2,

        # Длина
        max_seq_length=2048,

        seed=42,
    )

    # --- Студент ---
    print(f"\n  Загрузка студента: {args.sft_model}")
    student = AutoModelForCausalLM.from_pretrained(
        args.sft_model,
        torch_dtype="bfloat16",
    )

    # --- Учитель ---
    print(f"  Загрузка учителя: {args.teacher_model}")
    teacher = AutoModelForCausalLM.from_pretrained(
        args.teacher_model,
        torch_dtype="bfloat16",
    )

    # --- Тренер ---
    print("  Инициализация GKDTrainer...")

    trainer = GKDTrainer(
        model=student,
        teacher_model=teacher,
        args=training_args,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        peft_config=peft_config,
    )

    # --- Обучение ---
    print("\n  Начало обучения GKD...")
    trainer.train()

    # --- Сохранение ---
    print(f"\n  Сохранение в {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print("\n  Готово! Следующие шаги:")
    print("  1. Merge LoRA: python -m peft.merge_and_unload ...")
    print("  2. Конвертация в GGUF: python llama.cpp/convert_hf_to_gguf.py ...")
    print("  3. Квантизация: llama-quantize ... Q4_K_M")
    print("  4. Загрузка на HuggingFace")


if __name__ == "__main__":
    main()
