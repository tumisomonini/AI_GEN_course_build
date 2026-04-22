"""PostgreSQL initialization module with Docker auto-start."""

import subprocess
import os
from pathlib import Path

def ensure_postgres_docker():
    """Ensure Postgres Docker service is running."""
    docker_dir = Path(__file__).resolve().parents[3] / "Application/Docker"
    try:
        # Check if postgres healthy
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "name=postgres", "--filter", "status=healthy"],
            cwd=docker_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("🚀 Starting Postgres Docker...")
            subprocess.run(["docker-compose", "up", "-d", "postgres"], cwd=docker_dir, check=True)
            print("⏳ Waiting for Postgres healthy...")
            subprocess.run(["docker-compose", "logs", "-f", "postgres"], cwd=docker_dir, timeout=60)
        else:
            print("✅ Postgres Docker healthy")
    except Exception as e:
        print(f"⚠️ Docker check failed (run manually): cd Application/Docker && docker-compose up -d postgres\nError: {e}")

def init_postgres(db_name: str = None, user: str = None, password: str = None):
    """Initialize PostgreSQL database using Ports layer."""
    ensure_postgres_docker()
    try:
        from Application.Ports.postgres_repo import PostgresRepo
        repo = PostgresRepo()
        repo.init_schema()
        print("✅ PostgreSQL initialized successfully!")
        return repo
    except Exception as e:
        print(f"❌ Error initializing PostgreSQL: {e}")
        raise
