from neomodel import StructuredNode, StringProperty, DateTimeProperty, Relationship, IntegerProperty, ZeroOrMore
from typing import List, Optional
from datetime import datetime

class Course(StructuredNode):
    course_id = IntegerProperty(unique_index=True, required=True)
    title = StringProperty(required=True)
    created_at = StringProperty(default=lambda: datetime.utcnow().isoformat())

    # Relationships
    topics = Relationship('Topic', 'HAS_TOPIC', cardinality=ZeroOrMore)

class Topic(StructuredNode):
    name = StringProperty(unique_index=True, max_length=255)
    description = StringProperty(default='')
    created_at = StringProperty(default=lambda: datetime.utcnow().isoformat())
    updated_at = StringProperty(default=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    prerequisites = Relationship('Topic', 'PREREQUISITE', cardinality=ZeroOrMore)
    dependents = Relationship('Topic', 'PREREQUISITE', cardinality=ZeroOrMore)
    
    # Related
    related_to = Relationship('Topic', 'RELATED_TO', cardinality=ZeroOrMore)
