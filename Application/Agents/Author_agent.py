from typing import Dict, List
from openai import OpenAI

class AuthorAgent:
    def __init__(self, astra_db, llm_api_key: str, mock_mode: bool = False):
        self.mock_mode = mock_mode
        if not mock_mode:
            self.vector_store = astra_db
            self.openai_client = OpenAI(
                api_key=llm_api_key,
                base_url="https://openrouter.ai/api/v1"
            )

    def generate_content(self, topic: str) -> str:
        if self.mock_mode:
            return f"# {topic}\n\nThis is mock content for {topic}. In a real implementation, this would be generated using AI based on retrieved knowledge chunks.\n\n## Key Concepts\n- Concept 1\n- Concept 2\n\n## Examples\n- Example code or explanation"

        chunks = self._retrieve_chunks(topic)
        prompt = f"Generate a chapter on {topic} using the following chunks:\n\n" + "\n".join(chunks)
        response = self.openai_client.chat.completions.create(
            model="openai/gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _retrieve_chunks(self, query: str, k: int = 5) -> List[str]:
        results = self.vector_store.query(query, k=k)
        return [result["text"] for result in results]