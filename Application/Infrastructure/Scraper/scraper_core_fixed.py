"""
Scraper core module providing a stateful Scraper class with initialized resources.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import json
import re
import asyncio
import concurrent.futures
import requests
import redis
try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    _HTTPX_AVAILABLE = False
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

try:
    from ddgs import DDGS as _DDGS
    _DDGS_AVAILABLE = True
except ImportError:
    _DDGS = None  # type: ignore[assignment]
    _DDGS_AVAILABLE = False

from Application.Infrastructure.ETL.cleaner import clean_raw_text, clean_syllabus_dict, log_cleaning_stats
from Application.Infrastructure.Scraper.web_scraper import scrape_web_syllabus
from Application.Infrastructure.Scraper.pdf_scraper import scrape_pdf_syllabus

from Application.Infrastructure.Scraper.llm_triage import triage_results


# Load environment variables
_ENV_PATH = Path(__file__).resolve().parents[3] / '.env'
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


class Scraper:
    # Class-level defaults so tests can monkeypatch attributes on the type.
    redis_client = None
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

        # Async Playwright resources (created per-call, no shared state)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    # ------------------------------------------------------------------
    # Async Playwright helpers
    # ------------------------------------------------------------------
    async def _fetch_page_html(self, url: str) -> str:
        """Fetch page HTML using async Playwright. Launches a fresh context per call."""
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            try:
                for attempt in range(2):
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                        break
                    except Exception:
                        if attempt == 1:
                            raise
                        await asyncio.sleep(1)
                return await page.content()
            finally:
                await page.close()
                await browser.close()

    # ------------------------------------------------------------------
    # Core scrape methods
    # ------------------------------------------------------------------
    async def scrape_web_async(self, url: str) -> str:
        """Async scrape a web page."""
        if 'wikipedia.org' in url.lower():
            raise ValueError("Wikipedia is blocked - use technical sites like realpython, freecodecamp, docs")
        html_content = await self._fetch_page_html(url)
        soup = BeautifulSoup(html_content, "html.parser")
        lines = [tag.get_text(strip=True) for tag in soup.find_all(['h1','h2','h3','h4','h5','h6','p','li','td']) if tag.get_text(strip=True)]
        return "\n".join(lines)

    def scrape_web(self, url: str) -> str:
        """Sync wrapper around async scrape_web_async."""
        return asyncio.run(self.scrape_web_async(url))

    def scrape_pdf(self, url: str) -> str:
        """Scrape a PDF using the reusable HTTP session."""
        response = self.session.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(response.content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _fetch_pdf_bytes_sync(self, url: str) -> bytes:
        response = self.session.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        return response.content

    async def _fetch_pdf_bytes(self, url: str) -> bytes:
        if _HTTPX_AVAILABLE and httpx is not None:
            async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        return await asyncio.to_thread(self._fetch_pdf_bytes_sync, url)

    async def scrape_pdf_async(self, url: str) -> str:
        """Async wrapper for PDF scraping."""
        pdf_bytes = await self._fetch_pdf_bytes(url)
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    async def scrape_technical_website_async(self, url: str) -> Dict[str, Any]:
        """Async robust scraper for any technical website."""
        if 'wikipedia.org' in url.lower():
            return {"error": "Wikipedia blocked - use technical sites like realpython, freecodecamp, docs"}
        html_content = await self._fetch_page_html(url)
        soup = BeautifulSoup(html_content, "html.parser")
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "No title"
        desc = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'description'})
        description = str(desc.get('content', '')) if desc else ""
        headings = []
        for tag in soup.find_all(['h1','h2','h3','h4','h5','h6']):
            heading_text = tag.get_text().strip()
            if heading_text:
                content = []
                sibling = tag.find_next_sibling()
                while sibling and sibling.name not in ['h1','h2','h3','h4','h5','h6','div']:
                    if sibling.name == 'p':
                        p_text = sibling.get_text().strip()
                        if p_text:
                            content.append(p_text)
                    sibling = sibling.find_next_sibling()
                headings.append({"heading": heading_text, "level": tag.name, "content": content[:3]})
        return {
            "title": title,
            "description": description[:500],
            "headings": headings[:10],
            "quality": len(headings) * 10,
            "sources": [{"title": title, "url": url}]
        }

    def scrape_technical_website(self, url: str) -> Dict[str, Any]:
        """Sync wrapper around async scrape_technical_website_async."""
        return asyncio.run(self.scrape_technical_website_async(url))

    # ------------------------------------------------------------------
    # Search + scrape workflow
    # ------------------------------------------------------------------
    async def search_and_scrape_async(self, course_title: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Async syllabus scraping: DDG search + parallel async Playwright page fetches.

        Latency improvement: optional LLM triage to decide which search results are worth
        fully scraping (Playwright/PDF). If LLM is disabled or fails, fall back to the
        original behavior.
        """
        cache_key = f"scraper_cache:{course_title.lower().strip()}"

        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data and isinstance(cached_data, str):
                    print(f"🎯 Cache hit for '{course_title}'")
                    return json.loads(cached_data)
            except Exception as e:
                print(f"⚠️ Redis cache read failed: {e}")

        if not _DDGS_AVAILABLE or _DDGS is None:
            return [{'error': 'Search dependency missing. Run pip install duckduckgo-search', 'quality_score': 0}]

        # Candidate search: Serpapi (preferred) -> DDG (fallback)
        try:
            search_query = f'{course_title} course syllabus topics outline'

            serpapi_key = os.getenv("SERPAPI_API_KEY")
            if serpapi_key:
                from Application.Infrastructure.Scraper.serpapi_search import serpapi_search
                serp_results = await asyncio.to_thread(
                    lambda: serpapi_search(search_query, max_results=max_results)
                )

                # Expect dicts with 'href' and 'title'
                results = [
                    {
                        'href': r.get('href', ''),
                        'title': r.get('title', 'Unknown'),
                    }
                    for r in (serp_results or [])
                    if r.get('href')
                ]

                if not results:
                    raise RuntimeError("Serpapi returned no results")
            else:
                raise RuntimeError("SERPAPI_API_KEY not set")

        except Exception:
            try:
                if not _DDGS_AVAILABLE or _DDGS is None:
                    return [{'error': 'Search dependency missing. Install serpapi or duckduckgo-search', 'quality_score': 0}]

                search_cls = _DDGS
                assert search_cls is not None
                results = await asyncio.to_thread(
                    lambda: list(search_cls().text(search_query, max_results=max_results))
                )
            except Exception as e:
                return [{'error': f'Search failed: {e}', 'quality_score': 0}]


        # ---------------- LLM triage (optional) ----------------
        # Decide which results to fully scrape to reduce Playwright latency.
        try:
            triage_top_k = min(max_results, int(os.getenv("LLM_TRIAGE_TOP_K", "2")))
        except Exception:
            triage_top_k = min(max_results, 2)

        # LLM triage can be disabled for tests or deployments.
        # If disabled, keep original behavior.
        llm_enabled = os.getenv("LLM_TRIAGE_ENABLED", "").strip().lower() in {"1", "true", "yes"}

        # Always define filtered_results to avoid UnboundLocalError when triage is disabled.
        filtered_results = results

        if llm_enabled:
            try:
                triage = await asyncio.to_thread(
                    triage_results,
                    course_title=course_title,
                    results=results,
                    select_top_k=triage_top_k,
                )
                selected_indices = set(triage.selected_indices)
            except Exception:
                selected_indices = set(range(min(triage_top_k, len(results))))

            triaged_results = [r for i, r in enumerate(results) if i in selected_indices]
            # If triage returned nothing usable, keep original behavior.
            if triaged_results:
                filtered_results = triaged_results
                results = filtered_results




        async def _process_result(result):
            url = result.get('href', '')
            source_title = result.get('title', 'Unknown')
            try:
                if 'pdf' in url.lower():
                    raw = await self.scrape_pdf_async(url)
                else:
                    raw = await self.scrape_web_async(url)
                cleaned_raw, raw_stats = clean_raw_text(raw)
                log_cleaning_stats(raw_stats, 'scrape')
                from Application.Ports.scraper import parse_syllabus
                structured_dict = parse_syllabus(cleaned_raw)
                structured_dict['source_url'] = url
                structured_dict['source_title'] = source_title
                cleaned_struct, struct_stats = clean_syllabus_dict(structured_dict)
                log_cleaning_stats({'structured': struct_stats}, 'parse')
                topic_count = len(cleaned_struct.get('main_topics', []))
                obj_count = len(cleaned_struct.get('learning_objectives', []))
                cleaned_struct['quality_score'] = (topic_count * 10) + (obj_count * 5)  # type: ignore[assignment]
                cleaned_struct['_cleaning_stats'] = {'raw': raw_stats, 'structured': struct_stats}  # type: ignore[assignment]
                return cleaned_struct
            except Exception as scrape_err:
                return {'error': str(scrape_err), 'source_url': url, 'source_title': source_title, 'quality_score': 0}

        syllabi = await asyncio.gather(*[_process_result(r) for r in filtered_results])

        syllabi = sorted(syllabi, key=lambda x: x.get('quality_score', 0), reverse=True)
        final_results = syllabi[:3]

        # If we triaged to fewer candidates, keep return shape stable.
        # Caller expects up to 3 results.


        if self.redis_client and final_results:
            try:
                self.redis_client.set(cache_key, json.dumps(final_results), ex=86400)
            except Exception as e:
                print(f"⚠️ Redis cache write failed: {e}")

        return final_results

    def search_and_scrape(self, course_title: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Sync wrapper — runs the async scraper in the current or a new event loop."""
        try:
            try:
                loop = asyncio.get_running_loop()
                is_running = True
            except RuntimeError:
                is_running = False
            if is_running:
                # Already inside an async context (e.g. called via asyncio.to_thread)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.search_and_scrape_async(course_title, max_results))
                    return future.result(timeout=60)
            return asyncio.run(self.search_and_scrape_async(course_title, max_results))
        except Exception as e:
            return [{'error': f'Search/scrape failed: {str(e)}', 'course_title': course_title}]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self):
        """Gracefully close reusable HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

