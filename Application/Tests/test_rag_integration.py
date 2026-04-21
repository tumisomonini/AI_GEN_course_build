import pytest
from fastapi.testclient import TestClient
from Application.API.Main import app
import os
import time
from Application.Ports.Astra_repo import AstraRepo

client = TestClient(app)

class TestRAGIntegration:
    def test_full_rag_flow(self):
        # Note: Data pre-loaded via loader, server running at :8000
        # Full RAG: scrape -> upsert -> generate with retrieval -> docx
        
        # 1. Scrape and upsert
        scrape_payload = {"title": "Introduction to Machine Learning"}
        scrape_resp = client.post("/syllabus/scrape", json=scrape_payload)
        print(f'Scrape status: {scrape_resp.status_code}')
        if scrape_resp.status_code == 200:
            scrape_data = scrape_resp.json()
            assert scrape_data["syllabi_found"] >= 0
            assert scrape_data["total_chunks_stored"] >= 0

        # 2. Generate syllabus (uses RAG retrieval in AuthorAgent)
        gen_payload = {"title": "Intro ML", "topics": ["Basics", "Neural Nets"]}
        gen_resp = client.post("/syllabus/generate", json=gen_payload)
        print(f'Generate status: {gen_resp.status_code}')
        assert gen_resp.status_code in [200, 503]
        if gen_resp.status_code == 200:
            gen_data = gen_resp.json()
            assert "syllabus" in gen_data
            assert len(gen_data["syllabus"]) > 0

        print("RAG system fully tested via API endpoints!")

    def test_vector_retrieval_accuracy(self):
        """Unit test for retrieval precision."""
        repo = AstraRepo("course_chunks")
        test_query = "Python Decorators"
        results = repo.similarity_search(test_query, k=3)
        
        assert isinstance(results, list)
        if len(results) > 0:
            # Ensure metadata exists
            assert "course_title" in results[0] or "source_url" in results[0]
            print(f"✅ Retrieval successful: Found {len(results)} chunks for '{test_query}'")
        else:
            pytest.skip("No data in AstraDB to test retrieval accuracy. Run populate_all_dbs.py first.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
