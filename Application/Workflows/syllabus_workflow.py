from langgraph.graph import StateGraph
from typing import Dict, List
from typing_extensions import TypedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from Application.Agents.Planner_agent import PlannerAgent
from Application.Agents.Author_agent import AuthorAgent
from Application.Agents.Reviewer_agent import ReviewerAgent
from Application.Agents.Assembler_agent import AssemblerAgent

class SyllabusState(TypedDict):
    topics: List[str]
    syllabus: List[str]
    chapters: Dict[str, str]
    validated: bool

def planner_node(state: SyllabusState, planner: PlannerAgent) -> SyllabusState:
    return {**state, "syllabus": planner.generate_syllabus(state["topics"])}

def author_node(state: SyllabusState, author: AuthorAgent) -> SyllabusState:
    chapters = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(author.generate_content, topic): topic for topic in state["syllabus"]}
        for future in as_completed(futures):
            chapters[futures[future]] = future.result()
    return {**state, "chapters": chapters}

def reviewer_node(state: SyllabusState, reviewer: ReviewerAgent) -> SyllabusState:
    validated = all(
        reviewer.validate_factual_grounding(content, "source") and reviewer.validate_style(content)
        for content in state["chapters"].values()
    )
    return {**state, "validated": validated}

def assemble_node(state: SyllabusState, assembler: AssemblerAgent, filename: str) -> SyllabusState:
    assembler.export_to_docx(
        [{"title": topic, "content": content} for topic, content in state["chapters"].items()],
        filename
    )
    return state

def create_syllabus_workflow(planner: PlannerAgent, author: AuthorAgent, reviewer: ReviewerAgent, assembler: AssemblerAgent):
    graph = StateGraph(SyllabusState)
    graph.add_node("planner", lambda state: planner_node(state, planner))
    graph.add_node("author", lambda state: author_node(state, author))
    graph.add_node("reviewer", lambda state: reviewer_node(state, reviewer))
    graph.add_node("assemble", lambda state: assemble_node(state, assembler, "syllabus.docx"))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "author")
    graph.add_edge("author", "reviewer")
    graph.add_edge("reviewer", "assemble")

    return graph.compile()