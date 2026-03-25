from langgraph.graph import StateGraph
from typing import Dict, List
from ..agents.planner_agent import PlannerAgent
from ..agents.author_agent import AuthorAgent
from ..agents.reviewer_agent import ReviewerAgent
from ..agents.assembler_agent import AssemblerAgent

class SyllabusState:
    syllabus: List[str]
    chapters: Dict[str, str]
    validated: bool

def planner_node(state: SyllabusState, planner: PlannerAgent, topics: List[str]):
    state.syllabus = planner.generate_syllabus(topics)
    return state

def author_node(state: SyllabusState, author: AuthorAgent):
    for topic in state.syllabus:
        state.chapters[topic] = author.generate_content(topic)
    return state

def reviewer_node(state: SyllabusState, reviewer: ReviewerAgent):
    for topic, content in state.chapters.items():
        state.validated = reviewer.validate_factual_grounding(content, "source") and reviewer.validate_style(content)
    return state

def assemble_node(state: SyllabusState, assembler: AssemblerAgent, filename: str):
    assembler.export_to_docx([{"title": topic, "content": content} for topic, content in state.chapters.items()], filename)
    return state

def create_syllabus_workflow(planner: PlannerAgent, author: AuthorAgent, reviewer: ReviewerAgent, assembler: AssemblerAgent):
    graph = StateGraph(SyllabusState)
    graph.add_node("planner", lambda state: planner_node(state, planner, ["Intro to Python", "Advanced Python"]))
    graph.add_node("author", lambda state: author_node(state, author))
    graph.add_node("reviewer", lambda state: reviewer_node(state, reviewer))
    graph.add_node("assemble", lambda state: assemble_node(state, assembler, "syllabus.docx"))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "author")
    graph.add_edge("author", "reviewer")
    graph.add_edge("reviewer", "assemble")

    return graph.compile()