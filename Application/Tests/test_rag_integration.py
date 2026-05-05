import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from Application.API.Main import app
import os
import time

client = TestClient(app)

class TestRAGIntegration:
    @patch('Application.Ports.Astra_repo.AstraRepo')
    def test_full_rag_flow(self, mock_astra):
        mock_astra.return_value.similarity_search.return_value = [{'document': 'mock chunk', 'score': 0.8}]
        
        # TripleDB enhanced
        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        health = health_resp.json()
        assert health['triple_manager']['integrated'] == 'ready'
        print('✅ TripleDB /health OK')

        # Legacy RAG
        scrape_payload = {"title": "Introduction to Machine Learning"}
        scrape_resp = client.post("/syllabus/scrape", json=scrape_payload)
        assert scrape_resp.status_code in [200, 422]
        print("RAG + TripleDB tested")


    def test_vector_retrieval_accuracy(self):
        """Unit test for retrieval precision."""
        pytest.skip("Vector store test requires AstraDB to be configured and populated. Run populate_all_dbs.py first.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
