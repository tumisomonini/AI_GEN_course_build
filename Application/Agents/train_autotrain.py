import os
import sys
from pathlib import Path
import pandas as pd

# Ensure script can find Application and Domain packages when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Application.Ports.postgres_repo import PostgresRepo

def prepare_autotrain_data():
    """
    Fetch generated chapter content from Postgres and format it for 
    AutoTrain LLM fine-tuning.
    """
    repo = PostgresRepo()
    print("📥 Fetching training data from Postgres...")
    
    with repo.get_cursor() as cur:
        # We only train on successfully generated content longer than 500 chars
        cur.execute("""
            SELECT c.title, c.content 
            FROM chapters c 
            WHERE c.status = 'generated' AND length(c.content) > 500
        """)
        rows = cur.fetchall()
    repo.close()

    if not rows:
        print("❌ No high-quality training data found in database.")
        return False

    # AutoTrain LLM SFT expects a 'text' column.
    # We use a standard Alpaca-style instruction format to fine-tune 
    # the model on your specific course-generation style.
    formatted_data = []
    for title, content in rows:
        text = f"### Instruction: Write a comprehensive educational chapter about {title}.\n\n### Response: {content}"
        formatted_data.append({"text": text})
    
    df = pd.DataFrame(formatted_data)
    
    # AutoTrain requires a directory containing CSV/JSONL files
    data_dir = "autotrain_training_data"
    os.makedirs(data_dir, exist_ok=True)
    df.to_csv(f"{data_dir}/train.csv", index=False)
    
    print(f"✅ Prepared {len(df)} samples in {data_dir}/train.csv")
    return True

def get_autotrain_command():
    """
    Returns the command to trigger AutoTrain locally. 
    Requires: pip install autotrain-advanced
    """
    model_name = os.getenv("AUTOTRAIN_BASE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
    project_name = "course_author_model_autotrain"
    
    # This command uses the SFT (Supervised Fine-Tuning) trainer
    cmd = (
        f"autotrain llm --train --model {model_name} "
        f"--data-path autotrain_training_data/ "
        f"--project-name {project_name} "
        f"--lr 2e-4 --batch-size 2 --epochs 3 --trainer sft --peft "
    )
    
    if os.getenv("HF_TOKEN"):
        hf_user = os.getenv("HF_USERNAME", "your-hf-username")
        cmd += f"--push-to-hub --repo-id {hf_user}/{project_name}"
        
    # Note: This command is intended to be run in a terminal where autotrain-advanced is installed.
    # It is not automatically executed by this script to allow for user review.
    return cmd

if __name__ == "__main__":
    if prepare_autotrain_data():
        print("\n🚀 Data is ready. To start training, run the following command:")
        print(get_autotrain_command())