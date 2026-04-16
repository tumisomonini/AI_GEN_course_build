#!/usr/bin/env python3
"""Test data loader for RAG testing."""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from Application.Ports.scraper import scrape_relevant_syllabi
from Application.Ports.Astra_repo import AstraRepo
from Application.Infrastructure.graphDb.neo4j_repo import Neo4jRepository

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

def load_test_data(course_title: str):
    print(f'Loading test data for \\"{course_title}\\"')
    
    # 1. Scrape syllabi
    syllabi = scrape_relevant_syllabi(course_title, max_results=3)
    print(f'Found {len([s for s in syllabi if "error" not in s])} syllabi')
    
    # 2. Flatten to chunks for Astra
    all_texts = []
    all_metadatas = []
    for syllabus in syllabi:
        if 'error' not in syllabus:
            for section, chunks in syllabus.items():
                if isinstance(chunks, list):
                    for chunk in chunks:
                        all_texts.append(chunk)
                        all_metadatas.append({
                            'course_title': course_title,
                            'section': section,
                            'type': 'test_rag_chunk',
                            'source': syllabus.get('source_url', '')
                        })
    
    # Upsert to Astra test collection
    if all_texts:
        astra_repo = AstraRepo('course_chunks')
        astra_repo.upsert_syllabus_chunks(all_texts[:50], all_metadatas[:50])  # limit
        print(f'✅ Upserted {len(all_texts[:50])} chunks to Astra course_chunks')
    else:
        print('⚠️ No texts to upsert - scraper may have failed')
    
    # 3. Populate Neo4j with basic topics
    neo4j_uri = 'bolt://localhost:7687'
    neo4j_user = 'neo4j'
    neo4j_pass = 'password'
    repo = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_pass)
    topics = ['Introduction', 'Machine Learning Basics', 'Neural Networks']
    for topic in topics:
        repo.add_topic(topic)
        repo.add_prerequisite(topic, 'Introduction')  # dummy prereq
    repo.close()
    print('✅ Populated Neo4j with test topics graph')
    
    print('Test data loaded! Ready for RAG tests.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--course', default='Introduction to Machine Learning', help='Course title to scrape')
    args = parser.parse_args()
    load_test_data(args.course)
