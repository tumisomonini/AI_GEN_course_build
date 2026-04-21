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

from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository
from Application.Ports.Astra_repo import AstraRepo
import redis

print("🚀 Populating all databases...")

# 1. Postgres Schema
print("📊 Initializing Postgres...")
pg = PostgresRepo()
pg.init_schema()
print("✅ Postgres schema ready")

# 2. Neo4j Samples
print("🧠 Populating Neo4j...")
uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USERNAME', 'neo4j')
pwd = os.getenv('NEO4J_PASSWORD', 'password')
neo = Neo4jRepository(uri, user, pwd)
neo.add_topic("Machine Learning")
neo.add_topic("Neural Networks")
neo.add_prerequisite("Neural Networks", "Machine Learning")
neo.close()
print("✅ Neo4j populated")

# 3. Astra Test Data
print("🔍 Adding Astra test chunks...")
if os.getenv("ASTRA_DB_APPLICATION_TOKEN"):
    astra = AstraRepo("course_chunks")
    astra.upsert_syllabus_chunks(
        ["Test chapter on Python basics.", "Data structures list dict set."],
        [{"test": True}, {"test": True}]
    )
    print("✅ Astra test data added")
else:
    print("⚠️ Astra skipped (no token)")

# 4. Redis Ping
print("📡 Pinging Redis...")
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
r.ping()
r.set("health:populate", "ok")
print(f"✅ Redis healthy (set key: {r.get('health:populate')}")

print("🎉 All databases populated!")

