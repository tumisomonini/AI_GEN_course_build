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
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE")

    # Relational repo for agent logging
    from Application.Ports.postgres_repo import PostgresRepo
    repo = PostgresRepo()

    # Astra vector store (required for AuthorAgent RAG)
    from Application.Infrastructure.vectorDb.Astra_vector_store import AstraVectorStore
    vector_store = AstraVectorStore(collection_name="course_chunks")

    # Initialize real agents
    from Application.Agents.Planner_agent import PlannerAgent
    from Application.Agents.Author_agent import AuthorAgent
    from Application.Agents.Reviewer_agent import ReviewerAgent
    from Application.Agents.Assembler_agent import AssemblerAgent

    agents = {
        "planner": PlannerAgent(neo4j_uri, neo4j_user, neo4j_password, neo4j_database),
        "author": AuthorAgent(vector_store, repo=repo),
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
