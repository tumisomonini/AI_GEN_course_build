from .init_postgres import init_postgres
from .init_neo4j import init_neo4j
from .init_astra import init_astra

def init_all():
    print("Initializing PostgreSQL...")
    init_postgres("course_db", "postgres", "postgres")

    print("Initializing Neo4j...")
    init_neo4j("bolt://localhost:7687", "neo4j", "password")

    print("Initializing AstraDB...")
    init_astra(
        collection_name="course_chunks",
        astra_token="your_astra_token",
        astra_api_endpoint="https://your_astra_api_endpoint"
    )

    print("All databases initialized successfully!")

if __name__ == "__main__":
    init_all()