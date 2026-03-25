from fastapi import APIRouter, Depends
from application.workflows.syllabus_workflow import create_syllabus_workflow
from application.agents.planner_agent import PlannerAgent
from application.agents.author_agent import AuthorAgent
from application.agents.reviewer_agent import ReviewerAgent
from application.agents.assembler_agent import AssemblerAgent
from infrastructure.vector.astra_vector_store import AstraVectorStore
from infrastructure.graph.neo4j_repo import Neo4jRepository

router = APIRouter()

@router.post("/generate")
async def generate_syllabus():
    planner = PlannerAgent(neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="password")
    author = AuthorAgent(AstraVectorStore("course_chunks"), openai_api_key="your-openai-key")
    reviewer = ReviewerAgent()
    assembler = AssemblerAgent()

    workflow = create_syllabus_workflow(planner, author, reviewer, assembler)
    result = workflow(SyllabusState(syllabus=[], chapters={}, validated=False))

    return {"status": "success", "syllabus": result.syllabus}