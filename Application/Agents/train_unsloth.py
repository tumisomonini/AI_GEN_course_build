import os
from unsloth import FastLanguageModel
import torch
from trl.trainer.sft_trainer import SFTTrainer
from trl.trainer.sft_config import SFTConfig
from datasets import Dataset
from Application.Ports.postgres_repo import PostgresRepo

def get_training_data():
    """Pull approved chapter content from Postgres for fine-tuning."""
    repo = PostgresRepo() # Instantiate the repo
    rows = repo.get_training_chapters(min_length=500) # Use the dedicated method
    repo.close() # Ensure the connection is closed
    
    # Format into Instruction-Input-Output style for LLM
    formatted_data = []
    for title, content in rows:
        formatted_data.append({
            "instruction": f"Generate a comprehensive educational chapter on '{title}'.",
            "input": "",
            "output": content
        })
    return Dataset.from_list(formatted_data)

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        # Standard Alpaca-style formatting
        text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
        texts.append(text)
    return { "text" : texts, }

def train():
    model_name = "unsloth/llama-3-8b-instruct-bnb-4bit"
    max_seq_length = 2048
    
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = model_name,
        max_seq_length = max_seq_length,
        load_in_4bit = True,
    )
    
    tokenizer.model_max_length = max_seq_length

    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj",],
        lora_alpha = 16,
        lora_dropout = 0,
        bias = "none",
        use_gradient_checkpointing = "unsloth",
    )

    dataset = get_training_data()
    dataset = dataset.map(formatting_prompts_func, batched=True)

    if len(dataset) == 0:
        print("⚠️ Training aborted: No data found in the 'generated' chapters table.")
        return

    # Optimized configuration for the Supervised Fine-Tuning (SFT) engine.
    # We utilize 8-bit Adam optimization to maintain a low VRAM footprint.
    sft_config = SFTConfig(
        dataset_text_field="text",
        output_dir="course_author_lora_checkpoints",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=3,
        warmup_ratio=0.1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        logging_steps=1,
        report_to="none",
        save_strategy="epoch",
        save_total_limit=2,
        seed=42,
        logging_dir="./logs",
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
    )

    trainer.train()
    
    # Export for use in the AuthorAgent
    model.save_pretrained_gguf("model_unsloth_optimized", tokenizer, quantization_method = "q4_k_m")

if __name__ == "__main__":
    train()