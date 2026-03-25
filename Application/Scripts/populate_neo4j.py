from infrastructure.graph.neo4j_repo import Neo4jRepository
from scripts.scrape_syllabus import scrape_and_structure

def populate_neo4j(neo4j_uri: str, neo4j_user: str, neo4j_password: str, url: str = None, file_path: str = None):
    structured_syllabus = scrape_and_structure(url, file_path)
    repo = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_password)
    for section, content in structured_syllabus.items():
        repo.add_topic(section)
        for item in content:
            if "Prerequisite:" in item:
                prereq = item.replace("Prerequisite:", "").strip()
                repo.add_prerequisite(section, prereq)

if __name__ == "__main__":
    populate_neo4j(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        url="https://example.edu/course-syllabus"
    )