import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

class PostgresRepo:
    """Env-aware Postgres repository adapter (like AstraRepo)."""
    
    def __init__(self):
        # Inside Docker network, use the service name. Outside, use localhost.
        is_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"
        
        # If POSTGRES_HOST is not set, use service name 'postgres' in docker, else 'localhost'
        host = os.getenv('POSTGRES_HOST', 'postgres' if is_docker else 'localhost')
        port = int(os.getenv('POSTGRES_PORT', '5432' if is_docker else '5433'))
        
        # Internal port is 5432, but host-mapped port in your docker-compose is 5433
        default_port = '5432' if is_docker else '5433'
        port = int(os.getenv('POSTGRES_PORT', default_port))
        
        dbname = os.getenv('POSTGRES_DBNAME', 'ai_gen_db')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'password123')
        
        self.repo = PostgresRepository(dbname, user, password, host, port)
        try:
            self.repo.init_schema()
        except Exception as e:
            print(f"⚠️ Schema init skipped (already exists): {e}")
        print(f"PostgresRepo connected: {host}:{port}/{dbname}")
    
    def __getattr__(self, name):
        """Delegate all methods to underlying PostgresRepository."""
        return getattr(self.repo, name)
    
    def close(self):
        self.repo.close()
    
    def init_schema(self):
        """Ensure schema is initialized."""
        self.repo.init_schema()
