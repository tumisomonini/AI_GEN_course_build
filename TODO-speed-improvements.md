# Speed Optimization Plan - author_node (Approved: proceed)

## Current Performance
- max_workers=3 
- timeout=60s per chapter
- Total: 2-5min for 8 chapters

## 1. Increase Concurrency
- Change max_workers=3 → max_workers=6 (OpenAI rate limits safe)

## 2. Reduce Timeout
- Change timeout=60 → timeout=45s

## 3. Limit Chapters
- planner_node: [:8] → [:6]

## 4. Followup
- Test generation timing in logs
- Monitor OpenAI rate limits
- Restart server to apply (--reload automatic)

Status: Ready to edit Application/Workflows/syllabus_workflow.py
