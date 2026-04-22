"""Neo4j initialization module with Docker auto-start and .env fallback."""
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

_ENV = Path(__file__).resolve().parents[2] / '.env'

def ensure_neo4j_docker():
    """Ensure Neo4j Docker service is running."""
    docker_dir = Path(__file__).resolve().parents[3] / "Application/Docker"
    try:
        # Check if neo4j is specifically 'running' or 'healthy'
        result = subprocess.run(
            ["docker-compose", "ps", "-q", "neo4j", "--filter", "status=running"],
            cwd=docker_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        # If the output is empty, the container is not running
        if not result.stdout.strip():
            print("🚀 Starting Neo4j Docker...")
            subprocess.run(["docker-compose", "up", "-d", "neo4j"], cwd=docker_dir, check=True)
            print("⏳ Waiting for Neo4j healthy...")
            try:
                subprocess.run(["docker-compose", "logs", "-f", "neo4j"], cwd=docker_dir, timeout=30)
            except subprocess.TimeoutExpired:
                print("✅ Log stream ended (Neo4j initialization continuing in background)")
        else:
            print("✅ Neo4j Docker container is already running")
    except Exception as e:
        print(f"⚠️ Docker check failed: cd Application/Docker && docker-compose up -d neo4j\nError: {e}")

def init_neo4j():
    load_dotenv(_ENV)
    uri = os.getenv("NEO4J_URI")
    if not uri:
        print("⚠️ No NEO4J_URI in .env, using local Docker fallback")
        uri = "bolt://localhost:7687"
        os.environ["NEO4J_URI"] = uri  # For Ports layer
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    from Application.API.dependencies import sanitize_neo4j_uri
    uri = sanitize_neo4j_uri(uri)

    ensure_neo4j_docker()
    try:
        from Application.Infrastructure.graphDb.neo4j_repo import Neo4jRepository
        repo = Neo4jRepository(uri, user, password, database)
        print(f"Neo4j database initialized successfully at {uri}!")
        return repo
    except Exception as e:
        print(f"Error initializing Neo4j: {e}")
        raise
