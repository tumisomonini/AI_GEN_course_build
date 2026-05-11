"""AstraDB initialization module."""
import sys
from pathlib import Path

# Ensure project root is on sys.path so 'Application' package is found
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from Application.API.dependencies import init_astra_singleton

def init_astra(*args, **kwargs):
    """Initialize AstraDB using centralized dependency logic."""
    # Centralized init handles env-driven configuration
    return init_astra_singleton()

if __name__ == "__main__":
    init_astra()