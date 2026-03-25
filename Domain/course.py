from dataclasses import dataclass
from typing import List

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