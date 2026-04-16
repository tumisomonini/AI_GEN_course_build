import re
import json
import logging
import asyncio
from typing import Dict, Optional, Any
from openai import AsyncOpenAI
import os

logger = logging.getLogger(__name__)

class ReviewerAgent:
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        self.client = openai_client or self._init_client()
        self.model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

    def _init_client(self):
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            return None
        base_url = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else "https://api.mistral.ai/v1"
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def validate_content_with_llm(self, content: str, topic: str) -> Dict[str, Any]:
        """Uses LLM to provide a semantic critique of the generated content."""
        if not self.client:
            return {"score": 0.8, "feedback": "LLM client not available, skipping semantic check."}
        
        prompt = (
            f"Critique this educational content for the topic '{topic}'.\n"
            "Return ONLY a JSON object with keys: 'accuracy' (0-1), 'depth' (0-1), 'clarity' (0-1), and 'feedback' (string).\n\n"
            f"Content: {content[:2000]}"
        )
        
        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model, 
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                res_data = json.loads(response.choices[0].message.content)
                # Calculate an average score
                avg_score = (res_data.get('accuracy', 0) + res_data.get('depth', 0) + res_data.get('clarity', 0)) / 3
                return {"score": round(avg_score, 2), "feedback": res_data.get('feedback', '')}
            except Exception as e:
                logger.error(f"ReviewerAgent LLM validation failed: {e}")
                await asyncio.sleep(1)
        
        return {"score": 0.5, "feedback": "Critique failed after retries."}

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
        placeholder_phrases = ['generation timeout', 'theory content for', 'placeholder']
        return not any(p in content.lower() for p in placeholder_phrases)

    def validate_style(self, content: str) -> bool:
        """Check content has basic structure — headings or paragraphs."""
        return bool(re.search(r'(#{1,3} .+|\n\n.{50,})', content))
