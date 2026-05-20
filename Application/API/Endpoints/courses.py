from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Body
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    AliasChoices,
)
from typing import Dict, Any, List, Optional, Self
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
import os
import time
import json
import asyncio

from ..dependencies import get_postgres_repo
from Application.Ports.postgres_repo import PostgresRepo

router = APIRouter(tags=["Courses"])


class InlineScraper:
    """Minimal scraper class for search - delegates to initialized Scraper."""

    def __init__(self):
        from Application.Ports.scraper import get_scraper

        self._scraper = get_scraper()

    async def scrape_relevant_sources(self, topic: str) -> Dict:
        results = await self._scraper.search_and_scrape_async(topic, max_results=3)
        valid = [r for r in results if "error" not in r]
        return {
            "total_sources": len(valid),
            "quality_score": valid[0].get("quality_score", 0) if valid else 0,
            "sources": [
                {
                    "title": r.get("source_title", f"'{topic}' tutorial"),
                    "quality": r.get("quality_score", 0),
                }
                for r in valid[:3]
            ],
        }


inline_scraper = InlineScraper()


class CourseGenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(
        ..., min_length=3, validation_alias=AliasChoices("title", "topic")
    )
    topic: Optional[str] = None  # Kept for compatibility if needed elsewhere
    level: str = "beginner"
    duration_months: int = Field(default=3, ge=1)

    @field_validator("level")
    @classmethod
    def level_must_be_valid(cls, v):
        allowed = {"beginner", "intermediate", "advanced"}
        if v not in allowed:
            raise ValueError(f"level must be one of {allowed}")
        return v

    @model_validator(mode="after")
    @classmethod
    def sync_title_and_topic(cls, values):
        """Ensure title and topic are always synced to prevent workflow failures."""
        if not values.topic:
            values.topic = values.title
        return values


@router.get("/search-courses")
async def search_courses(q: str = "", repo: PostgresRepo = Depends(get_postgres_repo)):
    """Search existing courses and return counts"""
    if not repo:
        raise HTTPException(status_code=503, detail="Database connection not available")
    results = repo.search_courses(q) if q else []
    return {
        "query": q,
        "results": results,
        "db_count": len(results),
        "web_count": 0,
        "message": f"Ready to generate '{q}' course! Use /generate endpoint.",
    }


@router.post("/generate/course-template")
async def generate_course_template(
    request: CourseGenerateRequest,
    background_tasks: BackgroundTasks,
    repo: PostgresRepo = Depends(get_postgres_repo),
):
    "Generate TOC-style template only (cheap, no LLM content)"
    if not repo:
        raise HTTPException(status_code=503, detail="Database connection not available")
    # 1. Create a placeholder course to get an ID for progress tracking
    course_title = request.title or request.topic
    template_stub = {
        "title": course_title,
        "level": request.level.capitalize(),
        "duration_months": request.duration_months,
        "chapters": [],
        "status": "generating_outline",
    }
    course_id = repo.create_course_from_template(template_stub)
    run_id = repo.create_run(course_id, "template_generation")

    repo.log_message(
        run_id, "System", f"Starting outline generation for '{course_title}'", "info"
    )

    # Move logic to background to allow ChatGPT-style streaming via SSE
    background_tasks.add_task(outline_generation_task, request, course_id, run_id)

    return {
        "course_id": course_id,
        "run_id": run_id,
        "status": "generating_outline",
        "message": "Generation started. Follow stream for progress.",
    }


@router.get("/generate/course-template-stream")
async def generate_course_template_stream(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str,
    level: str = "beginner",
    duration_months: int = 3,
    repo: PostgresRepo = Depends(get_postgres_repo),
):
    """
    All-in-one endpoint: Starts generation and streams progress immediately (ChatGPT-style).
    Fixes 404 for GET /courses/generate/course-template-stream
    """
    # 1. Initialize course and run
    template_stub = {
        "title": title,
        "level": level.lower(),
        "duration_months": duration_months,
        "chapters": [],
    }
    course_id = repo.create_course_from_template(template_stub)
    run_id = repo.create_run(course_id, "template_generation_stream")
    repo.log_message(run_id, "System", f"Initiating stream for '{title}'...", "info")

    # 2. Trigger the actual work in background
    gen_request = CourseGenerateRequest(
        title=title, level=level.lower(), duration_months=duration_months
    )
    background_tasks.add_task(outline_generation_task, gen_request, course_id, run_id)

    # 3. Stream the logs
    async def event_generator():
        last_log_id = 0
        # Send initial course_id so frontend knows what was created
        yield f"data: {json.dumps({'type': 'init', 'course_id': course_id, 'run_id': run_id})}\n\n"

        while True:
            if await request.is_disconnected():
                break

            status_info = repo.get_course_status(course_id)
            logs = repo.get_logs_after(
                run_id, last_log_id
            )  # Assuming this method exists or use direct query

            for log in logs:
                yield f"data: {json.dumps({'type': 'log', 'agent': log['agent_name'], 'message': log['message'], 'level': log['level']})}\n\n"
                last_log_id = log["log_id"]

            if status_info["status"] in ["completed", "failed", "awaiting_approval"]:
                yield f"data: {json.dumps({'type': 'done', 'course_id': course_id, 'status': status_info['status']})}\n\n"
                break
            await asyncio.sleep(0.8)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{course_id}/resume")
async def resume_course_generation(
    course_id: int,
    background_tasks: BackgroundTasks,
    repo: PostgresRepo = Depends(get_postgres_repo),
):
    """
    Resume course generation for a course in 'draft' or 'failed' status.
    Detects progress and triggers either outline generation or full content generation.
    """
    course_info = repo.get_course_status(course_id)
    if not course_info or "error" in course_info:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    status = course_info.get("status")
    title = course_info.get("title")

    # Case 1: Course is a shell or outline failed
    if status in ["draft", "failed", "generating_outline"]:
        try:
            review_data = repo.get_course_review(course_id)
            template = review_data.get("template", {})
        except:
            template = {}

        gen_request = CourseGenerateRequest(
            title=title,
            level=template.get("level", "beginner").lower()
            if isinstance(template, dict) and template.get("level")
            else "beginner",
            duration_months=template.get("duration_months", 3)
            if isinstance(template, dict)
            else 3,
        )

        run_id = repo.create_run(course_id, "resume_outline_generation")
        repo.update_course_status(course_id, "generating_outline")
        repo.log_message(
            run_id, "System", f"Resuming outline generation for '{title}'", "info"
        )
        background_tasks.add_task(
            outline_generation_task, gen_request, course_id, run_id
        )
        return {
            "course_id": course_id,
            "run_id": run_id,
            "status": "generating_outline",
        }

    # Case 2: Outline exists, just needs content generation
    if status == "awaiting_approval":
        return await approve_and_generate_full(course_id, background_tasks, None, repo)

    return {
        "course_id": course_id,
        "status": status,
        "message": "Course is already active or completed",
    }


async def outline_generation_task(
    request: CourseGenerateRequest, course_id: int, run_id: int
):
    """Background task to handle template generation with status tracking"""
    repo = PostgresRepo()
    try:
        from Application.Workflows.syllabus_workflow import create_outline_workflow

        course_title = request.title or request.topic or ""
        template = await create_outline_workflow(
            course_title, request.level, request.duration_months, run_id=run_id
        )


        repo.update_course_template(course_id, template)
        repo.update_course_status(course_id, "awaiting_approval")
        repo.update_run_status(run_id, "completed")
        repo.log_message(run_id, "System", "Outline ready for review.", "info")
    except Exception as e:
        repo.log_message(run_id, "System", f"Template failed: {str(e)}", "error")
        repo.update_course_status(course_id, "failed")
    finally:
        repo.close()


@router.post("/{course_id}/approve-full")
async def approve_and_generate_full(
    course_id: int,
    background_tasks: BackgroundTasks,
    modifications: Optional[List[str]] = Body(None),
    repo: PostgresRepo = Depends(get_postgres_repo),
):
    """Approve template -> trigger full content generation background.

    Guardrail: do not start full generation until the outline is ready.
    """
    # 1) Require outline phase to be complete
    course_status_row = repo.get_course_status(course_id)
    status = (course_status_row or {}).get("status")
    if status != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Outline not ready for course_id={course_id}. "
                f"Current status: {status!r}. Wait until outline generation completes."
            ),
        )

    # 2) Require existing approved template with chapters
    review_data = repo.get_course_review(course_id)
    template = (review_data or {}).get("template", {}) if isinstance(review_data, dict) else {}
    chapters = template.get("chapters", []) if isinstance(template, dict) else []
    if not chapters or not isinstance(chapters, list):
        raise HTTPException(
            status_code=409,
            detail=(
                f"No approved outline template/chapter list found for course_id={course_id}. "
                "Outline generation may have failed or DB state is inconsistent."
            ),
        )

    # 3) Optional modifications are applied only after guardrails pass
    if modifications:
        template["chapters"] = modifications
        repo.update_course_template(course_id, template)

    repo.create_approval(course_id, approved=True)
    repo.update_course_status(course_id, "generating_full")

    run_id = repo.create_run(course_id, "full_content_generation")
    background_tasks.add_task(full_content_workflow, course_id, run_id)

    return {
        "status": "approved",
        "run_id": run_id,
        "message": "Full content generation started",
    }


async def full_content_workflow(course_id: int, run_id: int):
    """Background full content with proper run tracking"""
    repo = PostgresRepo()
    try:
        review_data = repo.get_course_review(course_id)
        if not review_data or not review_data.get("template"):
            repo.log_message(
                run_id,
                "workflow",
                "Failure: No approved template found to generate from.",
                "error",
            )
            repo.update_course_status(course_id, "failed")
            return

        template = review_data["template"]
        title = (
            template["title"]
            if isinstance(template, dict)
            else template.get("title", "")
        )
        duration = (
            template.get("duration_months", 3) if isinstance(template, dict) else 3
        )
        level = (
            template.get("level", "beginner").lower()
            if isinstance(template, dict)
            else "beginner"
        )
        repo.log_message(
            run_id, "workflow", f"Starting generation for: {title}", "info"
        )

        # Extract approved chapters from template to skip re-scraping and re-planning
        approved_chapters = (
            template.get("chapters", []) if isinstance(template, dict) else []
        )

        from Application.Workflows.syllabus_workflow import (
            create_real_syllabus_workflow,
        )

        result, _ = await create_real_syllabus_workflow(
            title,
            duration,
            level=level,
            run_id=run_id,
            topics=approved_chapters,
            syllabus=approved_chapters,
        )

        # result is a Syllabus.model_dump() — chapters is a list of Chapter dicts
        chapters = result.get("chapters", [])
        if isinstance(chapters, dict):
            chapters_list = [{"title": k, "content": v} for k, v in chapters.items()]
        else:
            chapters_list = [
                {"title": ch.get("title", ""), "content": ch.get("content", "")}
                for ch in chapters
            ]

        repo.save_full_course_chapters(course_id, chapters_list)

        # ✅ Finish end-to-end course ↔ topics linking where course_id exists (endpoint layer)
        try:
            from Application.Infrastructure.graphDb.neo4j_repo import Neo4jNeomodelRepository
            from Application.API.dependencies import sanitize_neo4j_uri

            neo_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo_user = os.getenv("NEO4J_USERNAME", "neo4j")
            neo_pass = os.getenv("NEO4J_PASSWORD", "password")
            neo_db = os.getenv("NEO4J_DATABASE", "neo4j")
            neo_uri = sanitize_neo4j_uri(neo_uri)

            neo_repo = Neo4jNeomodelRepository(neo_uri, neo_user, neo_pass, neo_db)
            topic_names = [ch.get("title", "") for ch in chapters_list if isinstance(ch, dict) and ch.get("title")]
            topic_names = [t for t in topic_names if t]

            neo_repo.link_topics_to_course(
                course_id=course_id,
                title=title,
                topic_names=topic_names,
            )
            neo_repo.close()
            repo.log_message(run_id, "Neo4j", f"Linked course↔topics for course_id={course_id}", "info")
        except Exception as link_e:
            # Linking is best-effort; do not fail full generation if Neo4j is down.
            repo.log_message(run_id, "Neo4j", f"Course↔topics linking failed: {link_e}", "warning")

        repo.log_message(run_id, "assembler", "Course assembly complete", "info")
        repo.update_course_status(course_id, "completed")
        repo.update_run_status(run_id, "completed")
    except Exception as e:
        import traceback

        traceback.print_exc()
        error_detail = f"Generation failed: {str(e)}"
        repo.log_message(run_id, "workflow", error_detail, "error")
        repo.update_course_status(course_id, "failed")
        repo.update_run_status(run_id, "failed")
    finally:
        repo.close()


@router.get("/{course_id}")
async def course_status(
    course_id: int, repo: PostgresRepo = Depends(get_postgres_repo)
):
    status = repo.get_course_status(course_id)
    return status


@router.get("/{course_id}/status")
async def course_status_only(
    course_id: int, repo: PostgresRepo = Depends(get_postgres_repo)
):
    """Lightweight status-only endpoint for frontend polling"""
    row = repo.get_course_status(course_id)
    if not row or not row.get("status"):
        raise HTTPException(status_code=404, detail="Course not found")

    response = {"status": row.get("status", "unknown"), "course_id": course_id}
    if response["status"] == "failed":
        response["error_details"] = repo.get_latest_error(course_id)

    return response


@router.get("/{course_id}/events")
async def stream_course_updates(
    course_id: int, request: Request, repo: PostgresRepo = Depends(get_postgres_repo)
):
    """SSE endpoint to stream real-time progress to the frontend."""

    async def event_generator():
        last_log_id = 0
        # Resolve the initial run_id
        run_id = None
        with repo.get_cursor() as cur:
            cur.execute(
                "SELECT run_id FROM runs WHERE course_id = %s ORDER BY run_id DESC LIMIT 1",
                (course_id,),
            )
            row = cur.fetchone()
            if row:
                run_id = row[0]

        while True:
            if await request.is_disconnected():
                break

            status_info = repo.get_course_status(course_id)

            if run_id:
                logs = repo.get_logs_after(run_id, last_log_id)
                for log in logs:
                    yield f"data: {json.dumps({'type': 'log', 'agent': log['agent_name'], 'message': log['message'], 'level': log['level'], 'status': status_info['status']})}\n\n"
                    last_log_id = log["log_id"]

            if status_info["status"] in ["completed", "failed"]:
                yield f"data: {json.dumps({'type': 'done', 'status': status_info['status']})}\n\n"
                break

            await asyncio.sleep(1.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{course_id}/generation-content")
async def get_generation_content(
    course_id: int, repo: PostgresRepo = Depends(get_postgres_repo)
):
    """Return best-effort generation payload for frontend display.

    During generation, the full payload may not yet be persisted.
    This endpoint returns:
      - status (draft/generating/awaiting_approval/completed/failed)
      - template (if available)
      - chapters: only chapters with non-empty content (if available)

    Frontend can poll this endpoint while SSE streams logs.
    """
    status_info = repo.get_course_status(course_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Course not found")

    review_data = None
    try:
        review_data = repo.get_course_review(course_id)
    except Exception:
        review_data = None

    template = {}
    chapters = []

    if isinstance(review_data, dict):
        template = review_data.get("template") or {}
        chapters = review_data.get("chapters") or []

    # Best-effort: strip empty chapter content
    filtered_chapters = []
    for ch in chapters if isinstance(chapters, list) else []:
        if not isinstance(ch, dict):
            continue
        content = ch.get("content")
        if isinstance(content, str) and content.strip():
            filtered_chapters.append(ch)
        elif ch.get("title") and content is None:
            # keep placeholder titles if backend stores empty content as null
            filtered_chapters.append(ch)

    return {
        "course_id": course_id,
        "status": status_info.get("status", "unknown"),
        "template": template if isinstance(template, dict) else {},
        "chapters": filtered_chapters,
        "generated_chapter_count": len(filtered_chapters),
        "total_chapter_count": len(chapters) if isinstance(chapters, list) else 0,
    }


@router.get("/{course_id}/course-review")
async def get_course_review(
    course_id: int, repo: PostgresRepo = Depends(get_postgres_repo)
):
    review_data = repo.get_course_review(course_id)
    if not review_data:
        raise HTTPException(status_code=404, detail="Course not found")
    return review_data



@router.get("/{course_id}/download")
async def download_course(
    course_id: int,
    format: str = "markdown",
    repo: PostgresRepo = Depends(get_postgres_repo),
):
    """Return course content as downloadable format"""
    review_data = repo.get_course_review(course_id)
    template = review_data.get("template", {})
    chapters = review_data.get("chapters", [])

    title = template.get("title", "course") if isinstance(template, dict) else "course"

    if format == "json":
        return JSONResponse(
            content=review_data,
            headers={"Content-Disposition": f"attachment; filename={title}.json"},
        )

    # Build markdown from chapters
    lines = [f"# {title}\n"]
    if isinstance(template, dict):
        if template.get("learning_objectives"):
            lines.append("## Learning Objectives")
            for obj in template["learning_objectives"]:
                lines.append(f"- {obj}")
            lines.append("")
        if template.get("prerequisites"):
            lines.append("## Prerequisites")
            for req in template["prerequisites"]:
                lines.append(f"- {req}")
            lines.append("")

    for ch in chapters:
        lines.append(f"## {ch.get('title', 'Chapter')}")
        content = ch.get("content", "")
        if content:
            lines.append(content)
        lines.append("")

    markdown = "\n".join(lines)

    return PlainTextResponse(
        content=markdown,
        headers={
            "Content-Disposition": f"attachment; filename={title.replace(' ', '_')}.md"
        },
    )


@router.post("/{course_id}/approve")
async def approve_course(course_id: int, background_tasks: BackgroundTasks):
    """Frontend compatibility endpoint - calls full generation workflow"""
    print(
        f"✅ Frontend approve endpoint hit for course {course_id} - starting full generation"
    )
    return await approve_and_generate_full(course_id, background_tasks)


print("✅ Simplified endpoints - Real generation focus!")
