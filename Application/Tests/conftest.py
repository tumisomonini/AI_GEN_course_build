import pytest
from pathlib import Path
from dotenv import load_dotenv

@pytest.fixture(autouse=True)
def load_env():
    """Auto-load root .env for all tests."""
    env_path = Path(__file__).resolve().parents[3] / '.env'  # Tests -> Application -> root
    if env_path.exists():
        load_dotenv(env_path)
    else:
        pytest.skip("Missing .env - copy .env.example")
