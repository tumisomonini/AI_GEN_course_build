from neo4j import GraphDatabase
from .neo4j_repo import Neo4jRepository
from typing import List

__all__ = ["init_graphdb"]

def init_graphdb(uri: str, user: str, password: str):
    """Non-defensively initialize Neo4j graph DB: create constraints and sample data."""
    repo = Neo4jRepository(uri, user, password)
    cypher = """
-- Create constraints
CREATE CONSTRAINT unique_topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;

-- Sample data
CREATE (t1:Topic {name: "Introduction to Python"})
CREATE (t2:Topic {name: "Advanced Python"})
CREATE (t3:Topic {name: "Data Structures"})
CREATE (t1)-[:PREREQUISITE]->(t2)
CREATE (t2)-[:PREREQUISITE]->(t3)
    """
    with repo.driver.session() as session:
        session.run(cypher)
    repo.close()

