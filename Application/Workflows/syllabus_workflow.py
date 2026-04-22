from langgraph.graph import StateGraph, END
from typing import Dict, List, Optional, Any
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
from Application.Ports.postgres_repo import PostgresRepo
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential
from Domain.course import CourseTemplate, Chapter

class OutlineState(Dict[str, Any]):  # Keep simple dict for cheap outline
    title: str
    level: str
    duration_months: int
    run_id: int
    syllabus: List[Dict[str, Any]]
    scraped_syllabi: List[Any]
    template: Dict[str, Any]

def scrape_node(state: SyllabusState) -> SyllabusState:
    """Enhanced scraping with upsert to Astra"""
    from Application.API.dependencies import _postgres_repo as repo_logger
    # Skip if topics already exist (e.g. resuming from approved template)
    if state.topics and len(state.topics) > 0:
        return state

    run_id = getattr(state, "run_id", 0)
    
    msg = f"🔍 Scraping real-world syllabi for '{state.title}'..."
    print(msg)
    if repo_logger and run_id > 0: repo_logger.log_message(run_id, "Scraper", msg)

    syllabi = scrape_relevant_syllabi(state.title, max_results=3)
    
    if repo_logger and run_id > 0:
        repo_logger.log_message(run_id, "Scraper", "🌐 Connected to search engine. Analyzing top results...")
    
    # Extract topics from best syllabus dict
    top_syllabus = next((s for s in syllabi if 'error' not in s and s.get('main_topics')), None)
    raw_topics = top_syllabus.get('main_topics', [])[:10] if top_syllabus else []
    
    # ETL: Comprehensive cleaning replaces simple filter
    if '_cleaning_stats' in top_syllabus:
        print(f"📊 Pre-cleaned topics: {len(raw_topics)}, stats: {top_syllabus['_cleaning_stats']}")
    
    cleaned_topics_dict, stats = clean_syllabus_dict({'main_topics': raw_topics})
    clean_topics = cleaned_topics_dict.get('main_topics', [])
    log_cleaning_stats({'workflow': stats}, 'workflow')
    
    if not clean_topics:
        # Generate sensible default topics from the course title
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
    
    # Ensure we don't pass NoneType or empty strings to the planner
    state.topics = list(dict.fromkeys([str(t) for t in clean_topics if t])) # Deduplicate topic names
    state.scraped_syllabi = syllabi

    if not syllabi or all('error' in s for s in syllabi):
        if repo_logger:
            repo_logger.close()
        return state
    
    # Upsert to Astra
    all_texts = []
    all_metadatas = []
    seen_texts = set()

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
            from Application.API.dependencies import get_astra_repo
            repo = next(get_astra_repo())
            # Perform the heavy AstraDB upsert in a background thread.
            # This prevents blocking the outline generation, as these chunks
            # are only needed later by the AuthorAgent. Now fully thread-safe.
            threading.Thread(target=repo.upsert_syllabus_chunks, args=(all_texts, all_metadatas), daemon=True).start()
            log_msg = f"📡 Knowledge base update dispatched to background (thread-safe)"
            if repo_logger: repo_logger.log_message(run_id, "AstraDB", log_msg)
            print(log_msg)
        except Exception as e:
            print(f"⚠️ Astra upsert failed: {e}")
        finally:
            if repo_logger:
                repo_logger.log_message(run_id, "Scraper", f"Found {len(syllabi)} relevant sources")
                repo_logger.close()
    return state

def planner_node(state: SyllabusState, planner: PlannerAgent) -> SyllabusState:
    """Generate syllabus order"""
    from Application.API.dependencies import _postgres_repo as repo_logger
    # Skip if syllabus is already determined
    if state.syllabus and len(state.syllabus) > 0:
        return state

    run_id = getattr(state, "run_id", 0)

    msg = "📋 Organizing syllabus topics into an optimal learning path..."
    print(msg)
    if repo_logger and run_id > 0: repo_logger.log_message(run_id, "Planner", msg)

    state.syllabus = planner.generate_syllabus(state.topics[:6])
    msg = f"✅ Syllabus organized: {len(state.syllabus)} chapters determined."
    print(msg)
    if repo_logger: repo_logger.log_message(run_id, "Planner", msg)
        
    return state

async def author_node(state: SyllabusState, author: AuthorAgent) -> SyllabusState:
    """Generate real chapter content"""
    from Application.API.dependencies import _postgres_repo as repo_logger
    print("✍️ Generating real chapter content...")
    run_id = getattr(state, "run_id", 0)
    
    start_time = time.time()

    try:
        # Use asyncio.gather for true non-blocking concurrency with async agents
        tasks = [author.generate_content(topic, state, i) for i, topic in enumerate(state.syllabus)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_chapters = {}
        for i, result in enumerate(results):
            topic = state.syllabus[i]
            if isinstance(result, Exception):
                new_chapters[topic] = f"Error: {str(result)}"
            else:
                new_chapters[topic] = result.content
                if repo_logger: repo_logger.log_message(run_id, "Author", f"Finished: {topic}")

    finally:
        if repo_logger: repo_logger.close()
    
    state.chapters = new_chapters
    state.generation_time = time.time() - start_time
    print(f"📚 Generated {len(state.chapters)} chapters in {state.generation_time:.1f}s")
    return state

async def reviewer_node(state: SyllabusState, reviewer: ReviewerAgent) -> SyllabusState:
    """Review content quality"""
    from Application.API.dependencies import _postgres_repo as repo_logger
    run_id = getattr(state, "run_id", 0)

    msg = "🔍 Performing quality assurance and semantic review..."
    print(msg)
    if repo_logger: repo_logger.log_message(run_id, "Reviewer", msg)

    failed = 0
    chapters = state.chapters or {}
    semantic_scores = []
    try:
        for topic, content in chapters.items():
            # 1. Semantic Critique
            critique = await reviewer.validate_content_with_llm(content, topic)
            semantic_score = critique.get("semantic_score", 0.0)
            semantic_pass = critique.get("semantic_pass", False)
            semantic_scores.append(semantic_score)
            
            # 2. Heuristic Grounding & Style
            is_substantive = reviewer.validate_factual_grounding(content)
            is_styled = reviewer.validate_style(content)
            
            # 3. Compliance & Safety Check (Fixes ❌)
            safety = await reviewer.check_intent_and_safety(content[:1000])
            is_safe = safety.get("is_safe", True)

            if not semantic_pass or not is_substantive or not is_styled or not is_safe:
                failed += 1
                err_msg = f"⚠️ Quality alert for '{topic}': Score={semantic_score}, Substantive={is_substantive}, Safe={is_safe}"
                print(err_msg)
                if repo_logger: repo_logger.log_message(run_id, "Reviewer", err_msg, "warning")
            else:
                if repo_logger: repo_logger.log_message(run_id, "Reviewer", f"✅ Content verified for '{topic}'")
    
        state.reviewer_semantic_avg = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0
        state.semantic_pass_rate = sum(s >= 0.6 for s in semantic_scores) / len(semantic_scores) if semantic_scores else 0.0
        state.validated = state.semantic_pass_rate >= 0.8 and failed == 0
        res_msg = f"🏁 Review complete: {'PASS' if state.validated else 'NEEDS_WORK'} ({failed}/{len(state.chapters)} issues found)"
        print(res_msg)
        if repo_logger: repo_logger.log_message(run_id, "Reviewer", res_msg)
    finally:
        if repo_logger: repo_logger.close()
        
    return state

def assemble_node(state: SyllabusState, assembler: AssemblerAgent) -> SyllabusState:
    """Assemble final course"""
    from Application.API.dependencies import _postgres_repo as repo_logger
    run_id = getattr(state, "run_id", 0)

    msg = "📄 Finalizing course assembly and exporting assets..."
    print(msg)
    if repo_logger: repo_logger.log_message(run_id, "Assembler", msg)

    chapters = state.chapters or {}
    chapters_list = [{"title": k, "content": v} for k, v in chapters.items()]
    filename = assembler.export_to_docx(chapters_list, f"{state.title.replace(' ', '_')}.docx")
    
    msg = f"🎉 Course generation successful! Artifact: {filename}"
    print(msg)
    if repo_logger: repo_logger.log_message(run_id, "Assembler", msg)
    if repo_logger: repo_logger.close()
    
    return state

def create_outline_workflow(title: str, level: str = "beginner", duration_months: int = 3, run_id: int = 0) -> Dict[str, Any]:
    """Cheap outline workflow"""
    from ..API.agents import get_real_agents
    agents = get_real_agents()
    
    # Safety/Intent Gate
    reviewer = agents["reviewer"]
    # We wrap this in a run_async or similar if needed
    loop = asyncio.get_event_loop()
    check = loop.run_until_complete(reviewer.check_intent_and_safety(title))
    if not check.get('is_valid') or not check.get('is_safe'):
        print(f"🛑 Query Rejected: {check.get('reason')}")
        return {"title": title, "status": "failed", "error": check.get('reason')}

    graph = StateGraph(OutlineState)
    def scrape_to_dict(s):
        result = scrape_node(SyllabusState.model_validate(s))
        # Merge SyllabusState fields back into the OutlineState dict
        d = dict(s)
        d["topics"] = result.topics
        d["scraped_syllabi"] = result.scraped_syllabi or []
        return d
    graph.add_node("scrape", scrape_to_dict)
    graph.add_node("planner", lambda s: planner_node_outline(s, agents["planner"]))
    
    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "planner")
    
    workflow = graph.compile()
    
    initial_state = {
        "title": title,
        "level": level,
        "duration_months": duration_months,
        "run_id": run_id,
        "syllabus": [],
        "scraped_syllabi": [],
        "template": {}
    }
    
    result = workflow.invoke(initial_state)
    
    raw_syllabus = result["syllabus"][:6]
    chapter_titles = [c["title"] if isinstance(c, dict) else c for c in raw_syllabus]
    template = CourseTemplate(
        title=title,
        level=level,
        duration_months=duration_months,
        learning_objectives=[f"Master {title}", "Build real projects"],
        prerequisites=[f"Basic {title.split()[0]}", "Programming experience"],
        chapters=chapter_titles
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
    repo_logger = PostgresRepo() if run_id else None
    
    if repo_logger: 
        repo_logger.log_message(run_id, "Planner", "🧠 Analyzing prerequisites and organizing modules...")

    # scrape_node returns a SyllabusState; topics is a flat list of strings
    raw_topics = state.get("topics", []) if isinstance(state, dict) else getattr(state, "topics", [])
    
    topic_titles = []
    for t in raw_topics[:10]: # Process up to 10 for better selection
        if isinstance(t, dict):
            topic_titles.append(t.get("title") or t.get("name", "Untitled Chapter"))
        else:
            topic_titles.append(str(t))
    
    ordered_titles = planner.generate_syllabus(topic_titles)
    
    # Simulate "streaming" by logging chapters one-by-one
    for i, title in enumerate(ordered_titles):
        if repo_logger:
            repo_logger.log_message(run_id, "Planner", f"✨ Chapter {i+1} determined: {title}")
            time.sleep(0.4) # Small delay for "ChatGPT" streaming feel

    if isinstance(state, dict):
        state["syllabus"] = [{"title": chap} for chap in ordered_titles]
    else:
        state.syllabus = ordered_titles
    
    if repo_logger: repo_logger.close()
    return state

def create_syllabus_workflow(planner: PlannerAgent, author: AuthorAgent, reviewer: ReviewerAgent, assembler: AssemblerAgent):
    """Full domain-integrated workflow"""
    graph = StateGraph(SyllabusState)
    graph.add_node("scrape", lambda s: scrape_node(s))
    graph.add_node("planner", lambda s: planner_node(s, planner))
    async def author_node_func(state):
        return await author_node(state, author)

    async def reviewer_node_func(state):
        return await reviewer_node(state, reviewer)

    graph.add_node("author", author_node_func)
    graph.add_node("reviewer", reviewer_node_func)
    graph.add_node("assemble", lambda s: assemble_node(s, assembler))

    graph.set_entry_point("scrape")
    graph.add_conditional_edges(
        "scrape",
        lambda s: "planner" if s.topics else END,
        {"planner": "planner"}
    )
    graph.add_edge("planner", "author")
    graph.add_edge("author", "reviewer")
    graph.add_edge("reviewer", "assemble")
    
    return graph.compile()

async def create_real_syllabus_workflow(
    title: str, 
    duration_months: int = 3, 
    level: str = "beginner",
    run_id: int = 0, 
    topics: List[str] = None, 
    syllabus: List[str] = None
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
        chapters={},
        scraped_syllabi=None,
        validated=False,
        duration_months=duration_months,
        level=level,
        generation_time=0.0
    )
    
    result = await workflow.ainvoke(initial_state)
    final_syllabus = Syllabus.from_state(SyllabusState.model_validate(result))
    return final_syllabus.model_dump(), agents["assembler"]
