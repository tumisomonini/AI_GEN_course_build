import asyncio
from typing import List
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
    def __init__(self, vector_store, repo=None, kg=None):
        self.vector_store = vector_store
        self.openai_client = None
        self.repo = repo
        self.kg = kg  # Knowledge Graph (Neo4j)

        # 1. Try Local Inference (Unsloth/vLLM/Ollama)
        local_url = os.getenv("LOCAL_LLM_URL")
        if local_url:
            if self._setup_client(local_url, "local-token", "LOCAL_LLM_MODEL", "unsloth-llama-3-8b", timeout=120.0):
                return
        
        # Try OpenRouter first
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            if self._setup_client("https://openrouter.ai/api/v1", openrouter_key, "LLM_MODEL", "openai/gpt-4o-mini"):
                return
        
        # Fallback to Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            if self._setup_client("https://api.mistral.ai/v1", mistral_key, "LLM_MODEL", "mistral-small-latest"):
                return
        
        raise ValueError("No valid LLM API key found. Set OPENROUTER_API_KEY or MISTRAL_API_KEY in .env")

    def _setup_client(self, base_url, api_key, model_env, default_model, timeout=60.0):
        try:
            self.openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
            self.model = os.getenv(model_env, default_model)
            print(f"✅ AuthorAgent using {base_url} with model: {self.model}")
            return True
        except Exception as e:
            print(f"⚠️ LLM Init failed for {base_url}: {e}")
            return False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type((openai.APIError, openai.RateLimitError, openai.Timeout, openai.APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _call_llm(self, **kwargs):
        """Retryable LLM call."""
        if not self.openai_client:
            raise ValueError("No LLM client initialized")
        return await self.openai_client.chat.completions.create(**kwargs)

    async def generate_content(self, topic: str, state: SyllabusState = None, order: int = 0, reviewer=None) -> Chapter:
        """Generate chapter content. Returns a Domain Chapter object."""
        run_id = state.run_id if (state and state.run_id and state.run_id > 0) else None
        if self.repo and run_id:
            self.repo.log_message(run_id, "AuthorAgent", f"Starting generation for topic: {topic}")
            
        # Query Routing Implementation
        strategy = "hybrid"
        if reviewer:
            route_data = await reviewer.route_query(topic)
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
        
        # Define configuration mapping for different durations
        duration_configs = {
            1: {"depth": "introductory", "words": "600-900"},
            2: {"depth": "comprehensive overview", "words": "900-1200"},
            3: {"depth": "in-depth and detailed", "words": "1200-1600"},
        }
        
        # Get config with a fallback for durations > 3 months
        config = duration_configs.get(duration, {"depth": "highly technical and exhaustive", "words": "1600-2200"})
        
        depth_instruction = config["depth"]
        word_count = config["words"]

        chunk_text = "\n".join([f"CHUNK {i+1}: {c[:1000]}" for i, c in enumerate(chunks[:5])])
        grounding_instruction = "Use ONLY the following scraped knowledge chunks as factual source material." if chunks else "Use your internal knowledge to provide accurate educational content."

        prompt = f"""Generate a {depth_instruction} educational chapter on '{topic}' for the '{course_title}' course.
This course is designed to span {duration} months, so ensure the level of detail is appropriate for this timeframe.
The target audience is at the {level} level.

COMPLIANCE NOTICE: 
- Do NOT include PII (emails, phone numbers, or real names) in the content.
- Strictly avoid generating harmful, biased, or non-educational content.

 {grounding_instruction}
 IMPORTANT: For every factual claim made, cite the chunk number used (e.g., [Chunk 1]). 
 If the chunks do not contain enough information, state this clearly rather than hallucinating.

Knowledge chunks (Synthesize information across these sources):
{chunk_text if chunks else "No specific source chunks available."}
Note: If chunks contain conflicting info, prioritize the most recent or detailed one.

Structure:
1. Learning objectives
2. Key concepts with explanations
3. Code examples if applicable
4. Summary and exercises
Approximately {word_count} words."""
        
        try:
            response = await self._call_llm(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )
            if self.repo and run_id:
                self.repo.log_message(run_id, "AuthorAgent", f"Successfully generated content for {topic}", "info")
                
            return Chapter(
                title=topic,
                content=response.choices[0].message.content,
                chapter_order=order,
                status="generated"
            )
        except Exception as e:
            print(f"❌ Error generating chapter for {topic} after retries: {e}")
            return Chapter(
                title=topic,
                content=f"Error generating content: {str(e)}",
                chapter_order=order,
                status="error"
            )

    async def _retrieve_chunks(self, query: str, k: int = 8, course_title: str = None, strategy: str = "vector") -> List[str]:
        """
        Enhanced retrieval with expanded context window and metadata filtering.
        Supports Vector, KG, and Hybrid strategies.
        """
        if not self.vector_store:
            logger.error("Vector store not initialized.")
            return []
            
        filters = {"course_title": course_title} if course_title else {}
        try:
            final_chunks = []

            # Path 1: Knowledge Graph (Structural context)
            if strategy in ["kg", "hybrid"] and self.kg:
                details = self.kg.get_topic_details(query)
                if details:
                    final_chunks.append(f"CONCEPTUAL OVERVIEW: {details.get('description')}")
                
                prereqs = self.kg.get_prerequisites(query)
                if prereqs:
                    final_chunks.append(f"PREREQUISITES: This topic builds upon {', '.join(prereqs)}.")

            # Path 2: Vector Store (Technical depth)
            if strategy in ["vector", "hybrid"]:
                results = self.vector_store.query(query, k=k, filter=filters)
                if results:
                    final_chunks.extend([result.get("document", "") for result in results if result.get("document")])

            return final_chunks
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
