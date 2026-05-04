# OpenRouter Setup - KEY REQUIRED ✅

## .env Template Ready!
Edit `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here  # Get from https://openrouter.ai/keys (REQUIRED for agents)
MISTRAL_API_KEY=...  # Optional fallback
```

## Steps:
1. Sign up: https://openrouter.ai → Dashboard → Keys
2. Copy `sk-or-v1-...`
3. Paste into `.env`
4. Test: `python test_llm_keys.py` → ✅ "LLM API key valid"
5. Restart server: `./run_dev.sh`
6. Health: `curl http://localhost:8000/health`
7. Demo: Open Pages/dashboard.html

**Neo4j cloud skipped per task.**

**Program ready once key set! 🚀**
