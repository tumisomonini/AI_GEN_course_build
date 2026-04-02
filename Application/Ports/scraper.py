import requests
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import re
from duckduckgo_search import DDGS
from Application.Infrastructure.Scraper.web_scraper import scrape_web_syllabus
from Application.Infrastructure.Scraper.pdf_scraper import scrape_pdf_syllabus
import concurrent.futures

def scrape_technical_website(url: str) -> Dict[str, Any]:
    """
    Robust scraper for any technical website (skip Wikipedia)
    Returns structured {title, description, sections: [{heading, content}]}
    """
    if 'wikipedia.org' in url.lower():
        return {"error": "Wikipedia blocked - use technical sites like realpython, freecodecamp, docs"}
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
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

def parse_syllabus(raw_syllabus: str) -> Dict[str, List[str]]:
    """
    Parse raw syllabus text into structured format with topics and subtopics
    """
    lines = [line.strip() for line in raw_syllabus.split('\n') if line.strip()]
    
    structured_syllabus = {
        "main_topics": [],
        "learning_objectives": [],
        "prerequisites": [],
        "assessment_methods": []
    }
    
    current_section = None
    
    for line in lines:
        # Detect section headers
        if re.match(r'^(week|module|unit|topic|chapter)\s*\d+', line.lower()):
            structured_syllabus["main_topics"].append(line)
        elif any(keyword in line.lower() for keyword in ['learning objective', 'student will', 'upon completion']):
            structured_syllabus["learning_objectives"].append(line)
        elif any(keyword in line.lower() for keyword in ['prerequisite', 'requirement', 'background']):
            structured_syllabus["prerequisites"].append(line)
        elif any(keyword in line.lower() for keyword in ['assessment', 'exam', 'quiz', 'assignment', 'grade']):
            structured_syllabus["assessment_methods"].append(line)
        elif line and not line.startswith(('•', '-', '*')):
            # Likely a main topic
            structured_syllabus["main_topics"].append(line)
    
    # Remove duplicates and clean up
    for key in structured_syllabus:
        structured_syllabus[key] = list(set(structured_syllabus[key]))
    
    return structured_syllabus

def scrape_relevant_syllabi(course_title: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Dynamic syllabus scraping based on course title/query.
    1. DDG search for syllabi
    2. Scrape top web/PDF results
    3. Parse and return structured syllabi with metadata
    """
    syllabi = []
    
    try:
        # Search for syllabi: prioritize PDFs and edu sites
        search_query = f'syllabus "{course_title}" filetype:pdf OR site:.edu OR site:.ac.uk'
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(search_query, max_results=max_results)]
        def _process_result(result):
            url = result.get('href', '')
            source_title = result.get('title', 'Unknown')
            try:
                if 'pdf' in url.lower():
                    raw_content = scrape_pdf_syllabus(url)
                else:
                    raw_content = scrape_web_syllabus(url)

                structured = parse_syllabus(raw_content)
                structured['source_url'] = url
                structured['source_title'] = source_title
                structured['quality_score'] = len(structured.get('main_topics', [])) * 10 + len(structured.get('learning_objectives', [])) * 5
            except Exception as scrape_err:
                structured = {
                    'source_url': url,
                    'source_title': source_title,
                    'error': str(scrape_err),
                    'quality_score': 0
                }
            return structured

        max_workers = min(max_results, 10)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_process_result, result) for result in results]
            for future in concurrent.futures.as_completed(futures):
                try:
                    syllabi.append(future.result())
                except Exception as e:
                    syllabi.append({'error': f'Unexpected scrape thread failure: {e}', 'quality_score': 0})
        
        # Sort by quality descending
        syllabi.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        return syllabi[:3]  # Top 3
        
    except Exception as e:
        return [{'error': f'Search/scrape failed: {str(e)}', 'course_title': course_title}]
