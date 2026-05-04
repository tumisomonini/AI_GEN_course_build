import os
from utils.env_loader import load_root_env

load_root_env()
print('OPENROUTER_API_KEY len:', len(os.getenv('OPENROUTER_API_KEY', '')))
print('Key starts with:', repr(os.getenv('OPENROUTER_API_KEY', '')[:20]))
from Application.Agents.Reviewer_agent import ReviewerAgent
agent = ReviewerAgent()
print("Client:", agent.client is not None)

