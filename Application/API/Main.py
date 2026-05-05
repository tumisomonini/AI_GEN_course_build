from contextlib import asynccontextmanager
from typing import Optional
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import traceback
from pathlib import Path
import sys

# Fix utils import by adding root to path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from utils.env_loader import load_root_env

# Load env centrally
load_root_env()

from Application.API.Endpoints.syllabus import router as syllabus_router
from Application.API.Endpoints.courses import router as courses_router
from Application.API.Endpoints.session import router as session_router
from Application.API.dependencies import get_postgres_repo, get_neo4j_repo, get_astra_repo, get_triple_db_manager, sanitize_neo4j_uri
from Application.API.agents import get_real_agents
from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Init repos
    print("🚀 Starting full infrastructure...")
    import Application.API.dependencies as deps
    from Domain.knowledge_graphy import KnowledgeGraph
    
    # Use centralized init for consistency and schema enforcement
    deps.init_postgres_singleton()
    deps.init_neo4j_singleton()
    try:
        deps.init_astra_singleton()
        print("✅ AstraDB ready")
    except Exception as e:
        print(f"⚠️ Astra optional failed: {e}")
    
    # Auto-populate Neo4j sample data using the shared driver
    if deps._neo4j_repo:
        try:
            target_db = os.getenv('NEO4J_DATABASE', 'neo4j')
            
            # Safety check: If we are on localhost but using an Aura-style ID, fallback to 'neo4j'
            # Local Docker Neo4j instances usually only have the 'neo4j' database created.
            raw_uri = os.getenv('NEO4J_URI', '')
            if "localhost" in raw_uri or "127.0.0.1" in raw_uri:
                if target_db != "neo4j":
                    target_db = "neo4j"

            kg = KnowledgeGraph(deps._neo4j_repo.driver, target_db)
            kg.add_topic("Python Basics", "Fundamental syntax and data types")
            kg.add_topic("Data Structures", "Lists, dicts, sets")
            kg.add_prerequisite("Data Structures", "Python Basics")
            print("✅ Neo4j populated with sample KG data")
        except Exception as e:
            print(f"⚠️ Neo4j population skipped: {e}")
    
    # Comprehensive final check
    try:
        manager = get_triple_db_manager()
        health = manager.get_health()
        critical_dbs = {k: v for k, v in health.items() if k in ('postgres', 'neo4j')}
        if all(v == 'healthy' for v in critical_dbs.values()):
            astra_status = health.get('astra', 'unknown')
            if astra_status == 'healthy':
                print("✅ TripleDBManager: All 3 DBs healthy & integrated!")
            else:
                print(f"⚠️ TripleDBManager: Astra status: {astra_status} (Vector RAG disabled)")
            
            # Ensure metadata is synced between Relational and Graph layers
            manager.sync_metadata()
        else:
            raise ValueError(f"Critical DB health failed: {critical_dbs}")
    except Exception as e:
        print(f"❌ Triple integration failed: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🔌 Closing connections...")
    if deps._postgres_repo:
        deps._postgres_repo.close()
    if deps._neo4j_repo:
        deps._neo4j_repo.close()
    print("✅ Shutdown complete")


app = FastAPI(
    title="🚀 AI Course Builder API",
    description="Real scraping → RAG → AI course generation",
    version="2.0.0",
    lifespan=lifespan
)

from fastapi.middleware.gzip import GZipMiddleware  # Performance: Enable compression

# Performance: GZip compression for large JSON responses (courses/syllabus)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Compliance: Restrict CORS origins in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """Global exception handler to provide detailed error logs for 500 errors."""
    try:
        return await call_next(request)
    except Exception as exc:
        print(f"🚨 UNHANDLED EXCEPTION: {str(exc)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {type(exc).__name__}", "message": str(exc)}
        )

app.include_router(syllabus_router, prefix="/syllabus", tags=["Syllabus"])
app.include_router(courses_router, prefix="/courses", tags=["Courses"])
app.include_router(session_router, prefix="/session", tags=["Session"])

@app.get("/health-check", include_in_schema=False)
async def root():
    """Redirect root to frontend index"""
    return RedirectResponse(url="/index.html")

@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots():
    """Compliance: Prevent search engines from indexing API routes."""
    return "User-agent: *\nDisallow: /syllabus/\nDisallow: /courses/\nDisallow: /session/"

# Static mounts MUST come after all API routes — mount("/") shadows everything registered after it
pages_path = Path(__file__).parent.parent.parent / "Pages"
if pages_path.exists():
    app.mount("/Pages", StaticFiles(directory=pages_path, html=True), name="pages")
    print(f"✅ Pages served from {pages_path} at /Pages")

frontend_path = Path(__file__).parent.parent.parent / "Front_End"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    print(f"✅ Frontend served from {frontend_path} at /")

@app.websocket("/ws/health")
async def websocket_health_check(websocket: WebSocket):
    """Basic WebSocket health endpoint to handle heartbeat/monitoring."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"status": "healthy", "service": "AI Course Builder"})
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        print("🔌 WebSocket health check disconnected")

@app.get("/health")
async def health():
    """Full system health: TripleDB + agents."""
    from Application.API.dependencies import get_postgres_repo, get_astra_repo, get_neo4j_repo, get_triple_db_manager
    from Application.API.agents import get_real_agents
    
    # Safe repo fetches (handle None)
    pg = next(get_postgres_repo() or iter([]), None)
    astra_repo = next(get_astra_repo() or iter([]), None)
    neo4j_repo = next(get_neo4j_repo() or iter([]), None)
    manager = get_triple_db_manager()
    
    health = manager.get_health()
    
    # Agent status
    try:
        get_real_agents()  # Smoke test
        agent_status = 'ready'
    except Exception as e:
        agent_status = f'degraded: {str(e)}'
    
    # Individual DB details with light retries if manager degraded
    pg_status = {'status': 'ready' if pg else 'down'}
    astra_status = {'status': 'ready' if astra_repo else 'down'}
    neo4j_status = {'status': 'ready' if neo4j_repo else 'down'}
    
    if neo4j_repo:
        try:
            database = os.getenv('NEO4J_DATABASE', 'neo4j')
            with neo4j_repo.driver.session(database=database) as session:
                count = len(list(session.run('MATCH (t:Topic) RETURN t LIMIT 1')))
                neo4j_status['topics_count'] = count
        except Exception:
            neo4j_status['status'] = 'error'
    
    overall = 'healthy' if all(s['status'] == 'ready' for s in [pg_status, neo4j_status]) else 'degraded'
    
    return {
        'status': overall,
        'triple_manager': health,
        'postgres': pg_status,
        'neo4j': neo4j_status,
        'astra': astra_status,
        'agents': agent_status,
        'pipeline': 'integrated'
    }

print("🎓 Real course builder live at http://localhost:8000/Pages/workflow.html")
