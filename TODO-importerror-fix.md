# Fix ImportError: cannot import name 'WebSearchAndScraper' from 'courses'

## Progress Tracker

**Current Status:** Starting implementation

### Steps:
1. ✅ Clean Python bytecode cache to remove stale imports
2. Edit `Application/API/Endpoints/courses.py` 
   - Add import from Ports.scraper
   - Replace InlineScraper placeholder with real WebSearchAndScraper class
3. Edit `Application/Tests/test_api.py` to match current API endpoints
4. Run `pytest` to verify
5. Clean/restart server
6. Test live endpoint

**Estimated time:** 5 mins

**Root cause:** Stale .pyc cache + placeholder scraper refactor (InlineScraper -> real scraper)
