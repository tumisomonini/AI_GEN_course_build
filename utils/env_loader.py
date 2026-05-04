from pathlib import Path
from dotenv import load_dotenv
import os

def load_root_env():
    """Load .env from project root reliably, with debug."""
    root = Path(__file__).resolve().parents[1]
    env_path = root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded env from {env_path}")
        # Verify critical vars loaded (without printing values)
        critical = ['NEO4J_URI', 'POSTGRES_HOST', 'OPENROUTER_API_KEY']
        missing = [v for v in critical if not os.getenv(v)]
        if missing:
            print(f"⚠️ Missing critical env vars: {missing}")
        else:
            print("✅ All critical env vars present")
    else:
        print(f"⚠️ .env not found at {env_path}. Copy .env.example -> .env")
