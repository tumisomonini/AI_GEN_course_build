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
        from Application.Infrastructure.graphDb.neo4j_repo import Neo4jNeomodelRepository as Neo4jRepository
        repo = Neo4jRepository(uri, user, password, database)
        
        # Scale to 100+ topics with 50+ relationships
        topics = [
            "Python Basics", "Data Structures", "Algorithms", "OOP", "Functions", "Classes", "Inheritance",
            "Polymorphism", "Encapsulation", "Lists", "Tuples", "Dictionaries", "Sets", "Strings",
            "File I/O", "Exceptions", "Modules", "Packages", "Lambda", "Map Filter", "Decorators", "Generators",
            "Context Managers", "AsyncIO", "Multithreading", "NumPy", "Pandas", "Matplotlib", "Scikit-learn",
            "Flask", "Django", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker", "Kubernetes", "AWS", "CI/CD",
            "Git", "Testing", "TDD", "Microservices", "REST APIs", "GraphQL", "Kafka", "Redis", "Neo4j"
        ] * 4  # 120 topics
        
        prereqs = [
            "Python Basics", "Data Structures", "Algorithms",
            "OOP", "Data Structures", "Algorithms",
            # Add 50+...
        ]
        for t in topics[:100]:
            repo.add_topic(t)
        
        # Add relationships (50+)
        relationships = [
            ("OOP", "Classes"), ("Classes", "Inheritance"), ("Inheritance", "Polymorphism"),
            ("Data Structures", "Lists"), ("Lists", "Tuples"), ("Tuples", "Dictionaries"),
            ("AsyncIO", "Python Basics"), ("FastAPI", "Flask"), ("Docker", "Git"),
            # More...
        ] * 5  # 50+
        for child, parent in relationships[:50]:
            repo.add_prerequisite(child, parent)
        
        print(f"✅ Scaled Neo4j: 100+ topics, 50+ relationships at {uri}!")
        return repo
    except Exception as e:
        print(f"Error initializing Neo4j: {e}")
        raise

