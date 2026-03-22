from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model
from trl import ORPOTrainer, ORPOConfig
import torch

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)

print("Loading model...")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", quantization_config=bnb, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
tokenizer.pad_token = tokenizer.eos_token

lora_config = LoraConfig(r=64, lora_alpha=128, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")

print("Loading data...")
train_ds = load_dataset("json", data_files="./data/v3_preference_train.jsonl", split="train")
val_ds = load_dataset("json", data_files="./data/v3_preference_val.jsonl", split="train")
print(f"Train: {len(train_ds)}, Val: {len(val_ds)}")

args = ORPOConfig(
    output_dir="./outputs/yurteg-orpo-v3",
    num_train_epochs=5,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=8e-5,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    bf16=True,
    logging_steps=5,
    save_strategy="epoch",
    save_total_limit=3,
    eval_strategy="no",
    seed=42,
    max_length=4096,
    beta=0.2,
    gradient_checkpointing=True,
)

trainer = ORPOTrainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    processing_class=tokenizer,
    peft_config=lora_config,
)

print("Starting ORPO...")
trainer.train()
trainer.save_model("./outputs/yurteg-orpo-v3")
tokenizer.save_pretrained("./outputs/yurteg-orpo-v3")
print("ORPO Done!")
