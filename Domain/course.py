from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from typing import Literal

# Domain dataclasses (existing)
@dataclass
class Course:
    title: str
    audience: str
    outcomes: List[str]

@dataclass
class Chapter:
    title: str
    content: str

@dataclass
class Syllabus:
    course: Course
    chapters: List[Chapter]

# Pydantic models for API
class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    level: Literal["beginner", "intermediate", "advanced"]
    duration_months: int = Field(..., ge=1, le=12)
    audience: Optional[str] = None

class CourseTemplate(BaseModel):
    title: str
    level: str
    duration_months: int
    learning_objectives: List[str]
    prerequisites: List[str]
    chapters: List[Dict[str, Any]]

class ScrapingResult(BaseModel):
    is_real_data: bool = False
    total_sources: int = 0
    quality_score: int = 70
    total_content: str = "N/A"
    sources: List[Dict[str, str]] = []

class CourseReviewResponse(BaseModel):
    course_id: int
    template: CourseTemplate
    scraping_result: ScrapingResult = ScrapingResult()
    metadata: Dict[str, Any] = {}
    status: Literal["draft", "approved", "generating", "completed", "published", "rejected"] = "draft"

class ApproveRequest(BaseModel):
    approved: bool
    comments: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
