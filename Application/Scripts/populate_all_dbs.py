#!/usr/bin/env python3
"""
Populate all databases: Postgres schema, Neo4j samples, Astra test data, Redis ping.
Run: python Application/Scripts/populate_all_dbs.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

load_dotenv()

from Application.API.dependencies import sanitize_neo4j_uri
from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository
import redis

print("🚀 Populating all databases...")

# 1. Postgres Schema
print("📊 Initializing Postgres...")
pg = PostgresRepo()
try:
    pg.init_schema()
except Exception as e:
    print(f"⚠️ Schema already exists: {e}")
print("✅ Postgres ready")

# 2. Neo4j Samples
print("🧠 Populating Neo4j with PG link...")
raw_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
uri = sanitize_neo4j_uri(raw_uri)
user = os.getenv('NEO4J_USERNAME', 'neo4j')
pwd = os.getenv('NEO4J_PASSWORD', 'password')
database = os.getenv('NEO4J_DATABASE', 'neo4j')
neo = Neo4jRepository(uri, user, pwd, database)

# Wait for Neo4j readiness
import time
for attempt in range(30):
    try:
        with neo.driver.session(database=database) as session:
            session.run("RETURN 1").single()
        print(f"✅ Neo4j connection verified at {uri}")
        break
    except Exception as e:
        if attempt % 5 == 0:
            print(f"⏳ Waiting for Neo4j ({uri})... Error: {str(e)[:50]}...")
        time.sleep(2)
else:
    raise RuntimeError("Neo4j not ready after 60s")

# Create sample course in PG
course_title = "Sample AI Course - PG-Neo4j Link"
course_id = pg.create_course(course_title, audience="ML Engineers")
print(f"Created PG course_id={course_id}: {course_title}")

# Add topics
neo.add_topic("Machine Learning")
neo.add_topic("Neural Networks")
neo.add_prerequisite("Neural Networks", "Machine Learning")

# Link PG course_id to Neo4j topics
with neo._session() as session:
    session.run(
        """
        MERGE (c:Course {course_id: $course_id})
        WITH c
        MATCH (t:Topic {name: 'Machine Learning'})
        MERGE (c)-[:HAS_TOPIC]->(t)
        WITH c
        MATCH (t2:Topic {name: 'Neural Networks'})
        MERGE (c)-[:HAS_TOPIC]->(t2)
        RETURN 1
        """,
        course_id=course_id
    )

neo.close()
print(f"✅ Neo4j populated & linked to PG course_id={course_id}")

# 3. Astra Test Data
print("🔍 Populating Astra with sample data...")
try:
    from Application.Ports.Astra_repo import AstraRepo
    repo = AstraRepo()
    sample_texts = [
        "Introduction to Machine Learning: Supervised vs unsupervised learning.",
        "Neural Networks Basics: Layers, activation functions, backpropagation.",
        "Sample syllabus chunk 3: Transformers and attention mechanisms."
    ]
    sample_metadatas = [
        {"course": "ML Basics", "section": "Intro", "type": "sample"},
        {"course": "ML Basics", "section": "NN", "type": "sample"},
        {"course": "ML Basics", "section": "Advanced", "type": "sample"}
    ]
    repo.upsert_syllabus_chunks(sample_texts, sample_metadatas)
    results = repo.similarity_search("neural", k=1)
    print(f"✅ Astra populated & verified: {len(results)} relevant chunks")
except Exception as e:
    print(f"⚠️ Astra population skipped: {e}")

# 4. Redis Ping
print("📡 Pinging Redis...")
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
r.ping()
r.set("health:populate", "ok")
print(f"✅ Redis healthy (set key: {r.get('health:populate')}")

print("🎉 All databases populated!")
