from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Application.Ports.neo4j_repo import Neo4jRepository

def link_course_to_graph(course_id: int, neo_repo: 'Neo4jRepository', title: str = None):
    """
    Link PG course_id to Neo4j topics (call after course create + syllabus gen).
    """
    from Application.Ports.postgres_repo import PostgresRepo
    pg = PostgresRepo()
    if title is None:
        status = pg.get_course_status(course_id)
        title = status.get('title', f'Course {course_id}')
    
    with neo_repo._session() as session:
        session.run(
            """
            MERGE (c:Course {course_id: $course_id, title: $title})
            RETURN c
            """,
            course_id=course_id, title=title
        )
        # Link to existing topics (assumes syllabus topics added)
        session.run(
            """
            MATCH (c:Course {course_id: $course_id})
            MATCH (t:Topic)
            WHERE NOT (c)-[:HAS_TOPIC]->(t)
            MERGE (c)-[:HAS_TOPIC]->(t)
            LIMIT 5  # Sample link
            """,
            course_id=course_id
        )
    print(f"✅ Linked course_id={course_id} '{title}' to Neo4j graph")
