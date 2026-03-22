from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel, LoraConfig, get_peft_model
from trl import DPOTrainer, DPOConfig
import torch

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)

print("Loading model...")
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", quantization_config=bnb, device_map="auto")
model = PeftModel.from_pretrained(base, "./sft-adapter")
model = model.merge_and_unload()

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
tokenizer.pad_token = tokenizer.eos_token

lora_config = LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

train_ds = load_dataset("json", data_files="./data/dpo_train.jsonl", split="train")
val_ds = load_dataset("json", data_files="./data/dpo_val.jsonl", split="train")
print(f"DPO train: {len(train_ds)}, val: {len(val_ds)}")

args = DPOConfig(
    output_dir="./outputs/yurteg-dpo-v2",
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=5e-5,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    bf16=True,
    logging_steps=1,
    save_strategy="epoch",
    save_total_limit=2,
    eval_strategy="epoch",
    seed=42,
    max_length=4096,
    max_prompt_length=3072,
)

trainer = DPOTrainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    processing_class=tokenizer,
)

print("Starting DPO...")
trainer.train()
trainer.save_model("./outputs/yurteg-dpo-v2")
tokenizer.save_pretrained("./outputs/yurteg-dpo-v2")
print("DPO Done!")
