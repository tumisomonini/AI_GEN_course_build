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

print("🚀 Populating all databases via TripleDBManager...")

from Application.Ports.triple_db_manager import TripleDBManager
from Application.API.dependencies import get_triple_db_manager

try:
    manager = get_triple_db_manager()
    course_id = manager.create_linked_course("TripleDB Integration Test Course", "developers")
    print(f"✅ Triple integration: Created & linked course_id={course_id} across PG+Neo4j+Astra")
except Exception as e:
    print(f"❌ TripleDBManager failed: {e}")
    print("💡 Ensure all DBs healthy: cd Application/Docker && docker compose up -d")

# 4. Redis Ping
print("📡 Pinging Redis...")
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    r.set("health:populate", "triple_ok")
    print(f"✅ Redis healthy (set key: {r.get('health:populate')}")
except:
    print("⚠️ Redis optional skipped")

print("🎉 TripleDB integration complete!")
