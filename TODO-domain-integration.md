# Domain Layer Full Integration TODO
Status: Approved by user - Proceed step-by-step

## Plan Breakdown (8 Steps)

### Phase 1: Enhance Domain Models
- [x] 1. Update Domain/syllabus.py: Full Syllabus Pydantic model + validate()
- [x] 2. Update Domain/course.py: Pydantic Course/Chapter + factories

### Phase 2: Ports Layer (Data Entry)
 - [x] 3. Refactor Application/Ports/scraper.py: Integrated cloudscraper

### Phase 3: Core Workflows
- [x] 4. Refactor Application/Workflows/syllabus_workflow.py: Use Domain.SyllabusState + run_id
- [x] 5. Update Application/Scripts/scrape_syllabus.py: Domain models

### Phase 4: Agents
- [x] 6. Refactor Application/Agents/Author_agent.py: run_id and logging support

### Phase 5: Tests & Verification
- [ ] 7. Update tests: test_syllabus_workflow.py, test_scraper.py
- [ ] 8. Test run: pytest && server start

## Current Progress
- [x] Plan created & approved

**Next: Step 1**
