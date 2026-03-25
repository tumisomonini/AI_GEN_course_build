from typing import List, Dict
from dataclasses import dataclass
from .course import Syllabus

@dataclass
class SyllabusValidation:
    is_valid: bool
    missing_prerequisites: List[str]

def validate_prerequisites(syllabus: Syllabus, graph: Dict[str, List[str]]) -> SyllabusValidation:
    missing = []
    for i, chapter in enumerate(syllabus.chapters):
        prerequisites = graph.get(chapter.title, [])
        if not all(p in [c.title for c in syllabus.chapters[:i]] for p in prerequisites):
            missing.extend(prerequisites)
    return SyllabusValidation(is_valid=len(missing) == 0, missing_prerequisites=missing)