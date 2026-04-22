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

from Application.API.Endpoints.syllabus import router as syllabus_router
from Application.API.Endpoints.courses import router as courses_router
from Application.API.Endpoints.session import router as session_router
from Application.API.dependencies import get_postgres_repo, get_neo4j_repo, get_astra_repo, sanitize_neo4j_uri
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
    
    try:
        deps._postgres_repo = PostgresRepo()
        print("✅ Postgres connected and ready")
    except Exception as e:
        deps._postgres_repo = None
        print(f"⚠️ Postgres skipped/failed: {e}")

    # Use centralized init for consistency
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
        from Application.API.dependencies import check_all_dbs
        check_all_dbs()
        print("✅ All critical DBs healthy - system ready for operation!")
    except Exception as e:
        print(f"⚠️ DEGRADED MODE (non-critical services may work): {e}")
    
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

# Serve Pages/ statically under /pages only
pages_path = Path(__file__).parent.parent.parent / "Pages"
if pages_path.exists():
    app.mount("/Pages", StaticFiles(directory=pages_path, html=True), name="pages")
    print(f"✅ Pages served from {pages_path} at /Pages")

app.include_router(syllabus_router, prefix="/syllabus", tags=["Syllabus"])
app.include_router(courses_router, prefix="/courses", tags=["Courses"])
app.include_router(session_router, prefix="/session", tags=["Session"])

@app.get("/")
async def root():
    """Redirect to test interface"""
    return RedirectResponse(url="/Pages/dashboard.html")

@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots():
    """Compliance: Prevent search engines from indexing API routes."""
    return "User-agent: *\nDisallow: /syllabus/\nDisallow: /courses/\nDisallow: /session/"

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
async def health(
    pg: PostgresRepo = Depends(get_postgres_repo),

    neo4j: Neo4jRepoImpl = Depends(get_neo4j_repo)
):
    """Full system health: DBs + agents."""
    # If the repo was None (failed init), try one more time via dependency logic
    import Application.API.dependencies as deps
    if pg is None and deps._postgres_repo is None:
        pg = next(get_postgres_repo())

    try:
        # Postgres health w/ retry
        if pg:
            for attempt in range(3):
                try:
                    with pg.get_cursor() as cur:
                        cur.execute("SELECT 1")
                    pg_status = {'status': 'ready', 'message': 'Postgres connected'}
                    break
                except Exception as e:
                    if attempt == 2:
                        pg_status = {'status': 'error', 'message': str(e)}
                    else:
                        time.sleep(1)
            else:
                pg_status = {'status': 'error', 'message': 'Retries exhausted'}
        else:
            pg_status = {'status': 'down', 'message': 'Not initialized'}

# Astra health w/ retry
        astra_status = {'status': 'down', 'message': 'Not initialized'}
        try:
            astra = next(get_astra_repo())
            if astra:
                for attempt in range(3):
                    try:
                        # Lighter check: init success, no embedding/search
                        assert astra.vector_store is not None
                        astra_status = {'status': 'ready', 'provider': 'AstraDB'}
                        break
                    except Exception as e:
                        if attempt == 2:
                            astra_status = {'status': 'error', 'message': str(e)}
                        else:
                            time.sleep(1)
                else:
                    astra_status = {'status': 'error', 'message': 'Retries exhausted'} 
        except Exception as e:
            astra_status = {'status': 'error', 'message': str(e)}
        
        # Neo4j health w/ retry
        if neo4j:
            for attempt in range(3):
                try:
                    database = os.getenv('NEO4J_DATABASE', 'neo4j')
                    with neo4j.driver.session(database=database) as session:
                        list(session.run('RETURN 1'))
                        result2 = list(session.run('MATCH (t:Topic) RETURN t LIMIT 1'))
                    neo4j_status = {'status': 'ready', 'topics_count': len(result2)}
                    break
                except Exception as e:
                    if attempt == 2:
                        neo4j_status = {'status': 'error', 'message': str(e)}
                    else:
                        time.sleep(1)
            else:
                neo4j_status = {'status': 'error', 'message': 'Retries exhausted'}
        else:
            neo4j_status = {'status': 'down', 'message': 'Not initialized'}
        
        # Agents
        try:
            agents = get_real_agents()
            agent_status = 'ready'
        except Exception as e:
            agent_status = f'degraded: {str(e)}'
        
        return {
            'status': 'healthy' if all(s.get('status') != 'error' for s in [pg_status, neo4j_status]) else 'degraded',
'dbs': {'postgres': pg_status, 'neo4j': neo4j_status, 'astra': astra_status},
            'agents': agent_status,
            'pipeline': 'ready'
        }
    except Exception as e:
        return {'status': 'degraded', 'error': str(e)}

print("🎓 Real course builder live at http://localhost:8000/Pages/test_interface.html")
