from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import traceback
from pathlib import Path

from Application.API.Endpoints.syllabus import router as syllabus_router
from Application.API.Endpoints.courses import router as courses_router
from Application.API.Endpoints.session import router as session_router
from Application.API.dependencies import get_postgres_repo, get_astra_repo, get_neo4j_repo
from Application.API.agents import get_real_agents
from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.Astra_repo import AstraRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Init repos
    print("🚀 Starting DB connections...")
    import Application.API.dependencies as deps
    
    deps._postgres_repo = PostgresRepo()
    if os.getenv("ASTRA_DB_APPLICATION_TOKEN"):
        deps._astra_repo = AstraRepo()
    else:
        deps._astra_repo = None
        print("⚠️ Astra repo skipped (token not set)")
    deps._neo4j_repo = Neo4jRepoImpl(
        os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        os.getenv('NEO4J_USERNAME', 'neo4j'),
        os.getenv('NEO4J_PASSWORD'),
        os.getenv('NEO4J_DATABASE')
    )
    # Optional: _postgres_repo.init_schema()
    print("✅ All DB repos initialized")
    
    yield
    
    # Shutdown
    print("🔌 Closing DB connections...")
    if deps._postgres_repo:
        deps._postgres_repo.close()
    if deps._neo4j_repo:
        deps._neo4j_repo.close()
    print("✅ DBs closed")

app = FastAPI(
    title="🚀 AI Course Builder API",
    description="Real scraping → RAG → AI course generation",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    return RedirectResponse(url="/Pages/test_interface.html")

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
    astra: AstraRepo = Depends(get_astra_repo),
    neo4j: Neo4jRepoImpl = Depends(get_neo4j_repo)
):
    """Full system health: DBs + agents."""
    try:
        # DB pings
        with pg.get_cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        pg_status = {'status': 'ready', 'message': 'Postgres connected'}

        astra_status = {'status': 'ready', 'collection_count': len(astra.similarity_search('test', k=1))}
        neo4j_status = {'topics_count': len(list(neo4j._session().run('MATCH (t:Topic) RETURN t LIMIT 1')))}
        
        # Agents
        agents = get_real_agents()
        
        return {
            'status': 'healthy',
            'dbs': {'postgres': pg_status, 'astra': astra_status, 'neo4j': neo4j_status},
            'agents': 'real',
            'pipeline': 'fully_integrated'
        }
    except Exception as e:
        return {'status': 'degraded', 'error': str(e)}

print("🎓 Real course builder live at http://localhost:8000/Pages/test_interface.html")
