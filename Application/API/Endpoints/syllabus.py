from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Callable
import json

try:
    from Application.Workflows.syllabus_workflow import create_syllabus_workflow
except ImportError:
    create_syllabus_workflow: Optional[Callable] = None

try:
    from ..agents import get_real_agents as get_agents
except ImportError:
    get_agents: Callable[[], dict] = lambda: {}

try:
    from Application.Ports.scraper import scrape_relevant_syllabi
except ImportError:
    scrape_relevant_syllabi: Optional[Callable] = lambda title, max_results: []


class SyllabusRequest(BaseModel):
    topics: List[str] = ["Intro to Python", "Advanced Python"]
    title: Optional[str] = None

class ScrapeRequest(BaseModel):
    title: str

router = APIRouter()

@router.post("/scrape")
async def scrape_syllabus(request: ScrapeRequest):
    """Scrape relevant syllabi for given course title and store chunks in AstraDB"""
    if scrape_relevant_syllabi is None:
        raise HTTPException(503, "Scraper service not available - check dependencies")
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
        
        # Upsert top chunks to Astra if available
        if all_texts:
            try:
                from Application.API.dependencies import get_triple_db_manager
                manager = get_triple_db_manager()
                repo = manager.astra
                if repo:
                    import threading
                    def background_upsert(texts, metas):
                        try:
                            repo.upsert_syllabus_chunks(texts, metas)
                        except Exception as e:
                            print(f"❌ Scrape endpoint background upsert failed: {e}")

                    thread = threading.Thread(target=background_upsert, args=(all_texts, all_metadatas), daemon=True)
                    thread.start()
            except Exception as e:
                print(f"⚠️ Astra upsert initialization failed: {e}")
        
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
    if create_syllabus_workflow is None:
        raise HTTPException(503, "Syllabus workflow not available - check dependencies")
    try:
        # If title provided, could optionally scrape first (future enhancement)
        if request.title:
            print(f"Note: Title '{request.title}' provided - consider scraping first via /scrape endpoint")
        
        workflow = create_syllabus_workflow(
            agents["planner"], agents["author"], agents["reviewer"], agents["assembler"]
        )
        invoke_data = {
            "title": request.title or "Untitled Course",
            "topics": request.topics,
            "syllabus": [],
            "chapters": [],
            "validated": False,
            "level": "beginner",
            "duration_months": 3
        }
        
        # Must use ainvoke for graphs with async nodes (Author/Reviewer)
        result = await workflow.ainvoke(invoke_data)
        
        # chapters is a List[Chapter], extract titles for response
        chapter_titles = [ch.title for ch in result.get("chapters", [])]
        return {"status": "success", "syllabus": result["syllabus"], "chapters": chapter_titles}
    except Exception as e:
        import traceback
        print("🚨 SYLLABUS GENERATION FULL TRACEBACK:")
        traceback.print_exc()
        print(f"Error type: {type(e).__name__}, message: {str(e)}")
        raise HTTPException(500, f"Generation failed: {type(e).__name__}: {str(e)}")

