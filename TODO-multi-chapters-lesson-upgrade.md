# TODO: Multi-chapter + Lessons upgrade

## Step 0 — Confirm scope
- [x] Normalize template chapter shape end-to-end (strings -> dicts)
- [ ] Add `Lesson` domain model
- [ ] Add `lessons` DB table + repository persistence
- [ ] Update workflow to generate lessons per chapter (default: 3)
- [ ] Update frontend to render lessons
- [ ] Add/adjust tests

## Step 1 — Normalize template chapters
- [ ] Add helper to coerce chapters to `[{title, ...}]`
- [ ] Apply helper in approve + full-generation flows
- [ ] Ensure frontend receives consistent `chapters` structure

## Step 2 — Add Lesson model
- [ ] Update `Domain/course.py`

## Step 3 — DB table + repo
- [ ] Update `Application/Infrastructure/relationalDB/postgres_repo.py` schema SQL
- [ ] Add methods to save/get lessons

## Step 4 — Workflow generate lessons
- [ ] Extend `SyllabusState` with lesson structure
- [ ] Add workflow node to generate lessons per chapter
- [ ] Store lessons in DB and expose in API output

## Step 5 — Frontend
- [ ] Update UI rendering for lessons inside each chapter

## Step 6 — Tests
- [ ] Add unit tests for chapter normalization
- [ ] Add unit tests for lesson persistence

