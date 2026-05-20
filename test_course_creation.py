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
    # Allow overrides via env vars; otherwise use the historical defaults.
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5433"))
    dbname = os.getenv("POSTGRES_DBNAME", "ai_gen_db")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password123")
    return host, port, dbname, user, password


def test_course_creation_smoke():
    host, port, dbname, user, password = _configured_postgres()

    if not _is_port_open(host, port):
        pytest.skip(f"Postgres not reachable at {host}:{port}")

    from Application.Infrastructure.relationalDB.postgres_orm_repo import (
        PostgresORMRepository,
    )

    try:
        # PostgresORMRepository historically reads config from env.
        # We set env vars here so it behaves deterministically.
        os.environ["POSTGRES_HOST"] = host
        os.environ["POSTGRES_PORT"] = str(port)
        os.environ["POSTGRES_DBNAME"] = dbname
        os.environ["POSTGRES_USER"] = user
        os.environ["POSTGRES_PASSWORD"] = password

        repo = PostgresORMRepository()
        course_id = repo.create_course(
            title="Test Course Schema Fix",
            audience="general",
            description="Schema fix test",
            created_by=1,
        )
        status = repo.get_course_status(course_id)
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "too many clients" in msg or "connection to server" in msg:
            pytest.skip(f"Postgres refused connection: {e}")
        raise

    assert course_id is not None
    assert status is not None

