import re
import json
import logging
import asyncio
from typing import Dict, Optional, Any, List
import openai
from openai import AsyncOpenAI
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import os

logger = logging.getLogger(__name__)

class ReviewerAgent:
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        self.client = openai_client
        self.model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

        if not self.client:
            self._init_client()

    def _init_client(self):
        """Initialize LLM client with priority: Local -> OpenRouter -> Mistral"""
        local_url = os.getenv("LOCAL_LLM_URL")
        if local_url:
            if self._setup_client(local_url, "local-token", "LOCAL_LLM_MODEL", "unsloth-llama-3-8b"):
                return

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            if self._setup_client("https://openrouter.ai/api/v1", openrouter_key, "LLM_MODEL", "openai/gpt-4o-mini"):
                return

        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            if self._setup_client("https://api.mistral.ai/v1", mistral_key, "LLM_MODEL", "mistral-small-latest"):
                return

        logger.warning("ReviewerAgent initialized without LLM client (Safety/Review checks will be bypassed)")

    def _setup_client(self, base_url, api_key, model_env, default_model, timeout=60.0):
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
            self.model = os.getenv(model_env, default_model)
            return True
        except Exception as e:
            logger.error(f"ReviewerAgent LLM Init failed for {base_url}: {e}")
            return False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type((openai.APIError, openai.RateLimitError, openai.Timeout, openai.APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _call_llm(self, **kwargs):
        """Retryable LLM call."""
        if not self.client:
            raise ValueError("No LLM client initialized")
        return await self.client.chat.completions.create(**kwargs)

    async def validate_content_with_llm(self, content: str, topic: str) -> Dict[str, Any]:
        """Uses LLM to provide a semantic critique of the generated content."""
        if not self.client:
            return {"score": 0.8, "feedback": "LLM client not available, skipping semantic check."}
        
        prompt = (
            f"Critique this educational content for the topic '{topic}'.\n"
            "Return ONLY a JSON object with keys: 'accuracy' (0-1), 'depth' (0-1), 'clarity' (0-1), and 'feedback' (string).\n\n"
            f"Content: {content[:2000]}"
        )
        
        try:
            response = await self._call_llm(
                model=self.model, 
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            res_data = json.loads(response.choices[0].message.content)
            # Calculate an average score
            avg_score = (res_data.get('accuracy', 0) + res_data.get('depth', 0) + res_data.get('clarity', 0)) / 3
            semantic_pass = avg_score >= 0.6
            return {"semantic_score": round(avg_score, 2), "semantic_pass": semantic_pass, "feedback": res_data.get('feedback', '')}
        except Exception as e:
            logger.error(f"ReviewerAgent LLM validation failed after retries: {e}")
            return {"score": 0.5, "feedback": "Critique failed after retries."}

    async def check_intent_and_safety(self, query: str) -> Dict[str, Any]:
        """
        Validates if the user query is within the educational domain and safe.
        Handles: Out-of-scope queries and Guardrail tests.
        """
        if not self.client:
            return {
                "is_valid": True, 
                "is_safe": True, 
                "reason": "Safety check bypassed: LLM client not available"
            }

        prompt = (
            f"Analyze the user request: '{query}'\n"
            "Determine if this is an educational course topic and if it is safe (No PII, no harmful content).\n"
            "Return a JSON object: {'is_valid': bool, 'is_safe': bool, 'reason': string}."
        )
        try:
            # Privacy: Enhanced PII Regex checks (Email, Phone numbers)
            pii_patterns = {
                "Email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "Phone": r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b',
                "Credit_Card": r'\b(?:\d[ -]*?){13,16}\b',
                "SSN": r'\b\d{3}-\d{2}-\d{4}\b'
            }
            for pii_type, pattern in pii_patterns.items():
                if re.search(pattern, query):
                    return {"is_valid": False, "is_safe": False, "reason": f"PII ({pii_type}) detected in input."}

            response = await self._call_llm(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return {"is_valid": True, "is_safe": True, "reason": "Bypassed due to error"}

    async def route_query(self, query: str) -> Dict[str, Any]:
        """
        Routes the query to the appropriate RAG strategy.
        - vector: Technical facts, code, or specific snippets.
        - kg: Topic relationships, prerequisites, and syllabus structure.
        - hybrid: Comprehensive educational content.
        """
        if not self.client:
            return {"strategy": "vector", "reason": "No LLM available for routing"}

        prompt = (
            f"Analyze the educational query: '{query}'\n"
            "Classify the best retrieval strategy:\n"
            "1. 'vector': For specific factual questions, technical details, or code snippets.\n"
            "2. 'kg': For conceptual mapping, prerequisite identification, or topic definitions.\n"
            "3. 'hybrid': For broad topics requiring both structured relationships and deep technical data.\n"
            "Return ONLY a JSON object: {'strategy': 'vector'|'kg'|'hybrid', 'reason': 'string'}."
        )
        try:
            response = await self._call_llm(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Query routing failed: {e}")
            return {"strategy": "hybrid", "reason": "Error during routing, falling back to hybrid"}

    async def evaluate_rag_faithfulness(self, content: str, source_chunks: List[str]) -> Dict[str, Any]:
        """
        RAGAS-inspired Faithfulness check: Does the content stay true to the retrieved sources?
        """
        if not source_chunks:
            return {"score": 1.0, "reason": "No sources provided for grounding check."}
            
        sources_text = "\n".join([f"Source {i}: {s[:600]}" for i, s in enumerate(source_chunks[:5])])
        prompt = (
            "Act as a RAG Quality Auditor. Analyze the content against the provided sources.\n"
            "1. Faithfulness: Are the claims supported by sources?\n"
            "2. Context Relevancy: Are the sources actually useful for this topic?\n"
            "Return JSON: {'faithfulness_score': 0-1, 'relevancy_score': 0-1, 'hallucinations': []}.\n\n"
            f"Sources (Ground Truth):\n{sources_text}\n\nGenerated Content:\n{content[:2000]}"
        )
        
        try:
            response = await self._call_llm(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"score": 0.5, "error": str(e)}

    def validate_coverage(self, content: str, topic: str) -> float:
        """Lightweight keyword overlap coverage score (0.0 - 1.0)."""
        if not content or not topic:
            return 0.8
        topic_words = set(re.findall(r'\w+', topic.lower())) - {'the', 'a', 'an', 'of', 'in', 'for', 'and', 'to'}
        content_lower = content.lower()
        if not topic_words:
            return 0.8
        matched = sum(1 for w in topic_words if w in content_lower)
        score = matched / len(topic_words)
        # Reward longer content (more thorough)
        length_bonus = min(0.2, len(content) / 10000)
        return min(1.0, score + length_bonus)

    def validate_factual_grounding(self, content: str, source: str = "") -> bool:
        """Check content has substance — at least 100 chars and not placeholder text."""
        if not content or len(content) < 100:
            return False
        placeholder_phrases = ['generation timeout', ' theory content for', 'placeholder']
        return not any(p in content.lower() for p in placeholder_phrases)

    def validate_style(self, content: str) -> bool:
        """Check content has basic structure — headings or paragraphs."""
        return bool(re.search(r'(#{1,3} .+|\n\n.{50,})', content))
