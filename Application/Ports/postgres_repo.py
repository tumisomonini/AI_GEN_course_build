import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

class PostgresRepo:
    """Env-aware Postgres repository adapter (like AstraRepo)."""
    
    def __init__(self):
        host = os.getenv('POSTGRES_HOST', 'localhost')
        # Default to 5433 as per Docker Compose setup for this project
        port = int(os.getenv('POSTGRES_PORT', 5433))
        dbname = os.getenv('POSTGRES_DBNAME', 'ai_gen_db')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'password123')
        
        self.repo = PostgresRepository(dbname, user, password, host, port)
        self.repo.init_schema()
    
    def __getattr__(self, name):
        """Delegate all methods to underlying PostgresRepository."""
        return getattr(self.repo, name)
    
    def close(self):
        self.repo.close()
    
    def init_schema(self):
        """Ensure schema is initialized."""
        self.repo.init_schema()
