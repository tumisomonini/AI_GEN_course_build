from neomodel import db
from neomodel.exceptions import DoesNotExist as NeoDoesNotExist
from typing import List, Optional
import os
from .models import Topic, Course

class Neo4jNeomodelRepository:
    def __init__(self, uri: str, user: str, password: str, database: Optional[str] = None):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database or "neo4j"
        db.set_connection(driver=self.driver)
        # install_labels(Topic)  # Removed in neomodel 6.x
    
    def add_topic(self, topic: str):
        Topic.get_or_create({'name': topic})
    
    def add_prerequisite(self, topic: str, prerequisite: str):
        try:
            t1 = Topic.nodes.get(name=topic)
            t2 = Topic.nodes.get_or_create({'name': prerequisite})[0]
            t1.prerequisites.connect(t2)
        except NeoDoesNotExist:
            pass
    
    def get_prerequisites(self, topic: str) -> List[str]:
        try:
            t = Topic.nodes.get(name=topic)
            return [p.name for p in t.prerequisites.all()]
        except NeoDoesNotExist:
            return []
    
    def close(self):
        self.driver.close()
    
    # Additional for KnowledgeGraph compatibility
    def get_all_topics(self) -> List[dict]:
        return [{'name': t.name, 'description': t.description} for t in Topic.nodes.all()]

    def link_topics_to_course(self, course_id: int, title: str, topic_names: List[str]):
        """Link topics to Course node via HAS_TOPIC relationship."""
        try:
            course = Course.get_or_create({'course_id': course_id, 'title': title})[0]
            for topic_name in topic_names:
                topic = Topic.get_or_create({'name': topic_name})[0]
                course.topics.connect(topic)  # type: ignore[union-attr]
            print(f"✅ Linked course {course_id} to topics: {topic_names}")
        except Exception as e:
            print(f"❌ Link topics failed: {e}")
            raise
