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
from Application.API.dependencies import get_postgres_repo, get_astra_repo, get_neo4j_repo, sanitize_neo4j_uri
from Application.API.agents import get_real_agents
from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.Astra_repo import AstraRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Init repos
    print("🚀 Starting full infrastructure...")
    import Application.API.dependencies as deps
    from Domain.knowledge_graphy import KnowledgeGraph
    
    try:
        deps._postgres_repo = PostgresRepo()
        # Explicit schema verification
        deps._postgres_repo.init_schema()
        print("✅ Postgres ready with schema")
    except Exception as e:
        deps._postgres_repo = None
        print(f"⚠️ Postgres skipped/failed: {e}")

    if os.getenv("ASTRA_DB_APPLICATION_TOKEN"):
        deps._astra_repo = AstraRepo()
        print("✅ AstraDB ready")
    else:
        deps._astra_repo = None
        print("⚠️ Astra skipped - set ASTRA_DB_APPLICATION_TOKEN")
    
    # Use centralized init for consistency
    deps.init_neo4j_singleton()
    
    # Auto-populate Neo4j sample data using the shared driver
    if deps._neo4j_repo:
        try:
            kg = KnowledgeGraph(deps._neo4j_repo.driver, database)
            kg.add_topic("Python Basics", "Fundamental syntax and data types")
            kg.add_topic("Data Structures", "Lists, dicts, sets")
            kg.add_prerequisite("Data Structures", "Python Basics")
            print("✅ Neo4j populated with sample KG data")
        except Exception as e:
            print(f"⚠️ Neo4j population skipped: {e}")
    
    print("✅ Infrastructure fully initialized")
    
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
    return RedirectResponse(url="/Pages/dashboard.html")

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
        # Postgres health
        if pg:
            try:
                # Simple ping to verify connectivity
                with pg.get_cursor() as cur:
                    cur.execute("SELECT 1")
                pg_status = {'status': 'ready', 'message': 'Postgres connected'}
            except Exception as e:
                pg_status = {'status': 'error', 'message': str(e)}
        else:
            pg_status = {'status': 'down', 'message': 'Not initialized'}

        # Astra health
        if astra:
            try:
                # Safeguard against uninitialized vector_store within AstraRepo
                if not hasattr(astra, 'vector_store') or astra.vector_store is None:
                    astra_status = {'status': 'down', 'message': 'Vector store not initialized'}
                elif not os.getenv("ASTRA_DB_APPLICATION_TOKEN"):
                    astra_status = {'status': 'error', 'message': 'Missing Astra Token in environment'}
                else:
                    # Perform a lightweight check without full similarity search if possible, 
                    # or a very specific test query.
                    try:
                        results = astra.similarity_search('test', k=1)
                        astra_status = {'status': 'ready', 'collection_count': len(results) if results is not None else 0}
                    except AttributeError:
                        astra_status = {'status': 'error', 'message': 'Astra driver misconfigured (NoneType error)'}
            except Exception as e:
                astra_status = {'status': 'error', 'message': str(e)}
        else:
            astra_status = {'status': 'down', 'message': 'Not initialized'}
        
        # Neo4j health
        if neo4j:
            try:
                database = os.getenv('NEO4J_DATABASE', 'neo4j')
                with neo4j.driver.session(database=database) as session:
                    result = list(session.run('RETURN 1'))  # Basic ping first
                    result2 = list(session.run('MATCH (t:Topic) RETURN t LIMIT 1'))
                    neo4j_status = {'status': 'ready', 'topics_count': len(result2)}
            except Exception as e:
                neo4j_status = {'status': 'error', 'message': str(e)}
        else:
            neo4j_status = {'status': 'down', 'message': 'Not initialized'}
        
        # Agents
        try:
            agents = get_real_agents()
            agent_status = 'ready'
        except Exception as e:
            agent_status = f'degraded: {str(e)}'
        
        return {
            'status': 'healthy' if all(s.get('status') != 'error' for s in [pg_status, astra_status, neo4j_status]) else 'degraded',
            'dbs': {'postgres': pg_status, 'astra': astra_status, 'neo4j': neo4j_status},
            'agents': agent_status,
            'pipeline': 'fully_integrated'
        }
    except Exception as e:
        return {'status': 'degraded', 'error': str(e)}

print("🎓 Real course builder live at http://localhost:8000/Pages/test_interface.html")
