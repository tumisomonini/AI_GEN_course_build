from neo4j import GraphDatabase
from typing import List, Optional
import tenacity
from tenacity import retry, stop_after_attempt, wait_fixed

class Neo4jRepository:
    def __init__(self, uri: str, user: str, password: str, database: Optional[str] = None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def _session(self):
        return self.driver.session(database=self.database) if self.database else self.driver.session()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def add_topic(self, topic: str):
        with self._session() as session:
            session.run("MERGE (t:Topic {name: $topic})", topic=topic, timeout=10.0)

    def add_prerequisite(self, topic: str, prerequisite: str):
        with self._session() as session:
            session.run(
                """
                MATCH (a:Topic {name: $topic})
                MATCH (b:Topic {name: $prerequisite})
                MERGE (a)-[r:PREREQUISITE]->(b)
                """,
                topic=topic,
                prerequisite=prerequisite
            )

    def get_prerequisites(self, topic: str) -> List[str]:
        with self._session() as session:
            result = session.run(
                """
                MATCH (a:Topic {name: $topic})-[r:PREREQUISITE]->(b:Topic)
                RETURN b.name AS prerequisite
                """,
                topic=topic
            )
            return [record["prerequisite"] for record in result]

    def close(self):
        self.driver.close()
