import sys
import os
sys.path.insert(0, '.')
try:
    from Application.Agents.Reviewer_agent import ReviewerAgent
    agent = ReviewerAgent()
    print("✅ ReviewerAgent LLM client initialized:", agent.client is not None)
    print("Model:", getattr(agent, 'model', 'N/A'))
    print("OpenRouter key detected:", os.getenv('OPENROUTER_API_KEY') is not None)
except Exception as e:
    print("❌ LLM init failed:", e)

