import asyncio
from typing import List, Dict, Any, Optional
import os
from pydantic import Field
from Domain.course import Chapter
from Domain.syllabus import SyllabusState
import openai
from openai import AsyncOpenAI
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging
logger = logging.getLogger(__name__)

class AuthorAgent:
    def __init__(self, manager=None, repo=None, kg=None):
        self.manager = manager
        self.vector_store = manager.astra.vector_store if manager else None
        self.repo = manager.pg if manager else repo
        self.kg = manager.kg if manager else kg

        # 1. Try Local Inference (Unsloth/vLLM/Ollama)
        local_url = os.getenv("LOCAL_LLM_URL")
        if local_url:
            if self._setup_client(local_url, "local-token", "LOCAL_LLM_MODEL", "unsloth-llama-3-8b", timeout=120.0):
                return
        
        # Try OpenRouter first
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            if self._setup_client("https://openrouter.ai/api/v1", openrouter_key, "OPENROUTER_MODEL", "openai/gpt-4o-mini"):
                return
        
        # Fallback to Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            if self._setup_client("https://api.mistral.ai/v1", mistral_key, "MISTRAL_MODEL", "mistral-small-latest"):
                return
        
        raise ValueError("No valid LLM API key found. Set OPENROUTER_API_KEY or MISTRAL_API_KEY in .env")

    def _setup_client(self, base_url, api_key, model_env, default_model, timeout=60.0):
        try:
            self.openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
            self.model = os.getenv(model_env, default_model)
            logger.info(f"AuthorAgent using {base_url} with model: {self.model}")
            return True
        except Exception as e:
            logger.warning(f"LLM Init failed for {base_url}: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((openai.APIError, openai.RateLimitError, openai.APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _call_llm(self, **kwargs):
        """Retryable LLM call."""
        if not self.openai_client:
            raise ValueError("No LLM client initialized")
        return await self.openai_client.chat.completions.create(**kwargs)

    async def generate_content(self, topic: str, state: Optional[SyllabusState] = None, order: int = 0, reviewer=None, max_retries: int = 1) -> Optional[Chapter]:
        """Generate chapter content. Returns a Domain Chapter object."""
        run_id = state.run_id if (state and state.run_id and state.run_id > 0) else None
        if self.repo and run_id:
            self.repo.log_message(run_id, "AuthorAgent", f"Starting generation for topic: {topic}")
            
        # Query Routing Implementation (sync — no LLM call)
        strategy = "hybrid"
        if reviewer:
            route_data = reviewer.route_query(topic)
            strategy = route_data.get("strategy", "hybrid")
            if self.repo and run_id:
                self.repo.log_message(run_id, "AuthorAgent", f"Routing strategy: {strategy} ({route_data.get('reason')})")

        try:
            chunks = await self._retrieve_chunks(
                topic, 
                course_title=state.title if state else None,
                strategy=strategy
            )
        except Exception as e:
            logger.error(f"Retrieval failed for {topic} using {strategy}: {e}")
            chunks = []
        
        # Use Pydantic dot notation for type safety and clarity
        course_title = state.title if state else topic
        level = state.level if state else 'beginner'
        duration = state.duration_months if state else 3
        
        # Statistically scale depth and word count based on course duration
        if duration <= 1:
            config = {"depth": "introductory", "words": "600-900"}
        elif duration == 2:
            config = {"depth": "comprehensive overview", "words": "900-1200"}
        elif duration == 3:
            config = {"depth": "in-depth and detailed", "words": "1200-1600"}
        else:
            # Scale words by ~200 per extra month beyond 3
            base_words = 1600 + (min(duration, 12) - 3) * 200
            config = {"depth": "highly technical and exhaustive", "words": f"{base_words}-{base_words+400}"}
        
        depth_instruction = config["depth"]
        word_count = config["words"]

        chunk_text = "\n".join([f"CHUNK {i+1}: {c[:2500]}" for i, c in enumerate(chunks[:8])])
        grounding_instruction = "Use ONLY the following scraped knowledge chunks as factual source material." if chunks else "Use your internal knowledge to provide accurate educational content."

        prompt = f"""Generate a {depth_instruction} educational chapter on '{topic}' for the '{course_title}' course.
This course is designed to span {duration} months, so ensure the level of detail is appropriate for this timeframe.
The target audience is at the {level} level.

COMPLIANCE NOTICE: 
- Do NOT include PII (emails, phone numbers, or real names) in the content.
- Strictly avoid generating harmful, biased, or non-educational content.

 {grounding_instruction}
 IMPORTANT: For every factual claim made, cite the chunk number used (e.g., [Source Chunk 1]). 
 If the chunks do not contain enough information, state this clearly rather than hallucinating.

GROUND TRUTH KNOWLEDGE CHUNKS:
{chunk_text if chunks else "No specific source chunks available."}
Note: Synthesize information across these sources. If chunks contain conflicting info, prioritize the most recent or detailed one.

Structure:
1. Learning objectives
2. Key concepts with explanations
3. Code examples if applicable
4. Summary and exercises
Approximately {word_count} words."""
        
        current_prompt = prompt
        for attempt in range(max_retries + 1):
            try:
                response = await self._call_llm(
                    model=self.model,
                    messages=[{"role": "user", "content": current_prompt}],
max_tokens=1400
                )
                content = response.choices[0].message.content

                if reviewer and attempt < max_retries:
                    critique = await reviewer.validate_content_with_llm(content, topic)
                    if critique.get("semantic_pass"):
                        if self.repo and run_id:
                            self.repo.log_message(run_id, "AuthorAgent", f"Content passed review on attempt {attempt+1}")
                        break
                    else:
                        if self.repo and run_id:
                            self.repo.log_message(run_id, "AuthorAgent", f"Attempt {attempt+1} failed review. Feedback: {critique.get('feedback')}", "warning")
                        current_prompt = f"{prompt}\n\nREFINEMENT NEEDED: {critique.get('feedback')}. Focus strictly on the provided source chunks."
                        continue
                break # Exit loop if no reviewer or final attempt
            except Exception as e:
                if attempt == max_retries:
                    raise e

        try:
            return Chapter(
                title=topic,
                content=content,
                chapter_order=order,
                status="generated"
            )
        except Exception as e:
            logger.error(f"Error generating chapter for {topic} after retries: {e}")
            return None
    async def generate_multiple_chapters(self, topics: List[str], state: Optional[SyllabusState] = None, reviewer=None, max_retries: int = 1) -> List[Chapter]:
        """
        Parallel chapter generation for performance boost. Limits concurrency to avoid rate limits.
        """
        if len(topics) == 0:
            return []

        max_concurrent = 6
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_limited(topic: str, order: int) -> Optional[Chapter]:
            async with semaphore:
                return await self.generate_content(topic, state, order, reviewer)
        
        tasks = [generate_limited(topic, i) for i, topic in enumerate(topics)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        chapters = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate chapter {topics[i]}: {result}")
                chapters.append(Chapter(title=topics[i], content=f"Generation failed: {str(result)}", chapter_order=i, status="error"))
            elif result is None:
                logger.error(f"Failed to generate chapter {topics[i]}: returned None")
                chapters.append(Chapter(title=topics[i], content="Generation failed: unknown error", chapter_order=i, status="error"))
            else:
                chapters.append(result)
        
        return chapters


    async def _retrieve_chunks(self, query: str, k: int = 8, course_title: Optional[str] = None, strategy: str = "hybrid") -> List[str]:
        """
        TripleDB hybrid retrieval: Vector + KG + PG metadata.
        """
        if not self.manager:
            logger.error("TripleDBManager not available")
            return []
            
        search_results: Dict[str, Any] = await self.manager.hybrid_search(query, k=k, strategy=strategy)
        # Logic: Metadata -> KG Context (Structure) -> Vector (Facts)
        final_selection = []
        final_selection.extend(search_results['pg_courses'])
        final_selection.extend(search_results['kg_context']) # Elevated priority
        final_selection.extend(search_results['vector'])
        
        return final_selection[:12] # Slightly larger window for GPT-4o-mini

