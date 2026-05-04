# Scraper Initialization Plan

## Information Gathered
- `Application/Ports/scraper.py` exposes module-level functions (`scrape_relevant_syllabi`, `parse_syllabus`, `scrape_technical_website`) with no class or `__init__`.
- `Application/Infrastructure/Scraper/web_scraper.py` launches/tears down a Playwright browser on every call.
- `Application/Infrastructure/Scraper/pdf_scraper.py` creates a fresh `requests.get` on every call.
- `Application/API/Endpoints/courses.py` has a stub `InlineScraper` with no `__init__`.
- `Application/Tests/test_scraper.py` monkey-patches module-level names.
- Redis client in `Application/Ports/scraper.py` connects at import time with silent fallback.

## Plan
1. **Create `Application/Infrastructure/Scraper/scraper_core.py`**
   - Define a `Scraper` class with `__init__(self, redis_url=None, headless=True)`.
   - Initialize: Playwright browser (reusable), `requests.Session()`, Redis client, config (UA, timeouts).
   - Add methods: `scrape_web(url)`, `scrape_pdf(url)`, `search_and_scrape(course_title, max_results)`, `close()`.

2. **Update `Application/Infrastructure/Scraper/web_scraper.py`**
   - Refactor `scrape_web_syllabus` to accept optional `browser`/`context` args so the class can inject its reusable browser.
   - Keep backward-compatible standalone function signature.

3. **Update `Application/Infrastructure/Scraper/pdf_scraper.py`**
   - Refactor to accept optional `session` arg; fallback to `requests.get` if not provided.

4. **Update `Application/Ports/scraper.py`**
   - Import `Scraper` from `scraper_core`.
   - Provide module-level `_default_scraper = None` and `get_scraper()` lazy initializer.
   - Keep existing function signatures as thin wrappers around the default scraper instance.

5. **Update `Application/API/Endpoints/courses.py`**
   - Replace stub `InlineScraper` with one that calls `get_scraper()` and actually initializes.

6. **Update `Application/Tests/test_scraper.py`**
   - Add `test_scraper_initialization()` asserting `get_scraper()` returns a `Scraper` with expected attributes.
   - Adjust monkey-patching to target `scraper_core` methods if needed.

## Dependent Files
- `Application/Infrastructure/Scraper/scraper_core.py` (new)
- `Application/Infrastructure/Scraper/web_scraper.py`
- `Application/Infrastructure/Scraper/pdf_scraper.py`
- `Application/Ports/scraper.py`
- `Application/API/Endpoints/courses.py`
- `Application/Tests/test_scraper.py`

## Follow-up Steps
- Run `pytest Application/Tests/test_scraper.py -v` to verify initialization and existing tests still pass.

