#!/usr/bin/env python3
"""Pre-compute embeddings for common course syllabi to accelerate cold starts."""

import asyncio
from Application.Ports.scraper import scrape_relevant_syllabi
from Application.API.dependencies import get_triple_db_manager
from Application.Infrastructure.ETL.cleaner import log_cleaning_stats

COMMON_COURSES = [
    "Python", "Machine Learning", "Data Science", "Web Development", 
    "Deep Learning", "React", "Docker", "AWS", "SQL", "DevOps"
]

async def precompute():
    manager = get_triple_db_manager()
    astra = manager.astra
    if not astra:
        print("⚠️ Astra unavailable - skipping precompute")
        return
    
    all_texts, all_metas = [], []
    
    for course in COMMON_COURSES:
        print(f"Pre-scraping {course}...")
        syllabi = scrape_relevant_syllabi(course, max_results=2)
        for syllabus in syllabi[:2]:
            if 'error' not in syllabus:
                for topic in syllabus.get('main_topics', [])[:5]:
                    text = str(topic)[:1500]
                    if text:
                        all_texts.append(text)
                        all_metas.append({
                            'course_title': course,
                            'section': str(topic)[:100],
                            'type': 'precomputed_syllabus',
                            'precomputed': True
                        })
    
    if all_texts:
        print(f"Upserting {len(all_texts)} precomputed chunks...")
        astra.upsert_syllabus_chunks(all_texts, all_metas)
        print("✅ Pre-compute complete!")
    else:
        print("No chunks to pre-compute")

if __name__ == "__main__":
    asyncio.run(precompute())
