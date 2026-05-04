import sys
import os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, '.')
try:
    from Application.Agents.Author_agent import AuthorAgent
    agent = AuthorAgent()
    print("✅ LLM API key (OpenRouter/Mistral) valid - client initialized with model:", getattr(agent, 'model', 'N/A'))
except ValueError as e:
    if "No valid LLM API key" in str(e):
        print("❌ No valid LLM API key found in .env")
    else:
        print("⚠️ LLM init error:", e)
except Exception as e:
    print("❌ LLM init failed:", e)
