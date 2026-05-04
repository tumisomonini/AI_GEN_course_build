"""
Scraper core module providing a stateful Scraper class with initialized resources.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import time
import json
import re
import concurrent.futures

import requests
import redis
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

from Application.Infrastructure.ETL.cleaner import clean_raw_text, clean_syllabus_dict, log_cleaning_stats
from Application.Infrastructure.Scraper.web_scraper import scrape_web_syllabus
from Application.Infrastructure.Scraper.pdf_scraper import scrape_pdf_syllabus

# Load environment variables
_ENV_PATH = Path(__file__).resolve().parents[3] / '.env'
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


class Scraper:
    """
    Stateful scraper that initializes reusable resources on instantiation.

    Attributes:
        headless (bool): Whether Playwright runs headless.
        user_agent (str): Default User-Agent string.
        timeout (int): Default request/page timeout in seconds.
        redis_client (redis.Redis|None): Connected Redis client or None.
        session (requests.Session): Reusable HTTP session.
        _playwright: Playwright instance (created lazily).
        _browser: Playwright browser instance (created lazily).
        _context: Playwright browser context (created lazily).
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        headless: bool = True,
        user_agent: Optional[str] = None,
        timeout: int = 30,
    ):
        self.headless = headless
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        )
        self.timeout = timeout

        # Reusable HTTP session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        # Redis initialization
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception:
            self.redis_client = None

        # Pooled Playwright resources
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    # ------------------------------------------------------------------
    # Lazy Playwright helpers
    # ------------------------------------------------------------------
    def _ensure_browser(self):
        """Create Playwright browser/context on first use."""
        if self._browser is None or self._browser.is_closed():
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1920, "height": 1080},
            )
        return self._browser, self._context

    # ------------------------------------------------------------------
    # Core scrape methods
    # ------------------------------------------------------------------
    def scrape_web(self, url: str) -> str:
        """Scrape a web page using the reusable browser context."""
        if 'wikipedia.org' in url.lower():
            raise ValueError("Wikipedia is blocked - use technical sites like realpython, freecodecamp, docs")

        _, context = self._ensure_browser()
        page = context.new_page()
        try:
            for attempt in range(2):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                    break
                except Exception:
                    if attempt == 1:
                        raise
                    time.sleep(2)
            html_content = page.content()
        finally:
            page.close()

        soup = BeautifulSoup(html_content, "html.parser")
        syllabus_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td'])
        lines = [tag.get_text(strip=True) for tag in syllabus_tags if tag.get_text(strip=True)]
        return "\n".join(lines)

    def scrape_pdf(self, url: str) -> str:
        """Scrape a PDF using the reusable HTTP session."""
        response = self.session.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(response.content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def scrape_technical_website(self, url: str) -> Dict[str, Any]:
        """
        Robust scraper for any technical website (skip Wikipedia).
        Returns structured {title, description, headings: [{heading, level, content}]}
        """
        if 'wikipedia.org' in url.lower():
            return {"error": "Wikipedia blocked - use technical sites like realpython, freecodecamp, docs"}

        _, context = self._ensure_browser()
        page = context.new_page()
        try:
            for attempt in range(2):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                    break
                except Exception:
                    if attempt == 1:
                        raise
                    time.sleep(2)
            html_content = page.content()
        finally:
            page.close()

        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.find('title').get_text().strip() if soup.find('title') else "No title"
        desc = soup.find('meta', property='og:description') or soup.find('meta', name='description')
        description = desc['content'] if desc else ""

        headings = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = tag.get_text().strip()
            if heading_text:
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
                    "content": content[:3]
                })

        return {
            "title": title,
            "description": description[:500],
            "headings": headings[:10],
            "quality": len(headings) * 10,
            "sources": [{"title": title, "url": url}]
        }

    # ------------------------------------------------------------------
    # Search + scrape workflow
    # ------------------------------------------------------------------
    def search_and_scrape(self, course_title: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Dynamic syllabus scraping based on course title/query.
        1. DDG search for syllabi
        2. Scrape top web/PDF results
        3. Parse and return structured syllabus dictionaries with metadata
        """
        syllabi = []

        # 0. Check Cache
        cache_key = f"scraper_cache:{course_title.lower().strip()}"
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    print(f"🎯 Cache hit for '{course_title}'")
                    return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
            except Exception as e:
                print(f"⚠️ Redis cache read failed: {e}")

        try:
            if DDGS is None:
                print("⚠️ duckduckgo-search is not installed. Skipping search discovery.")
                return [{'error': 'Search dependency missing. Run pip install duckduckgo-search', 'quality_score': 0}]

            search_query = f'{course_title} course syllabus topics outline'
            ddgs_instance = DDGS()
            results = list(ddgs_instance.text(search_query, max_results=max_results))

            def _process_result(result):
                url = result.get('href', '')
                source_title = result.get('title', 'Unknown')
                try:
                    if 'pdf' in url.lower():
                        cleaned_raw, raw_stats = clean_raw_text(self.scrape_pdf(url))
                    else:
                        cleaned_raw, raw_stats = clean_raw_text(self.scrape_web(url))
                    log_cleaning_stats(raw_stats, 'scrape')

                    from Application.Ports.scraper import parse_syllabus
                    structured_dict = parse_syllabus(cleaned_raw)
                    structured_dict['source_url'] = url
                    structured_dict['source_title'] = source_title

                    cleaned_struct, struct_stats = clean_syllabus_dict(structured_dict)
                    log_cleaning_stats({'structured': struct_stats}, 'parse')

                    topic_count = len(cleaned_struct.get('main_topics', []))
                    obj_count = len(cleaned_struct.get('learning_objectives', []))
                    cleaned_struct['quality_score'] = (topic_count * 10) + (obj_count * 5)
                    cleaned_struct['_cleaning_stats'] = {'raw': raw_stats, 'structured': struct_stats}
                    return cleaned_struct
                except Exception as scrape_err:
                    return {
                        'error': str(scrape_err),
                        'source_url': url,
                        'source_title': source_title,
                        'quality_score': 0
                    }

            max_workers = 5
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_process_result, result) for result in results]
                for future in concurrent.futures.as_completed(futures, timeout=15):
                    try:
                        syllabi.append(future.result())
                    except Exception as e:
                        syllabi.append({'error': f'Unexpected scrape thread failure: {e}', 'quality_score': 0})

            syllabi.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            final_results = syllabi[:3]

            if self.redis_client and final_results:
                try:
                    self.redis_client.set(cache_key, json.dumps(final_results), ex=86400)
                except Exception as e:
                    print(f"⚠️ Redis cache write failed: {e}")

            return final_results

        except Exception as e:
            return [{'error': f'Search/scrape failed: {str(e)}', 'course_title': course_title}]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self):
        """Gracefully close all initialized resources."""
        if self._browser and not self._browser.is_closed():
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._context = None
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

