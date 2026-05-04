from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from .course import Chapter, Course

class SyllabusValidation(BaseModel):
    is_valid: bool
    missing_prerequisites: List[str] = []
    issues: List[str] = []

class SyllabusState(BaseModel):
    title: str = Field(..., min_length=3)
    run_id: int = 0
    level: str = "beginner"
    duration_months: int = 3
    topics: List[str] = Field(default_factory=list)
    syllabus: List[str] = Field(default_factory=list)
    # Changed from Dict[str, str] to support metadata like status and order.
    chapters: List[Chapter] = Field(default_factory=list)
    scraped_syllabi: Optional[List[Any]] = None
    validated: bool = False
    generation_time: float = 0.0
    reviewer_semantic_avg: float = 0.0
    semantic_pass_rate: float = 0.0
    
    # Removed topics_must_be_non_empty validator.
    # The scrape_node is responsible for populating topics. 
    # Validating non-empty here prevents the workflow from starting 
    # when topics are discovered dynamically.
    
    @field_validator('title')
    @classmethod
    def title_must_be_meaningful(cls, v):
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError('Title must be at least 3 characters long')
        return cleaned

class Syllabus(BaseModel):
    title: str
    course: Course
    chapters: List[Chapter] = []
    
    def validate(self, prereq_graph: Optional[Dict[str, List[str]]] = None) -> SyllabusValidation:
        """Rich domain validation"""
        issues = []
        if len(self.title.strip()) < 3:
            issues.append("Title too short")
        
        missing_prereqs = []
        is_valid = len(issues) == 0 and len(missing_prereqs) == 0
        return SyllabusValidation(
            is_valid=is_valid,
            missing_prerequisites=missing_prereqs,
            issues=issues
        )
    
    @classmethod
    def from_scraped_dict(cls, data: Dict[str, Any]) -> 'Syllabus':
        """Factory from scraper output"""
        chapters = []
        for topic in data.get('main_topics', []):
            chapters.append(Chapter(title=str(topic)[:100], content=str(topic)[:500]))
        for obj in data.get('learning_objectives', []):
            chapters.append(Chapter(title=str(obj)[:100], content=str(obj)[:500]))
        
        title = data.get('source_title') or data.get('title') or 'Untitled'
        course = Course(title=title, audience='general', outcomes=[])
        return cls(title=title, course=course, chapters=chapters[:10])
    
    @classmethod
    def from_state(cls, state: SyllabusState) -> 'Syllabus':
        """Convert workflow state to final Syllabus"""
        chapters = sorted(state.chapters, key=lambda x: x.chapter_order)
        course = Course(title=state.title, audience='general', outcomes=state.syllabus)
        return cls(title=state.title, course=course, chapters=chapters)
