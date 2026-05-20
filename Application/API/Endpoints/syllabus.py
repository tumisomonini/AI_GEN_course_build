from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Callable

try:
    from Domain.syllabus import SyllabusState
    from Application.Workflows.syllabus_workflow import create_syllabus_workflow
except ImportError:
    create_syllabus_workflow: Optional[Callable] = None
    SyllabusState = None  # type: ignore

try:
    from ..agents import get_real_agents as get_agents
except ImportError:
    get_agents: Callable[[], dict] = lambda: {}

try:
    from Application.Ports.scraper import (
        scrape_relevant_syllabi,
        scrape_relevant_syllabi_async,
    )
except ImportError:
    scrape_relevant_syllabi: Optional[Callable] = lambda title, max_results: []
    scrape_relevant_syllabi_async: Optional[Callable] = lambda title, max_results: []

router = APIRouter()


class SyllabusRequest(BaseModel):
    topics: List[str] = []
    title: Optional[str] = None


class ScrapeRequest(BaseModel):
    title: str


@router.post("/scrape")
async def scrape_syllabus(request: ScrapeRequest):
    """Scrape relevant syllabi for given course title and store chunks in AstraDB."""
    if scrape_relevant_syllabi is None:
        raise HTTPException(
            status_code=503, detail="Scraper service not available - check dependencies"
        )
    try:
        if scrape_relevant_syllabi_async is not None:
            syllabi = await scrape_relevant_syllabi_async(request.title, max_results=5)
        else:
            syllabi = scrape_relevant_syllabi(request.title, max_results=5)

        # Flatten and upsert top syllabi to AstraDB (user_syllabi collection)
        all_texts = []
        all_metadatas = []
        for syllabus in syllabi[:3]:  # Top 3
            if syllabus and isinstance(syllabus, dict) and "error" not in syllabus:
                for section_key, chunks in syllabus.items():
                    if isinstance(chunks, list):
                        for chunk in chunks[:5]:  # Limit per section
                            all_texts.append(chunk)
                            all_metadatas.append(
                                {
                                    "course_title": request.title,
                                    "source_url": syllabus.get("source_url", ""),
                                    "source_title": syllabus.get("source_title", ""),
                                    "section": section_key,
                                    "type": "relevant_syllabus_chunk",
                                }
                            )

        # Upsert top chunks to Astra (MANDATORY)
        if all_texts:
            try:
                from Application.API.dependencies import get_triple_db_manager

                manager = get_triple_db_manager()
                repo = manager.astra
                if repo is None:
                    raise HTTPException(
                        status_code=503,
                        detail="AstraDB not available - required for syllabus scraping",
                    )

                import threading

                def background_upsert(texts, metas):
                    repo.upsert_syllabus_chunks(texts, metas)

                thread = threading.Thread(
                    target=background_upsert,
                    args=(all_texts, all_metadatas),
                    daemon=True,
                )
                thread.start()
            except Exception as e:
                print(f"❌ Astra upsert failed (mandatory): {e}")
                raise

        return {
            "status": "success",
            "course_title": request.title,
            "syllabi_found": len([s for s in syllabi if "error" not in s]),
            "total_chunks_stored": len(all_texts),
            "syllabi": syllabi,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.post("/generate")
async def generate_syllabus(request: SyllabusRequest):
    """Generate a syllabus outline (TOC-style) using the domain workflow."""
    agents = get_agents()
    if not agents:
        raise HTTPException(
            status_code=503,
            detail="Agents not initialised — server may still be starting up",
        )
    if create_syllabus_workflow is None or SyllabusState is None:
        raise HTTPException(
            status_code=503,
            detail="Syllabus workflow not available - check dependencies",
        )

    try:
        if request.title:
            print(
                f"Note: Title '{request.title}' provided - consider scraping first via /scrape endpoint"
            )

        workflow = create_syllabus_workflow(
            agents["planner"],
            agents["author"],
            agents["reviewer"],
            agents["assembler"],
        )

        invoke_data = {
            "title": request.title or "Untitled Course",
            "topics": request.topics,
            # SyllabusState contract: chapters must be a list (never a dict)
            "syllabus": [],
            "chapters": [],
            "validated": False,
            "level": "beginner",
            "duration_months": 3,
        }
        invoke_data = SyllabusState(**invoke_data).model_dump()

        if not isinstance(invoke_data.get("chapters"), list):
            invoke_data["chapters"] = []

        result = await workflow.ainvoke(invoke_data)

        syllabus = result.get("syllabus")
        if not isinstance(syllabus, list):
            syllabus = []

        chapters_raw = result.get("chapters", []) or []
        chapter_titles: List[str] = []
        if isinstance(chapters_raw, list):
            for ch in chapters_raw:
                try:
                    chapter_titles.append(ch.title)
                except Exception:
                    continue

        if not syllabus and not chapter_titles:
            raise HTTPException(
                status_code=400,
                detail="No syllabus/chapter output was produced.",
            )

        return {"status": "success", "syllabus": syllabus, "chapters": chapter_titles}

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        print("🚨 SYLLABUS GENERATION FULL TRACEBACK:")
        traceback.print_exc()
        raise HTTPException(500, f"Generation failed: {type(e).__name__}: {str(e)}")

