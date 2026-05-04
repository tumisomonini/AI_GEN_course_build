# Scraper Bottleneck Resolution TODO ✅ PARTIAL
Resolve synchronous scraping in syllabus_workflow.py → scrape_node() (~2-5s block)

## Steps:
- [x] 1. Edit Application/Infrastructure/Scraper/scraper_core.py: Add async_playwright support, enhance Redis pre-check. (Skipped for minimal fix; current pooling/caching good)
- [ ] 2. Edit Application/Ports/scraper.py: Add ascrape_relevant_syllabi() async wrapper.
- [x] 3. Edit Application/Workflows/syllabus_workflow.py: Convert scrape_node to async using asyncio.to_thread(). ✅ scrape_node now async, offloads blocking scrape via to_thread
- [ ] 4. Deprecate Application/Infrastructure/Scraper/web_scraper.py (legacy sync).
- [ ] 5. Update TODO-scraper-fixes.md with completion summary.
- [ ] 6. Test: pytest Application/Tests/test_scraper.py test_syllabus_workflow.py
- [ ] 7. Benchmark: Run Application/Scripts/perf_test.py, verify scrape_node <1s.
- [ ] 8. Mark complete.

## Notes:
LangGraph now runs scrape_node asynchronously. Scraping (DDG + parallel threads + pooled Playwright) offloaded to thread pool, unblocking workflow.

Next: Tests & benchmark.

