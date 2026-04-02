from langgraph.graph import StateGraph, END
from typing import Dict, List, Optional
from typing_extensions import TypedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from Application.Agents.Planner_agent import PlannerAgent
from Application.Agents.Author_agent import AuthorAgent
from Application.Agents.Reviewer_agent import ReviewerAgent
from Application.Agents.Assembler_agent import AssemblerAgent
from Application.Ports.scraper import scrape_relevant_syllabi
from Application.Ports.Astra_repo import AstraRepo

class SyllabusState(TypedDict):
    title: Optional[str]
    topics: List[str]
    syllabus: List[str]
    chapters: Dict[str, str]
    scraped_syllabi: Optional[List[Dict]]
    validated: bool

def scrape_node(state: SyllabusState) -> SyllabusState:
    """Scrape relevant syllabi if title provided"""
    if state.get("title"):
        syllabi = scrape_relevant_syllabi(state["title"])
        # Extract topics from top syllabus
        top_syllabus = next((s for s in syllabi if 'error' not in s and 'main_topics' in s), None)
        if top_syllabus:
            state["topics"] = top_syllabus.get("main_topics", state.get("topics", []))
        
        # Upsert chunks to Astra
        all_texts = []
        all_metadatas = []
        for syllabus in syllabi:
            if 'error' not in syllabus:
                for section, chunks in syllabus.items():
                    if isinstance(chunks, list):
                        for chunk in chunks:
                            all_texts.append(chunk)
                            all_metadatas.append({
                                "course_title": state["title"],
                                "section": section,
                                "type": "workflow_syllabus_chunk"
                            })
        if all_texts:
            astra_repo = AstraRepo("workflow_syllabi")
            astra_repo.upsert_syllabus_chunks(all_texts[:100], all_metadatas[:100])
        
        state["scraped_syllabi"] = syllabi
    return state

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
        reviewer.validate_factual_grounding(content, state.get("title", "source")) and reviewer.validate_style(content)
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
    graph.add_node("scrape", scrape_node)
    graph.add_node("planner", lambda state: planner_node(state, planner))
    graph.add_node("author", lambda state: author_node(state, author))
    graph.add_node("reviewer", lambda state: reviewer_node(state, reviewer))
    graph.add_node("assemble", lambda state: assemble_node(state, assembler, "syllabus.docx"))

    graph.set_entry_point("scrape")
    graph.add_conditional_edges(
        "scrape",
        lambda state: "planner" if state.get("title") or state.get("topics") else END,
        {"planner": "planner"}
    )
    graph.add_edge("planner", "author")
    graph.add_edge("author", "reviewer")
    graph.add_edge("reviewer", "assemble")

    return graph.compile()
