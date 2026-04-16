from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from typing import Literal

# Domain dataclasses (existing)
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Course(BaseModel):
    title: str = Field(..., min_length=3)
    audience: str = "general"
    outcomes: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Course':
        return cls(
            title=data.get('title', 'Untitled'),
            audience=data.get('audience', 'general'),
            outcomes=data.get('outcomes', [])
        )

class Chapter(BaseModel):
    title: str
    content: str = ""
    
    @classmethod
    def from_scraped(cls, title: str, content: str) -> 'Chapter':
        return cls(title=title, content=content[:1000])  # Truncate long content

# Pydantic models for API
class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Course title must be at least 3 characters")
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
    status: Literal["draft", "approved", "generating", "completed"] = "draft"

class CourseGenerateRequest(BaseModel):
    topic: str
    usep_ai: bool = False
    max_time: int = 60


class ApproveRequest(BaseModel):
    approved: bool
    comments: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
