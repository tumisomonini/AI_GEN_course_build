import os
from dotenv import load_dotenv
from Application.Infrastructure.graphDb.neo4j_repo import Neo4jRepository
from Application.Scripts.scrape_syllabus import scrape_and_structure

def populate_neo4j(url: str = None, file_path: str = None):
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE")

    structured_syllabus = scrape_and_structure(url, file_path)
    repo = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
    populate_from_structured(repo, structured_syllabus)


def populate_from_template(repo: Neo4jRepository, title: str, chapters: list, prerequisites: list):
    """Populate Neo4j from a generated course template."""
    repo.add_topic(title)
    for prereq in prerequisites:
        repo.add_prerequisite(title, prereq)
    prev_chapter = title
    for chapter in chapters:
        chapter_title = chapter.get("title", "")
        if not chapter_title:
            continue
        repo.add_topic(chapter_title)
        repo.add_prerequisite(chapter_title, prev_chapter)
        prev_chapter = chapter_title


def populate_from_structured(repo: Neo4jRepository, structured_syllabus: dict):
    """Populate Neo4j from a scraped and structured syllabus dict."""
    sections = list(structured_syllabus.keys())
    for i, section in enumerate(sections):
        repo.add_topic(section)
        if i > 0:
            repo.add_prerequisite(section, sections[i - 1])

if __name__ == "__main__":
    populate_neo4j(url="https://example.edu/course-syllabus")
