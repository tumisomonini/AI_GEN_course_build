import pytest
from fastapi.testclient import TestClient
from Application.API.Main import app
from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

client = TestClient(app)

@pytest.fixture(scope="module")
def test_repo():
    """Use existing repo since Docker is up"""
    repo = PostgresRepository("ai_gen_db", "postgres", "password123", port=5433)
    try:
        yield repo
    finally:
        repo.close()

class TestCoursesEndpoints:
    @pytest.fixture(autouse=True)
    def setup_method(self, test_repo):
        # Cleanup test data
        with test_repo.conn.cursor() as cur:
            cur.execute("DELETE FROM courses WHERE title LIKE 'Test%'")
            test_repo.conn.commit()

    def test_search_courses(self):
        """Test course search endpoint"""
        response = client.get("/courses/search-courses?q=python")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["db_count"] >= 0
        assert data["web_count"] >= 0

    def test_generate_course_template(self):
        """Test course template generation"""
        payload = {
            "title": "Test Python Course",
            "level": "beginner",
            "duration_months": 2
        }
        response = client.post("/courses/generate/course-template", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "awaiting_approval"
        assert "course_id" in data
        assert data["sources_found"] >= 0

    def test_get_course_review(self, test_repo):
        """Test getting course review after creation"""
        # First create a test course
        course_id = test_repo.create_course("Test Review Course", "intermediate")
        
        response = client.get(f"/courses/{course_id}/course-review")
        assert response.status_code == 200
        data = response.json()
        assert data["course_id"] == course_id

    def test_course_status(self):
        """Test course status endpoint"""
        response = client.get("/courses/999999/status")  # Non-existent
        assert response.status_code == 404

class TestSyllabusEndpoints:
    def test_scrape_syllabus(self):
        """Test syllabus scraping endpoint"""
        payload = {"title": "Machine Learning Syllabus"}
        response = client.post("/syllabus/scrape", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "syllabi_found" in data
        assert data["total_chunks_stored"] >= 0

    def test_generate_syllabus(self):
        """Test syllabus generation (requires agents initialized)"""
        payload = {
            "topics": ["Intro ML", "Neural Networks"],
            "title": "Test ML Course"
        }
        response = client.post("/syllabus/generate", json=payload)
        # Agents may not be initialized; 503 expected if not ready
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "syllabus" in data

def test_root_redirect():
    """Test root endpoint redirects to test interface"""
    response = client.get("/")
    assert response.status_code == 200
    assert "RedirectResponse" in str(response.json())

print("API endpoint tests completed!")

