import asyncio
from typing import List
import os
from pydantic import Field
from Domain.course import Chapter
from Domain.syllabus import SyllabusState
from openai import AsyncOpenAI

class AuthorAgent:
    def __init__(self, astra_db, repo=None):
        self.vector_store = astra_db
        self.openai_client = None
        self.repo = repo
        
        # Try OpenRouter first
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            try:
                self.openai_client = AsyncOpenAI(
                    api_key=openrouter_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
                print("✅ AuthorAgent using OpenRouter")
            except Exception as e:
                print(f"❌ OpenRouter init failed: {e}")
        
        # Fallback to Mistral
        if self.openai_client is None:
            mistral_key = os.getenv("MISTRAL_API_KEY")
            if mistral_key:
                self.openai_client = AsyncOpenAI(
                    api_key=mistral_key,
                    base_url="https://api.mistral.ai/v1"
                )
                self.model = os.getenv("LLM_MODEL", "mistral-small-latest")
                print("✅ AuthorAgent fallback to Mistral")
            else:
                raise ValueError("No valid LLM API key found. Set OPENROUTER_API_KEY or MISTRAL_API_KEY in .env")

    async def generate_content(self, topic: str, state: SyllabusState = None, order: int = 0) -> Chapter:
        """Generate chapter content. Returns a Domain Chapter object."""
        run_id = state.run_id if state else 0
        if self.repo:
            self.repo.log_message(run_id, "AuthorAgent", f"Starting generation for topic: {topic}")
            
        try:
            chunks = await self._retrieve_chunks(topic, course_title=state.title if state else None)
        except Exception as e:
            print(f"⚠️ Vector retrieval failed for {topic}: {e}")
            chunks = []
        
        # Use Pydantic dot notation for type safety and clarity
        course_title = state.title if state else topic
        level = state.level if state else 'beginner'
        duration = state.duration_months if state else 3
        
        # Adjust depth based on duration
        word_count = "800-1200" if duration <= 2 else "1200-2000"
        depth_instruction = "introductory" if duration <= 1 else "in-depth and comprehensive"

        chunk_text = "\n".join([f"CHUNK {i+1}: {c[:1000]}" for i, c in enumerate(chunks[:5])])
        grounding_instruction = "Use ONLY the following scraped knowledge chunks as factual source material." if chunks else "Use your internal knowledge to provide accurate educational content."

        prompt = f"""Generate a {depth_instruction} educational chapter on '{topic}' for the '{course_title}' course.
This course is designed to span {duration} months, so ensure the level of detail is appropriate for this timeframe.
The target audience is at the {level} level.

 {grounding_instruction}

Knowledge chunks:
{chunk_text if chunks else "No specific source chunks available."}

Structure:
1. Learning objectives
2. Key concepts with explanations
3. Code examples if applicable
4. Summary and exercises
Approximately {word_count} words."""
        
        try:
            response = await self.openai_client.chat.completions.create(
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
            print(f"❌ Error generating chapter for {topic}: {e}")
            return Chapter(
                title=topic,
                content=f"Error generating content: {str(e)}",
                chapter_order=order,
                status="error"
            )

    async def _retrieve_chunks(self, query: str, k: int = 5, course_title: str = None) -> List[str]:
        """
        Hybrid-ready retrieval. 
        In AstraDB, this often involves passing a metadata filter 
        to ensure relevance to the specific course context.
        """
        filters = {"course_title": course_title} if course_title else {}
        # Assuming your AstraVectorStore.query supports metadata filtering
        results = self.vector_store.query(query, k=k, filter=filters)
        return [result.get("document", "") for result in results]
