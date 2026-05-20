
"""
This file is intentionally **not** collected/executed by default unit tests.
Use `Application/Tests/conftest_perf.py` with `RUN_PERF_TESTS=1` to run the
perf tests in a controlled manner.
"""

import asyncio

import pytest


# Prevent accidental pytest collection/runs.
pytest.skip(
    "perf_test.py is a manual performance harness; run perf tests via "
    "Application/Tests/conftest_perf.py with RUN_PERF_TESTS=1",
    allow_module_level=True,
)


async def main() -> None:
    # Kept as a placeholder so the script remains valid if someone runs it
    # directly with python.
    raise SystemExit(
        "This module is skipped under pytest. Run the perf tests from "
        "Application/Tests/conftest_perf.py instead.",
    )


if __name__ == "__main__":
    asyncio.run(main())
