# Template Approval Flow Implementation

## Steps (BLACKBOXAI)
- [ ] 1. Create split workflows: outline-only (scrape+planner), full (author+review+assemble)
- [ ] 2. courses.py: POST /generate/course-template → outline → Postgres draft
- [ ] 3. courses.py: POST /{id}/approve-full → full_workflow background
- [ ] 4. GET /{id}/course-review → outline or full based on status
- [ ] 5. Update test_interface.html POST endpoint
- [ ] 6. course_review_interface.html: Add "Approve → Gen Full" btn + poll
- [ ] 7. Ensure postgres_repo supports outline/full
- [ ] 8. pytest tests pass
- [ ] 9. Manual test: generate → approve → full content

Progress: Core backend/UI done. Steps 1-6 complete. Tests pending. Ready for testing: generate → approve → full.
