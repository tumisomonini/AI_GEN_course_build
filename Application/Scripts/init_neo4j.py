"""Neo4j initialization module."""
import os
from pathlib import Path
from dotenv import load_dotenv

_ENV = Path(__file__).resolve().parents[2] / '.env'

def init_neo4j():
    load_dotenv(_ENV)
    # Use local Docker Neo4j (existing course_neo4j container)
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password"  # Change if different
    database = None

    try:
        from Application.Infrastructure.graphDb.neo4j_repo import Neo4jRepository
        repo = Neo4jRepository(uri, user, password, database)
        print(f"Neo4j database initialized successfully at {uri}!")
        return repo
    except Exception as e:
        print(f"Error initializing Neo4j: {e}")
        raise
