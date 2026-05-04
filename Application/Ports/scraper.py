from typing import TYPE_CHECKING, Dict, Any, List
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
from Application.Infrastructure.Scraper.scraper_core_fixed import Scraper

if TYPE_CHECKING:
    from Domain.syllabus import Syllabus

# Global lazy-initialized scraper instance
_default_scraper: Scraper | None = None


def get_scraper() -> Scraper:
    """Return the default initialized Scraper instance (created lazily)."""
    global _default_scraper
    if _default_scraper is None:
        _default_scraper = Scraper()
    return _default_scraper


def scrape_technical_website(url: str) -> Dict[str, Any]:
    """
    Robust scraper for any technical website (skip Wikipedia)
    Returns structured {title, description, sections: [{heading, content}]}
    """
    return get_scraper().scrape_technical_website(url)

# Lines that look like navigation/UI noise rather than course topics
_JUNK_PATTERNS = re.compile(
    r'^(\d+|[^a-zA-Z]+|.{0,4}|.{120,})$'  # too short, too long, or no letters
    r'|(search|login|sign in|cookie|privacy|copyright|menu|navigation|home|contact|about us|cart|checkout|subscribe)',
    re.IGNORECASE
)

def _is_valid_topic(line: str) -> bool:
    """Return True only for lines that look like real course topic titles."""
    line = line.strip()
    # Check junk patterns and filter out common navigation text
    if _JUNK_PATTERNS.search(line) or any(nav in line.lower() for nav in ["click here", "read more", "view all"]):
        return False
    # Must have at least 2 words or be a known topic pattern
    words = line.split()
    if len(words) < 2 and not re.match(r'^(week|module|unit|topic|chapter)\s*\d+', line.lower()):
        return False
    # Reject lines that are mostly digits/symbols
    alpha_ratio = sum(c.isalpha() for c in line) / max(len(line), 1)
    return alpha_ratio > 0.5

def parse_syllabus(raw_syllabus: str) -> Dict[str, List[str]]:
    """
    Parse raw syllabus text into structured format with topics and subtopics
    """
    lines = [line.strip() for line in raw_syllabus.split('\n') if line.strip()]

    structured_syllabus: Dict[str, List[str]] = {
        "main_topics": [],
        "learning_objectives": [],
        "prerequisites": [],
        "assessment_methods": []
    }

    for line in lines:
        if re.match(r'^(week|module|unit|topic|chapter)\s*\d+', line.lower()):
            structured_syllabus["main_topics"].append(line)
        elif any(kw in line.lower() for kw in ['learning objective', 'student will', 'upon completion']):
            structured_syllabus["learning_objectives"].append(line)
        elif any(kw in line.lower() for kw in ['prerequisite', 'requirement', 'background']):
            structured_syllabus["prerequisites"].append(line)
        elif any(kw in line.lower() for kw in ['assessment', 'exam', 'quiz', 'assignment', 'grade']):
            structured_syllabus["assessment_methods"].append(line)
        elif _is_valid_topic(line):
            structured_syllabus["main_topics"].append(line)

    # Deduplicate
    for key in structured_syllabus:
        structured_syllabus[key] = list(dict.fromkeys(structured_syllabus[key]))

    return structured_syllabus

def scrape_relevant_syllabi(course_title: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Dynamic syllabus scraping based on course title/query.
    Delegates to the initialized Scraper instance.
    """
    return get_scraper().search_and_scrape(course_title, max_results=max_results)
