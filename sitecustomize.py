"""Test runner helper.

Ensure the repository root is on sys.path so imports like `import Application`
work regardless of the current working directory.

Python automatically imports `sitecustomize` at interpreter startup if it is
present on sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

