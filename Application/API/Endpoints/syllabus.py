from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json

try:
    from Application.Workflows.syllabus_workflow import create_syllabus_workflow
except ImportError:
    create_syllabus_workflow = None

try:
    from ..agents import get_real_agents as get_agents
except ImportError:
    get_agents = lambda: {}

try:
    from Application.Ports.scraper import scrape_relevant_syllabi
except ImportError:
    scrape_relevant_syllabi = lambda title, max_results: []



class SyllabusRequest(BaseModel):
    topics: List[str] = ["Intro to Python", "Advanced Python"]
    title: Optional[str] = None

class ScrapeRequest(BaseModel):
    title: str

router = APIRouter()

@router.post("/scrape")
async def scrape_syllabus(request: ScrapeRequest):
    """Scrape relevant syllabi for given course title and store chunks in AstraDB"""
    try:
        syllabi = scrape_relevant_syllabi(request.title, max_results=5)
        
        # Flatten and upsert top syllabi to AstraDB (user_syllabi collection)
        all_texts = []
        all_metadatas = []
        for syllabus in syllabi[:3]:  # Top 3
            if syllabus and isinstance(syllabus, dict) and 'error' not in syllabus:
                for section_key, chunks in syllabus.items():
                    if isinstance(chunks, list):
                        for chunk in chunks[:5]:  # Limit per section
                            all_texts.append(chunk)
                            all_metadatas.append({
                                "course_title": request.title,
                                "source_url": syllabus.get('source_url', ''),
                                "source_title": syllabus.get('source_title', ''),
                                "section": section_key,
                                "type": "relevant_syllabus_chunk"
                            })
        
        # Vector store removed; chunks not upserted
        
        return {
            "status": "success",
            "course_title": request.title,
            "syllabi_found": len([s for s in syllabi if 'error' not in s]),
            "total_chunks_stored": len(all_texts),
            "syllabi": syllabi
        }
    except Exception as e:
        raise HTTPException(500, f"Scraping failed: {str(e)}")

@router.post("/generate")
async def generate_syllabus(request: SyllabusRequest):
    agents = get_agents()
    if not agents:
        raise HTTPException(503, "Agents not initialised — server may still be starting up")
    try:
        topics = request.topics
        # If title provided, could optionally scrape first (future enhancement)
        if request.title:
            print(f"Note: Title '{request.title}' provided - consider scraping first via /scrape endpoint")
        
        workflow = create_syllabus_workflow(
            agents["planner"], agents["author"], agents["reviewer"], agents["assembler"]
        )
        invoke_data = {
            "topics": topics,
            "syllabus": [],
            "chapters": {},
            "validated": False
        }
        if request.title:
            invoke_data["title"] = request.title
        result = workflow.invoke(invoke_data)
        return {"status": "success", "syllabus": result["syllabus"], "chapters": list(result["chapters"].keys())}
    except Exception as e:
        import traceback
        print("🚨 SYLLABUS GENERATION FULL TRACEBACK:")
        traceback.print_exc()
        print(f"Error type: {type(e).__name__}, message: {str(e)}")
        raise HTTPException(500, f"Generation failed: {type(e).__name__}: {str(e)}")
