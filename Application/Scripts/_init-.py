from .init_postgres import init_postgres
from .init_neo4j import init_neo4j
from .init_astra import init_astra

def init_all():
    print("Initializing PostgreSQL...")
    init_postgres()

    print("Initializing Neo4j...")
    init_neo4j()

    print("Initializing AstraDB...")
    init_astra()

    print("All databases initialized successfully!")

if __name__ == "__main__":
    init_all()