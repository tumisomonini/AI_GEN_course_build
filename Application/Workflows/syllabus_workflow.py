from langgraph.graph import StateGraph, END
from typing import Dict, List, Optional, Any, TypedDict
import time
import asyncio
import threading

from Domain.syllabus import SyllabusState, Syllabus
from Application.Agents.Planner_agent import PlannerAgent
from Application.Agents.Author_agent import AuthorAgent
from Application.Agents.Reviewer_agent import ReviewerAgent
from Application.Agents.Assembler_agent import AssemblerAgent
from Application.Infrastructure.ETL.cleaner import clean_syllabus_dict, log_cleaning_stats
from Application.Ports.scraper import scrape_relevant_syllabi
from Domain.course import CourseTemplate, Chapter


class OutlineState(TypedDict):  # TypedDict for cheap dict-based outline state
    title: str
    level: str
    duration_months: int
    run_id: int
    syllabus: List[Dict[str, Any]]
    scraped_syllabi: List[Any]
    template: Dict[str, Any]
    topics: List[Any]


def _get_pg_logger():
    """Get the shared Postgres logger without creating a new instance."""
    from Application.API.dependencies import _postgres_repo
    return _postgres_repo


async def scrape_node(state: SyllabusState) -> SyllabusState:
    """Enhanced scraping with upsert to Astra + TripleDB logging"""
    repo_logger = _get_pg_logger()

    scrape_start = time.time()

    # Skip if topics already exist (e.g. resuming from approved template)
    if state.topics and len(state.topics) > 0:
        return state

    run_id = getattr(state, "run_id", 0)

    msg = f"🔍 Scraping real-world syllabi for '{state.title}'..."
    print(msg)
    if repo_logger and run_id > 0:
        repo_logger.log_message(run_id, "Scraper", msg)

    syllabi = await asyncio.to_thread(scrape_relevant_syllabi, state.title, max_results=2)

    if repo_logger and run_id > 0:
        repo_logger.log_message(run_id, "Scraper", "🌐 Connected to search engine. Analyzing top results...")

    # Extract topics from best syllabus dict
    top_syllabus = next((s for s in syllabi if 'error' not in s and s.get('main_topics')), None)
    raw_topics = top_syllabus.get('main_topics', [])[:10] if top_syllabus else []

    # ETL: Comprehensive cleaning replaces simple filter
    if top_syllabus and '_cleaning_stats' in top_syllabus:
        print(f"📊 Pre-cleaned topics: {len(raw_topics)}, stats: {top_syllabus['_cleaning_stats']}")

    cleaned_topics_dict, stats = clean_syllabus_dict({'main_topics': raw_topics})
    clean_topics = cleaned_topics_dict.get('main_topics', [])
    log_cleaning_stats({'workflow': stats}, 'workflow')

    if not clean_topics:
        words = state.title.split()
        base = " ".join(words[:3])
        clean_topics = [
            f"Introduction to {base}",
            f"{base} Core Concepts",
            f"{base} Tools and Setup",
            f"Practical {base}",
            f"Advanced {base}",
            f"{base} Projects and Applications",
        ]
        print(f"⚠️ Scraping yielded no clean topics — using generated defaults for '{state.title}'")

    state.topics = list(dict.fromkeys([str(t) for t in clean_topics if t]))
    state.scraped_syllabi = syllabi

    if not syllabi or all('error' in s for s in syllabi):
        return state

    # Upsert to Astra
    all_texts: List[str] = []
    all_metadatas: List[Dict[str, Any]] = []
    seen_texts: set = set()

    for syllabus in syllabi[:3]:
        if 'error' not in syllabus:
            for topic in syllabus.get('main_topics', []):
                text_content = str(topic)[:1500]
                if text_content in seen_texts:
                    continue
                seen_texts.add(text_content)
                all_texts.append(text_content)
                all_metadatas.append({
                    "course_title": state.title,
                    "section": str(topic)[:100],
                    "type": "scraped_syllabus"
                })

    if all_texts:
        try:
            from Application.API.dependencies import get_triple_db_manager
            manager = get_triple_db_manager()
            repo = manager.astra
            if repo:
                def background_upsert(texts: List[str], metas: List[Dict[str, Any]]) -> None:
                    try:
                        repo.upsert_syllabus_chunks(texts, metas)  # type: ignore[union-attr]
                    except Exception as thread_e:
                        print(f"❌ Background Astra upsert failed: {thread_e}")

                thread = threading.Thread(
                    target=background_upsert,
                    args=(all_texts, all_metadatas),
                    daemon=True
                )
                thread.start()
                log_msg = "📡 Knowledge base update dispatched to background (thread-safe)"
                if repo_logger:
                    repo_logger.log_message(run_id, "AstraDB", log_msg)
                print(log_msg)
            else:
                print("⚠️ Astra unavailable — skipping knowledge base upsert")
        except Exception as e:
            print(f"⚠️ Astra upsert failed: {e}")
        if repo_logger and run_id > 0:
            repo_logger.log_message(run_id, "Scraper", f"Found {len(syllabi)} relevant sources")

    state.scraper_time = time.time() - scrape_start
    return state


async def planner_node(state: SyllabusState, planner: PlannerAgent) -> SyllabusState:
    """Generate syllabus order (async)"""
    repo_logger = _get_pg_logger()

    planner_start = time.time()

    if state.syllabus and len(state.syllabus) > 0:
        return state

    run_id = getattr(state, "run_id", 0)

    msg = "📋 Organizing syllabus topics into an optimal learning path..."
    print(msg)
    if repo_logger and run_id > 0:
        repo_logger.log_message(run_id, "Planner", msg)

    loop = asyncio.get_running_loop()
    state.syllabus = await loop.run_in_executor(None, lambda: planner.generate_syllabus(state.topics[:4]))
    msg = f"✅ Syllabus organized: {len(state.syllabus)} chapters determined."
    print(msg)
    if repo_logger:
        repo_logger.log_message(run_id, "Planner", msg)

    state.planner_time = time.time() - planner_start
    return state


async def author_node(state: SyllabusState, author: AuthorAgent, reviewer: Optional[ReviewerAgent] = None) -> SyllabusState:
    """Generate real chapter content"""
    repo_logger = _get_pg_logger()
    print("✍️ Generating real chapter content...")
    run_id = getattr(state, "run_id", 0)

    author_start = time.time()

    results = await author.generate_multiple_chapters([topic for topic in state.syllabus], state, reviewer=reviewer)

    chapters_list = []
    for i, result in enumerate(results):
        topic = state.syllabus[i]
        if isinstance(result, Exception):
            error_chapter = Chapter(title=topic, content=f"Error: {str(result)}", chapter_order=i, status="error")
            chapters_list.append(error_chapter)
        else:
            chapters_list.append(result)
            if repo_logger:
                repo_logger.log_message(run_id, "Author", f"Finished: {topic}")

    state.chapters = chapters_list
    state.author_time = time.time() - author_start
    print(f"📚 Generated {len(chapters_list)} chapters in {state.author_time:.1f}s")
    return state


async def reviewer_node(state: SyllabusState, reviewer: ReviewerAgent) -> SyllabusState:
    """Review content quality"""
    repo_logger = _get_pg_logger()
    run_id = getattr(state, "run_id", 0)

    reviewer_start = time.time()

    msg = "🔍 Performing quality assurance and semantic review..."
    print(msg)
    if repo_logger:
        repo_logger.log_message(run_id, "Reviewer", msg)

    chapters = state.chapters or []

    async def review_single_chapter(chapter: Chapter):
        critique = await reviewer.validate_content_with_llm(chapter.content, chapter.title)
        semantic_score = critique.get("semantic_score", 0.0)
        semantic_pass = critique.get("semantic_pass", False)

        is_substantive = reviewer.validate_factual_grounding(chapter.content)
        is_styled = reviewer.validate_style(chapter.content)

        safety = await reviewer.check_intent_and_safety(chapter.content[:1000])
        is_safe = safety.get("is_safe", True)

        is_valid = semantic_pass and is_substantive and is_styled and is_safe
        if not is_valid:
            err_msg = f"⚠️ Quality alert for '{chapter.title}': Score={semantic_score}, Substantive={is_substantive}, Safe={is_safe}"
            if repo_logger:
                repo_logger.log_message(run_id, "Reviewer", err_msg, "warning")

        return semantic_score, is_valid

    review_tasks = [review_single_chapter(ch) for ch in chapters]
    results = await asyncio.gather(*review_tasks)

    semantic_scores = [r[0] for r in results]
    valid_flags = [r[1] for r in results]
    failed = valid_flags.count(False)

    reviewer_semantic_avg = round(sum(semantic_scores) / len(semantic_scores), 2) if semantic_scores else 0.0
    semantic_pass_rate = round(sum(s >= 0.6 for s in semantic_scores) / len(semantic_scores), 2) if semantic_scores else 0.0
    state = state.model_copy(update={
        "reviewer_semantic_avg": reviewer_semantic_avg,
        "semantic_pass_rate": semantic_pass_rate,
        "validated": semantic_pass_rate >= 0.8 and failed == 0,
    })

    res_msg = f"🏁 Review complete: {'PASS' if state.validated else 'NEEDS_WORK'} ({failed}/{len(chapters)} issues found)"
    print(res_msg)
    if repo_logger:
        repo_logger.log_message(run_id, "Reviewer", res_msg)

    state.reviewer_time = time.time() - reviewer_start
    return state


async def assemble_node(state: SyllabusState, assembler: AssemblerAgent) -> SyllabusState:
    """Assemble final course (async)"""
    repo_logger = _get_pg_logger()
    run_id = getattr(state, "run_id", 0)

    assembler_start = time.time()

    msg = "📄 Finalizing course assembly and exporting assets..."
    print(msg)
    if repo_logger:
        repo_logger.log_message(run_id, "Assembler", msg)

    loop = asyncio.get_running_loop()
    chapters = state.chapters or []
    chapters_list = [{"title": ch.title, "content": ch.content} for ch in chapters]
    filename = await loop.run_in_executor(None, lambda: assembler.export_to_docx(chapters_list, f"{state.title.replace(' ', '_')}.docx"))

    msg = f"🎉 Course generation successful! Artifact: {filename}"
    print(msg)
    if repo_logger and run_id > 0:
        repo_logger.log_message(run_id, "Assembler", msg)

    state.assembler_time = time.time() - assembler_start
    return state


def create_outline_workflow(title: str, level: str = "beginner", duration_months: int = 3, run_id: int = 0) -> Dict[str, Any]:
    """Cheap outline workflow"""
    from ..API.agents import get_real_agents
    agents = get_real_agents()

    reviewer = agents["reviewer"]
    check = asyncio.run(reviewer.check_intent_and_safety(title))
    if not check.get('is_valid') or not check.get('is_safe'):
        print(f"🛑 Query Rejected: {check.get('reason')}")
        return {"title": title, "status": "failed", "error": check.get('reason')}

    graph: StateGraph = StateGraph(OutlineState)

    async def scrape_to_dict(state: OutlineState) -> OutlineState:
        syllabus_state = SyllabusState.model_validate(dict(state))
        result = await scrape_node(syllabus_state)
        state["topics"] = result.topics
        state["scraped_syllabi"] = result.scraped_syllabi or []
        return state

    graph.add_node("scrape", scrape_to_dict)
    async def planner_outline_node(state: OutlineState, config: Any = None) -> OutlineState:
        return planner_node_outline(state, agents["planner"])
    graph.add_node("planner", planner_outline_node)

    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "planner")

    workflow = graph.compile()

    initial_state: OutlineState = {
        "title": title,
        "level": level,
        "duration_months": duration_months,
        "run_id": run_id,
        "syllabus": [],
        "scraped_syllabi": [],
        "template": {},
        "topics": [],
    }

    result = workflow.invoke(initial_state)

    raw_syllabus = result["syllabus"][:6]
    template = CourseTemplate(
        title=title,
        level=level,
        duration_months=duration_months,
        learning_objectives=[f"Master {title}", "Build real projects"],
        prerequisites=[f"Basic {title.split()[0]}", "Programming experience"],
        chapters=[{"title": c["title"] if isinstance(c, dict) else str(c)} for c in raw_syllabus]
    ).model_dump()

    template["scraping_result"] = {
        "is_real_data": True,
        "total_sources": len(result["scraped_syllabi"]),
        "quality_score": 85,
        "sources": [s.get("title", "Source") for s in result["scraped_syllabi"] if "error" not in s]
    }

    print(f"✅ Outline template: {len(template['chapters'])} chapters")
    return template


def planner_node_outline(state: OutlineState, planner: PlannerAgent) -> OutlineState:
    """Outline planner"""
    run_id = state.get("run_id", 0)
    repo_logger = _get_pg_logger() if run_id else None

    if repo_logger and run_id > 0:
        repo_logger.log_message(run_id, "Planner", "🧠 Analyzing prerequisites and organizing modules...")

    raw_topics = state.get("topics", [])

    topic_titles: List[str] = []
    for t in raw_topics[:10]:
        if isinstance(t, dict):
            topic_titles.append(t.get("title") or t.get("name", "Untitled Chapter"))
        else:
            topic_titles.append(str(t))

    ordered_titles = planner.generate_syllabus(topic_titles)

    for i, title in enumerate(ordered_titles):
        if repo_logger:
            repo_logger.log_message(run_id, "Planner", f"✨ Chapter {i+1} determined: {title}")

    state["syllabus"] = [{"title": chap} for chap in ordered_titles]
    return state


def create_syllabus_workflow(planner: PlannerAgent, author: AuthorAgent, reviewer: ReviewerAgent, assembler: AssemblerAgent):
    """Full domain-integrated workflow"""
    graph: StateGraph = StateGraph(SyllabusState)
    graph.add_node("scrape", scrape_node)

    async def planner_node_func(state: SyllabusState) -> SyllabusState:
        return await planner_node(state, planner)

    async def assemble_node_func(state: SyllabusState) -> SyllabusState:
        return await assemble_node(state, assembler)

    async def author_node_func(state: SyllabusState) -> SyllabusState:
        return await author_node(state, author, reviewer=reviewer)

    async def reviewer_node_func(state: SyllabusState) -> SyllabusState:
        return await reviewer_node(state, reviewer)

    graph.add_node("planner", planner_node_func)
    graph.add_node("author", author_node_func)
    graph.add_node("reviewer", reviewer_node_func)
    graph.add_node("assemble", assemble_node_func)

    graph.set_entry_point("scrape")
    graph.add_conditional_edges(
        "scrape",
        lambda s: "planner" if s.topics else END,
        {"planner": "planner"}
    )
    graph.add_edge("planner", "author")

    def should_review(state: SyllabusState) -> str:
        return "reviewer" if not getattr(state, "validated", True) else "assemble"

    graph.add_conditional_edges(
        "author",
        should_review,
        {"reviewer": "reviewer", "assemble": "assemble"}
    )
    graph.add_edge("reviewer", "assemble")

    return graph.compile()


async def create_real_syllabus_workflow(
    title: str,
    duration_months: int = 3,
    level: str = "beginner",
    run_id: int = 0,
    topics: Optional[List[str]] = None,
    syllabus: Optional[List[str]] = None
):
    """Legacy full workflow entry"""
    from ..API.agents import get_real_agents
    agents = get_real_agents()

    workflow = create_syllabus_workflow(
        planner=agents["planner"],
        author=agents["author"],
        reviewer=agents["reviewer"],
        assembler=agents["assembler"]
    )

    initial_state = SyllabusState(
        title=title,
        run_id=run_id,
        topics=topics or [],
        syllabus=syllabus or [],
        chapters=[],
        scraped_syllabi=None,
        validated=False,
        duration_months=duration_months,
        level=level,
        generation_time=0.0
    )

    result = await workflow.ainvoke(initial_state)
    final_syllabus = Syllabus.from_state(SyllabusState.model_validate(result))
    return final_syllabus.model_dump(), agents["assembler"]
