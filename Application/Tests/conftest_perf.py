import pytest

try:
    # Shared initializer used by the performance script
    from Application.Scripts.init_postgres import init_postgres
except Exception:  # pragma: no cover
    init_postgres = None


@pytest.fixture(scope="session")
def pg():
    """Performance-test Postgres fixture.

    The performance tests in `Application/Scripts/perf_test.py` are intended to
    run only when an external Postgres service is available. In typical unit
    test runs, we skip these tests to avoid hard dependency on infrastructure.
    """
    if init_postgres is None:
        pytest.skip("init_postgres() unavailable")

    # If user explicitly wants perf tests, they can enable by setting this flag.
    # Otherwise, skip during standard `pytest`.
    import os

    enabled = os.getenv("RUN_PERF_TESTS", "0") == "1"
    if not enabled:
        pytest.skip("Skipping perf tests (set RUN_PERF_TESTS=1 to enable)")

    pg = init_postgres()
    try:
        yield pg
    finally:
        try:
            pg.close()
        except Exception:
            pass


