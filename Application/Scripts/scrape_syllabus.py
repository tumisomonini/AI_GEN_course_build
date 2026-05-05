from typing import Dict, List, Optional
import os
import argparse
from utils.env_loader import load_root_env

load_root_env()
from Application.Ports.Astra_repo import AstraRepo
from Application.Infrastructure.ETL.cleaner import clean_raw_text, clean_syllabus_dict, log_cleaning_stats
from Application.Infrastructure.Scraper.web_scraper import scrape_web_syllabus
from Application.Infrastructure.Scraper.pdf_scraper import scrape_pdf_syllabus
from Application.Ports.scraper import parse_syllabus, scrape_relevant_syllabi
from Domain.syllabus import Syllabus
from Domain.course import Course

def scrape_and_structure(url: Optional[str] = None, file_path: Optional[str] = None, query: Optional[str] = None) -> Syllabus:
    if query:
        syllabi = scrape_relevant_syllabi(query)
        # Find top quality dict result and convert to Domain model
        top_dict = next((s for s in syllabi if not s.get('error') and s.get('quality_score', 0) > 0), None)
        if top_dict:
            structured = Syllabus.from_scraped_dict(top_dict)
        else:
            structured = Syllabus(title="No syllabus found", course=Course(title="Empty", audience="general", outcomes=[]), chapters=[])
    elif url:
        cleaned_raw, raw_stats = clean_raw_text(scrape_web_syllabus(url))
        log_cleaning_stats(raw_stats, 'raw')
        structured_dict = parse_syllabus(cleaned_raw)
        cleaned_struct, struct_stats = clean_syllabus_dict(structured_dict)
        structured = Syllabus.from_scraped_dict(cleaned_struct)
    elif file_path:
        cleaned_raw, raw_stats = clean_raw_text(scrape_pdf_syllabus(file_path))
        log_cleaning_stats(raw_stats, 'raw')
        structured_dict = parse_syllabus(cleaned_raw)
        cleaned_struct, struct_stats = clean_syllabus_dict(structured_dict)
        structured = Syllabus.from_scraped_dict(cleaned_struct)
    else:
        raise ValueError("Provide --url, --file, or --query")
    print("Structured Domain syllabus:", structured.model_dump())
    return structured

def upsert_syllabus_chunks_to_astra(structured_syllabus: 'Syllabus', source: str, collection_name: str = "syllabus_chunks"):
    """Upsert Domain Syllabus chapters to AstraDB"""
    texts = [ch.content for ch in structured_syllabus.chapters if ch.content.strip()]
    metadatas = [{"source": source, "section": ch.title, "type": "domain_syllabus_chunk"} for ch in structured_syllabus.chapters]
    
    if not texts:
        print("No valid chunks to upsert.")
        return
    
    try:
        astra_repo = AstraRepo(collection_name)
        astra_repo.upsert_syllabus_chunks(texts[:200], metadatas[:200])  # Limit to 200 chunks
        print(f"✅ Successfully upserted {len(texts[:200])} syllabus chunks to AstraDB '{collection_name}'!")
    except Exception as e:
        print(f"❌ Failed to upsert to AstraDB: {str(e)}")
        print("Ensure ASTRA_TOKEN, ASTRA_DB_ID env vars are set.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape syllabus and optionally store chunks in AstraDB")
    parser.add_argument("--url", type=str, help="Syllabus URL to scrape")
    parser.add_argument("--file", type=str, help="Local PDF file path")
    parser.add_argument("--query", type=str, help="Course title/query for dynamic syllabus search")
    parser.add_argument("--collection", type=str, default="syllabus_chunks", help="AstraDB collection name")
    
    args = parser.parse_args()
    
    if not (args.url or args.file or args.query):
        print("Error: Provide --url, --file, or --query")
        exit(1)
    
    source: str = args.query or args.url or args.file or "unknown"
    structured_syllabus = scrape_and_structure(url=args.url, file_path=args.file, query=args.query)
    
    print("Structured syllabus ready.")
    upsert_syllabus_chunks_to_astra(structured_syllabus, source, args.collection)
