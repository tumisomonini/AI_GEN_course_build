from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from fastapi.responses import StreamingResponse

from Application.Ports.postgres_repo import PostgresRepo
from Application.API.dependencies import get_postgres_repo
from .courses import CourseGenerateRequest, outline_generation_task

router = APIRouter(tags=["Courses"])


class GenerateCourseRequest(BaseModel):
    """Standard contract: generate any course from user input."""

    model_config = ConfigDict(populate_by_name=True)

    # Accept title/topic
    title: str = Field(..., min_length=3, validation_alias="topic")
    level: str = "beginner"
    duration_months: int = Field(default=3, ge=1)

    @field_validator("level")
    @classmethod
    def level_must_be_valid(cls, v: str) -> str:
        allowed = {"beginner", "intermediate", "advanced"}
        if v not in allowed:
            raise ValueError(f"level must be one of {allowed}")
        return v


@router.post("/generate")
async def generate_course(
    request: GenerateCourseRequest,
    background_tasks: BackgroundTasks,
    repo: PostgresRepo = Depends(get_postgres_repo),
):
    """Kick off outline generation from user input."""
    if not repo:
        raise HTTPException(status_code=503, detail="Database connection not available")

    template_stub = {
        "title": request.title,
        "level": request.level,
        "duration_months": request.duration_months,
        "chapters": [],
    }

    course_id = repo.create_course_from_template(template_stub)
    run_id = repo.create_run(course_id, "template_generation")

    repo.log_message(run_id, "System", f"Starting outline generation for '{request.title}'", "info")

    gen_request = CourseGenerateRequest(
        title=request.title,
        level=request.level,
        duration_months=request.duration_months,
    )
    background_tasks.add_task(outline_generation_task, gen_request, course_id, run_id)

    return {
        "course_id": course_id,
        "run_id": run_id,
        "status": "generating_outline",
        "message": "Generation started. Poll /courses/{course_id}/status or use /events for streaming logs.",
    }


@router.get("/generate/stream")
async def generate_course_stream(
    request: Request,
    title: str,
    level: str = "beginner",
    duration_months: int = 3,
    repo: PostgresRepo = Depends(get_postgres_repo),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """SSE wrapper around the same generation logic."""
    if not repo:
        raise HTTPException(status_code=503, detail="Database connection not available")

    template_stub = {
        "title": title,
        "level": level.lower(),
        "duration_months": duration_months,
        "chapters": [],
    }

    course_id = repo.create_course_from_template(template_stub)
    run_id = repo.create_run(course_id, "template_generation_stream")
    repo.log_message(run_id, "System", f"Initiating stream for '{title}'...", "info")

    gen_request = CourseGenerateRequest(title=title, level=level.lower(), duration_months=duration_months)
    background_tasks.add_task(outline_generation_task, gen_request, course_id, run_id)

    async def event_generator():
        last_log_id = 0
        yield f"data: {json.dumps({'type': 'init', 'course_id': course_id, 'run_id': run_id})}\n\n"

        while True:
            if await request.is_disconnected():
                break

            status_info = repo.get_course_status(course_id)
            status = status_info.get("status", "unknown")

            logs = repo.get_logs_after(run_id, last_log_id)
            for log in logs:
                yield (
                    f"data: {json.dumps({'type': 'log', 'agent': log.get('agent_name'), 'message': log.get('message'), 'level': log.get('level')})}\n\n"
                )
                last_log_id = int(log.get("log_id", last_log_id))

            if status in {"completed", "failed", "awaiting_approval"}:
                yield f"data: {json.dumps({'type': 'done', 'course_id': course_id, 'status': status})}\n\n"
                break

            await asyncio.sleep(0.8)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

