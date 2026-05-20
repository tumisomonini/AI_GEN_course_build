#!/usr/bin/env python3

import os
import socket

import pytest


def _is_port_open(host: str, port: int, timeout_s: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _configured_postgres() -> tuple[str, int, str, str, str]:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5433"))
    dbname = os.getenv("POSTGRES_DBNAME", "ai_gen_db")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password123")
    return host, port, dbname, user, password


def test_raw_course_creation_smoke():
    host, port, dbname, user, password = _configured_postgres()

    # If DB isn't reachable, skip instead of failing during collection.
    if not _is_port_open(host, port):
        pytest.skip(f"Postgres not reachable at {host}:{port}")

    from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

    # Some CI/dev environments have the port open but DB refuses connections
    # (e.g., too many clients). Treat those cases as a skip.
    try:
        repo = PostgresRepository(dbname, user, password, host, port)
        course_id = repo.create_course(
            title="Test Raw SQL Schema Fix",
            audience="general",
            description="Raw SQL test",
            created_by=None,
        )
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "too many clients" in msg or "connection to server" in msg:
            pytest.skip(f"Postgres refused connection: {e}")
        raise

    assert course_id is not None

