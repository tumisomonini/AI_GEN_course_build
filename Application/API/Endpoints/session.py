from fastapi import APIRouter, HTTPException, Form, Cookie, Response, BackgroundTasks, Depends
from typing import Optional
import redis
import json
import uuid
import os
from fastapi.responses import JSONResponse
from Application.API.dependencies import get_postgres_repo
from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

router = APIRouter(tags=["Session"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(REDIS_URL, decode_responses=True)

SESSION_KEY_PREFIX = "session:course:"
SESSION_COOKIE = "session_id"
SESSION_TTL = 3600

def _get_or_create_session(response: Response, session_id: Optional[str]) -> str:
    """Return existing session_id or mint a new one and set the cookie."""
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=SESSION_COOKIE,
            value=session_id,
            httponly=True,
            max_age=SESSION_TTL,
            samesite="lax"
        )
    return session_id

@router.get("/course")
async def get_course_session(
    response: Response,
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)
) -> dict:
    """Get active course_id from session cookie."""
    if not session_id:
        return {"course_id": None}
    data = r.get(SESSION_KEY_PREFIX + session_id)
    if not data:
        return {"course_id": None}
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {"course_id": None}

@router.post("")
async def set_course_session(
    response: Response,
    course_id: int = Form(...),
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)
):
    """Save course_id to session cookie."""
    session_id = _get_or_create_session(response, session_id)
    r.set(SESSION_KEY_PREFIX + session_id, json.dumps({"course_id": course_id}), ex=SESSION_TTL)
    return {"status": "saved", "course_id": course_id}

@router.post("/clear")
async def clear_course_session(
    response: Response,
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)
):
    """Clear session data and expire the cookie."""
    if session_id:
        r.delete(SESSION_KEY_PREFIX + session_id)
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "cleared"}

@router.post("/cleanup")
async def cleanup_sessions(background_tasks: BackgroundTasks, repo: PostgresRepository = Depends(get_postgres_repo)):
    """Trigger a cleanup of expired sessions in the relational DB via background task."""
    try:
        count = repo.cleanup_expired_sessions()
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


print("✅ Session endpoints with Redis ready")
