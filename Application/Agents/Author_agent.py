from typing import Dict, List
from sentence_transformers import SentenceTransformer
from openai import OpenAI

class AuthorAgent:
    def __init__(self, astra_db, openai_api_key: str):
        self.vector_store = astra_db
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.openai_client = OpenAI(api_key=openai_api_key)

    def generate_content(self, topic: str) -> str:
        chunks = self._retrieve_chunks(topic)
        prompt = f"Generate a chapter on {topic} using the following chunks:\n\n" + "\n".join(chunks)
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _retrieve_chunks(self, query: str, k: int = 5) -> List[str]:
        query_embedding = self.embedding_model.encode(query)
        results = self.vector_store.query(query_embedding, k=k)
        return [result["text"] for result in results]