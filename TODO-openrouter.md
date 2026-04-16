# OpenRouter Fallback ✅ (OpenAPI Unavailable)

## Progress
- [x] TODO created & plan approved

## Steps
- [ ] 1. Sign up https://openrouter.ai → Add `OPENROUTER_API_KEY=sk-or-...` to .env (use free llama-3.1-8b-instruct)
- [ ] 2. Start server: `./run_dev.sh` (Docker up, uvicorn --reload)
- [ ] 3. Test health: `curl http://localhost:8000/health` (agents:'real')
- [ ] 4. Test generation: `curl -X POST http://localhost:8000/syllabus/generate -H \"Content-Type: application/json\" -d '{\"topics\":[\"Python Basics\"]}'`
- [ ] 5. UI: http://localhost:8000/pages/test_interface.html → Generate course (uses OpenRouter)
- [ ] 6. Swagger: http://localhost:8000/docs (now available)

**Agents auto-prefer OpenRouter (Reviewer/Author init). Model: $LLM_MODEL or gpt-4o-mini.**
