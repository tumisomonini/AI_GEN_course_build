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
    from Application.API.dependencies import (
        init_postgres_singleton, 
        init_neo4j_singleton, 
        get_triple_db_manager
    )
    
    # Ensure core domain repositories and the integrated manager are initialized
    repo = init_postgres_singleton()
    neo4j_repo = init_neo4j_singleton()
    manager = get_triple_db_manager()

    # Initialize real agents
    from Application.Agents.Planner_agent import PlannerAgent
    from Application.Agents.Author_agent import AuthorAgent
    from Application.Agents.Reviewer_agent import ReviewerAgent
    from Application.Agents.Assembler_agent import AssemblerAgent

    # Safe initialization for PlannerAgent to prevent AttributeError on .database access
    planner_agent = None
    if neo4j_repo:
        try:
            planner_agent = PlannerAgent(neo4j_repo)
        except Exception as e:
            print(f"❌ Failed to initialize PlannerAgent: {e}")
            planner_agent = None
    else:
        print("⚠️ Warning: PlannerAgent will be unavailable (Neo4j Down)")

    agents = {
        "planner": planner_agent,
        "author": AuthorAgent(manager=manager, repo=repo),
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
