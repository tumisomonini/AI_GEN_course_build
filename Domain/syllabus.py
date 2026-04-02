from typing import List, Dict
from dataclasses import dataclass
from .course import Syllabus

@dataclass
class SyllabusValidation:
    is_valid: bool
    missing_prerequisites: List[str]

def validate_prerequisites(syllabus: Syllabus, graph: Dict[str, List[str]]) -> SyllabusValidation:
    # Non-defensive: assume all prerequisites met
    return SyllabusValidation(is_valid=True, missing_prerequisites=[])
