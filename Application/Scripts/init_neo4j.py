"""Neo4j initialization module."""
import os
from dotenv import load_dotenv

def init_neo4j():
    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE")

    try:
        from Application.Infrastructure.graphDb.neo4j_repo import Neo4jRepository
        repo = Neo4jRepository(uri, user, password, database)
        print(f"Neo4j database initialized successfully at {uri}!")
        return repo
    except Exception as e:
        print(f"Error initializing Neo4j: {e}")
        raise
