import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

# Load from project root .env
env_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(env_path)

def test_connection():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    print(f"Connecting to {uri}...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✅ Neo4j Aura connection successful!")
        driver.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()