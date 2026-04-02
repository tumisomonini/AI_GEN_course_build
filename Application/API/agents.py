"""
Agent management module to avoid circular imports
"""
from typing import Dict, Any
from ..Agents.Planner_agent import PlannerAgent
from ..Agents.Author_agent import AuthorAgent
from ..Agents.Reviewer_agent import ReviewerAgent
from ..Agents.Assembler_agent import AssemblerAgent
from ..Infrastructure.vectorDb.Astra_vector_store import AstraVectorStore
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

agents: Dict[str, Any] = {}

def initialize_agents():
    """Initialize all agents with their dependencies"""
    global agents

    llm_api_key = os.getenv("OPENROUTER_API_KEY")
    if not llm_api_key:
        print("Warning: OPENROUTER_API_KEY not set - agents will not be initialized")
        return

    try:
        # Get Neo4j configuration
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        neo4j_database = os.getenv("NEO4J_DATABASE")

        # Initialize vector store for AuthorAgent (optional - continue if fails)
        vector_store = None
        try:
            astra_collection = os.getenv("ASTRA_COLLECTION_NAME", "syllabus_chunks")
            vector_store = AstraVectorStore(astra_collection)
        except Exception as astra_error:
            print(f"Warning: Astra DB connection failed: {astra_error}")
            print("AuthorAgent will run in limited mode without vector search")

        # Initialize agents with correct parameters
        agents["planner"] = PlannerAgent(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
        agents["author"] = AuthorAgent(vector_store, llm_api_key) if vector_store else AuthorAgent(None, llm_api_key, mock_mode=True)
        agents["reviewer"] = ReviewerAgent()
        agents["assembler"] = AssemblerAgent()

        print(f"Successfully initialized {len(agents)} agents")

    except Exception as e:
        print(f"Failed to initialize agents: {e}")
        agents = {}

def get_agents():
    """Get the initialized agents"""
    return agents