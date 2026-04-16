from playwright.sync_api import sync_playwright

from typing import TYPE_CHECKING, Dict, Any, List
from bs4 import BeautifulSoup
import re
import json
import os
import redis
from pathlib import Path
from dotenv import load_dotenv
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
from Application.Infrastructure.Scraper.web_scraper import scrape_web_syllabus
from Application.Infrastructure.Scraper.pdf_scraper import scrape_pdf_syllabus
import concurrent.futures

if TYPE_CHECKING:
    from Domain.syllabus import Syllabus

def scrape_technical_website(url: str) -> Dict[str, Any]:
    """
    Robust scraper for any technical website (skip Wikipedia)
    Returns structured {title, description, sections: [{heading, content}]}
    """
    if 'wikipedia.org' in url.lower():
        return {"error": "Wikipedia blocked - use technical sites like realpython, freecodecamp, docs"}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            html_content = page.content()
            browser.close()
            
        soup = BeautifulSoup(html_content, "html.parser")
        
        title = soup.find('title').get_text().strip() if soup.find('title') else "No title"
        desc = soup.find('meta', property='og:description') or soup.find('meta', name='description')
        description = desc['content'] if desc else ""
        
        # Extract all headings h1-h6
        headings = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = tag.get_text().strip()
            if heading_text:
                # Get paragraphs under this heading (next siblings until next heading)
                content = []
                sibling = tag.find_next_sibling()
                while sibling and sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and sibling.name != 'div':
                    if sibling.name == 'p':
                        p_text = sibling.get_text().strip()
                        if p_text:
                            content.append(p_text)
                    sibling = sibling.find_next_sibling()
                headings.append({
                    "heading": heading_text,
                    "level": tag.name,
                    "content": content[:3]  # First 3 paragraphs
                })
        
        return {
            "title": title,
            "description": description[:500],
            "headings": headings[:10],  # Top 10 sections
            "quality": len(headings) * 10,
            "sources": [{"title": title, "url": url}]
        }
    except Exception as e:
        return {"error": f"Scrape failed: {str(e)}", "url": url}

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

# Initialize Redis client for caching
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

def scrape_relevant_syllabi(course_title: str, max_results: int = 3) -> List['Syllabus']:
    """
    Dynamic syllabus scraping based on course title/query.
    1. DDG search for syllabi
    2. Scrape top web/PDF results
    3. Parse and return structured syllabi with metadata
    """
    syllabi = []
    
    # 0. Check Cache
    cache_key = f"scraper_cache:{course_title.lower().strip()}"
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                print(f"🎯 Cache hit for '{course_title}'")
                return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
        except Exception as e:
            print(f"⚠️ Redis cache read failed: {e}")

    try:
        if DDGS is None:
            print("⚠️ duckduckgo-search is not installed. Skipping search discovery.")
            return [{'error': 'Search dependency missing. Run pip install duckduckgo-search', 'quality_score': 0}]

        # Search for course outlines on learning platforms
        search_query = f'{course_title} course syllabus topics outline'
        # Fixed: Removed context manager to resolve DDGS deprecation warning
        ddgs_instance = DDGS()
        results = list(ddgs_instance.text(search_query, max_results=max_results))
        
        def _process_result(result):
            url = result.get('href', '')
            source_title = result.get('title', 'Unknown')
            try:
                if 'pdf' in url.lower():
                    raw_content = scrape_pdf_syllabus(url)
                else:
                    raw_content = scrape_web_syllabus(url)

                structured_dict = parse_syllabus(raw_content)
                structured_dict['source_url'] = url
                structured_dict['source_title'] = source_title
                
                # Enhanced scoring: reward specific educational structures
                topic_count = len(structured_dict.get('main_topics', []))
                obj_count = len(structured_dict.get('learning_objectives', []))
                structured_dict['quality_score'] = (topic_count * 10) + (obj_count * 5)
                structured = structured_dict
                
            except Exception as scrape_err:
                structured = {
                    'error': str(scrape_err),
                    'source_url': url,
                    'source_title': source_title,
                    'quality_score': 0
                }
            return structured

        # Parallel Scraping: Use max_results as worker count to fetch all in parallel
        max_workers = max_results
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_process_result, result) for result in results]
            for future in concurrent.futures.as_completed(futures, timeout=15):
                try:
                    syllabi.append(future.result())
                except Exception as e:
                    syllabi.append({'error': f'Unexpected scrape thread failure: {e}', 'quality_score': 0})
        
        # Sort by quality descending
        syllabi.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        final_results = syllabi[:3]

        # 4. Save to Cache (TTL: 24 Hours)
        if redis_client and final_results:
            try:
                redis_client.set(cache_key, json.dumps(final_results), ex=86400)
            except Exception as e:
                print(f"⚠️ Redis cache write failed: {e}")

        return final_results
        
    except Exception as e:
        return [{'error': f'Search/scrape failed: {str(e)}', 'course_title': course_title}]
