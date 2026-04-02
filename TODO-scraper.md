# Dynamic Syllabus Scraping TODO

## Step 1: Install deps (duckduckgo-search for query-based URL discovery)
- execute `pip install duckduckgo-search`

## ✅ Step 2: Enhance Ports/scraper.py - Add scrape_relevant_syllabi(course_title: str) -> List[structured syllabi]
- Implemented DDGS search + scrape top 3 syllabi
- Search 'syllabus \"query\" filetype:pdf OR site:edu'
- Scrape top 3-5 URLs/PDFs using existing web/pdf scrapers
- Parse + return list of structured syllabi w/ source metadata

## ✅ Step 3: API Endpoints/syllabus.py - Add /scrape endpoint {title: str}
- Implemented POST /syllabus/scrape → scrape + upsert to 'user_syllabi' collection
- Enhanced /generate to accept optional title
- Call scraper.scrape_relevant_syllabus(title)
- Upsert to AstraDB (collection='user_syllabi')
- Return scraped data + store confirmation

## Step 4: Enhance /generate endpoint
- Accept optional title: str | topics: List[str]
- If title: scrape → extract topics → run workflow on extracted topics

## ✅ Step 5: Workflow/syllabus_workflow.py - Add scrape_node(state.title)
- Added scrape_node → DDGS search/scrape/upsert if title in state
- Updated SyllabusState + conditional edges to planner
- API /generate now passes title to workflow
- Integrate scrape before planner, inject scraped['main_topics'] to state.topics

## ✅ Step 6: Script/scrape_syllabus.py - Add --query arg
- Added --query → uses scrape_relevant_syllabi → CLI `python scrape_syllabus.py --query "Python Data Science"`
- Dynamic CLI: python scrape_syllabus.py --query "Python Data Science"

## Step 7: Test
- curl POST /syllabus/scrape {"title": "Machine Learning"}
- curl POST /syllabus/generate {"title": "Deep Learning"}
- Check AstraDB has scraped chunks

**Progress: 5/7**  - Workflow integrated w/ scraping
