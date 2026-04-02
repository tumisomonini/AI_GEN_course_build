from typing import Dict, List
import argparse
import os
from Application.Infrastructure.Scraper.web_scraper import scrape_web_syllabus
from Application.Infrastructure.Scraper.pdf_scraper import scrape_pdf_syllabus
from Application.Ports.scraper import parse_syllabus, scrape_relevant_syllabi
from Application.Ports.Astra_repo import AstraRepo

def scrape_and_structure(url: str = None, file_path: str = None, query: str = None) -> Dict[str, List[str]]:
    if query:
        syllabi = scrape_relevant_syllabi(query)
        # Flatten top syllabus main_topics
        top_syllabus = next((s for s in syllabi if 'error' not in s), {})
        structured = top_syllabus if top_syllabus else {"main_topics": ["No syllabus found"]}
    elif url:
        raw_syllabus = scrape_web_syllabus(url)
        structured = parse_syllabus(raw_syllabus)
    elif file_path:
        raw_syllabus = scrape_pdf_syllabus(file_path)
        structured = parse_syllabus(raw_syllabus)
    else:
        raise ValueError("Provide --url, --file, or --query")
    print("Structured syllabus:", structured)
    return structured

def upsert_syllabus_chunks_to_astra(structured_syllabus: Dict[str, List[str]], source: str, collection_name: str = "syllabus_chunks"):
    """Flatten structured syllabus to chunks and upsert to AstraDB"""
    texts = []
    metadatas = []
    for section_key, chunks in structured_syllabus.items():
        for chunk in chunks:
            if chunk.strip():
                texts.append(chunk)
                metadatas.append({
                    "source": source,
                    "section": section_key,
                    "type": "syllabus_chunk"
                })
    
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
    
    source = args.query or args.url or args.file
    structured_syllabus = scrape_and_structure(url=args.url, file_path=args.file, query=args.query)
    
    print("Structured syllabus ready.")
    upsert_syllabus_chunks_to_astra(structured_syllabus, source, args.collection)
