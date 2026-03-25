from fastapi import FastAPI
from .endpoints.syllabus import router as syllabus_router

app = FastAPI()
app.include_router(syllabus_router, prefix="/syllabus")