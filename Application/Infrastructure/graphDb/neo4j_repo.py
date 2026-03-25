from neo4j import GraphDatabase
from typing import List

class Neo4jRepository:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def add_topic(self, topic: str):
        with self.driver.session() as session:
            session.run("MERGE (t:Topic {name: $topic})", topic=topic)

    def add_prerequisite(self, topic: str, prerequisite: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (a:Topic {name: $topic})
                MATCH (b:Topic {name: $prerequisite})
                MERGE (a)-[:PREREQUISITE]->(b)
                """,
                topic=topic,
                prerequisite=prerequisite
            )

    def get_prerequisites(self, topic: str) -> List[str]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (a:Topic {name: $topic})-[:PREREQUISITE]->(b:Topic)
                RETURN b.name AS prerequisite
                """,
                topic=topic
            )
            return [record["prerequisite"] for record in result]