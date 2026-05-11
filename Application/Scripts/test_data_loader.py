#!/usr/bin/env python3
"""Test data loader for RAG system: scrape → Astra upsert → Neo4j topics"""
import argparse
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


from Application.Ports.scraper import scrape_relevant_syllabi
from Application.Ports.neo4j_repo import Neo4jRepository
from Application.Ports.Astra_repo import AstraRepo
from Domain.syllabus import Syllabus
from Domain.course import Chapter

def load_test_data(course_query: str = "Introduction to Machine Learning"):
    print(f"🚀 Loading test data for: {course_query}")
    
    # 1. Scrape syllabus
    print("🔍 Scraping syllabi...")
    syllabi_raw = scrape_relevant_syllabi(course_query)
    if not syllabi_raw or 'error' in syllabi_raw[0]:
        print("❌ No syllabi found, using mock data")
        # Domain.Syllabus requires both `title` and `course`.
        # Domain.Course is a Pydantic model.
        from Domain.course import Course

        syllabus = Syllabus(
            title="Mock ML Syllabus",
            course=Course(title="Mock ML Syllabus", audience="general", outcomes=[]),
            chapters=[
                Chapter(title="Intro", content="Machine learning basics: supervised, unsupervised..."),
                Chapter(title="Neural Nets", content="Backpropagation, layers, activation functions...")
            ],
        )
    else:
        syllabus = Syllabus.from_scraped_dict(syllabi_raw[0])
    
    # 2. Upsert to Astra for RAG
    print("📤 Upserting to AstraDB...")
    astra_repo = AstraRepo(collection_name="rag_test_chunks")
    texts = [ch.content for ch in syllabus.chapters if ch.content]
    metadatas = [{"course": course_query, "chapter": ch.title} for ch in syllabus.chapters]
    astra_repo.upsert_syllabus_chunks(texts, metadatas)
    print(f"✅ {len(texts)} chunks in AstraDB")
    
    # 3. Add topics to Neo4j (for planner)
    print("🗺️ Adding to Neo4j...")
    neo4j_repo = Neo4jRepository(
        uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        user=os.getenv('NEO4J_USER') or '',
        password=os.getenv('NEO4J_PASSWORD') or '',
        database=os.getenv('NEO4J_DATABASE', 'neo4j')
    )
    topics = [ch.title for ch in syllabus.chapters]
    for topic in topics:
        # Neo4j port supports `add_topic`.
        # This script is for seeding topic nodes for planning.
        neo4j_repo.add_topic(topic)
    print(f"✅ {len(topics)} topics in Neo4j")
    
    print("✅ Test data loaded! Ready for RAG testing.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test data for RAG")
    parser.add_argument("--course", default="Introduction to Machine Learning")
    args = parser.parse_args()
    load_test_data(args.course)
