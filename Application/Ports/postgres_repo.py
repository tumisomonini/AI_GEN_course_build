import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from Application.Infrastructure.relationalDB.postgres_orm_repo import PostgresORMRepository

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

class PostgresRepo:
    """Env-aware Postgres repository adapter (like AstraRepo)."""
    
    def __init__(self):
        # Inside Docker network, use the service name. Outside, use localhost.
        is_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"
        
        host = os.getenv('POSTGRES_HOST', 'postgres' if is_docker else 'localhost').strip()
        # Default to 5432 (standard) in Docker, or 5433 (mapped) on host
        port = int(os.getenv('POSTGRES_PORT', '5432' if is_docker else '5433').strip())
        
        dbname = os.getenv('POSTGRES_DBNAME', 'ai_gen_db')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'password123')
        
        self.repo = PostgresORMRepository()
        print(f"PostgresRepo connected: {host}:{port}/{dbname}")
    
    def ensure_schema(self):
        """Manual trigger for schema initialization if not using Alembic."""
        self.repo.init_schema()

    def __getattr__(self, name):
        """Delegate all methods to underlying PostgresRepository."""
        return getattr(self.repo, name)
    
    def close(self):
        self.repo.close()
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def init_schema(self):
        """Ensure schema is initialized."""
        self.repo.init_schema()
