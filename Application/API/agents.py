"""
Real Agent Factory - No more mocks!
"""
from typing import Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

def initialize_real_agents():
    """Initialize agents with production settings"""
    from Application.API.dependencies import sanitize_neo4j_uri, _postgres_repo, _neo4j_repo, get_vector_store
    
    # Use pre-initialized repos from lifespan to avoid redundant connection failures
    repo = _postgres_repo
    if repo is None:
        print("⚠️ Warning: AuthorAgent initialized without Postgres logging (Repo Down)")

    vector_store = get_vector_store()
    if vector_store is None:
        print("⚠️ Warning: AuthorAgent initialized without RAG capabilities (Astra Down)")

    # Initialize real agents
    from Application.Agents.Planner_agent import PlannerAgent
    from Application.Agents.Author_agent import AuthorAgent
    from Application.Agents.Reviewer_agent import ReviewerAgent
    from Application.Agents.Assembler_agent import AssemblerAgent

    # Reuse the already-connected Neo4j singleton (local Docker fallback already resolved)
    neo4j_repo = _neo4j_repo
    if neo4j_repo is None:
        print("⚠️ Warning: PlannerAgent initialized without Neo4j KG (Neo4j Down)")

    agents = {
        "planner": PlannerAgent(neo4j_repo),
        "author": AuthorAgent(manager=None, repo=repo, kg=None),
        "reviewer": ReviewerAgent(),
        "assembler": AssemblerAgent()
    }
    
    print("✅ All 4 agents initialized for real course generation (with OpenRouter/Mistral fallback)")
    return agents

# Global agents instance
agents = None

def get_real_agents():
    global agents
    if agents is None:
        agents = initialize_real_agents()
    return agents
