from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .agents import initialize_agents
from .Endpoints.syllabus import router as syllabus_router
from .Endpoints.courses import router as courses_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize agents on startup
    initialize_agents()
    yield
    # Cleanup on shutdown (if needed)

app = FastAPI(
    title="AI_GEN Course Builder API",
    description="Agentic AI-powered course generation with full workflow",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pages_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Pages"))
if os.path.exists(pages_dir):
    app.mount("/Pages", StaticFiles(directory=pages_dir), name="pages")

app.include_router(syllabus_router, prefix="/syllabus", tags=["Syllabus"])
app.include_router(courses_router, prefix="/courses", tags=["Courses"])

@app.get("/", tags=["Frontend"])
async def root():
    return RedirectResponse(url="/Pages/test_interface.html")

print("FastAPI app ready!")
