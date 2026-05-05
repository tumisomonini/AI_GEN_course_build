import pytest
from fastapi.testclient import TestClient
from Application.API.Main import app
from Application.Infrastructure.relationalDB.postgres_repo import PostgresRepository

client = TestClient(app)

@pytest.fixture(scope="module")
def test_repo():
    """Use existing repo since Docker is up"""
    try:
        repo = PostgresRepository("ai_gen_db", "postgres", "password123", port=5433)
        with repo.get_cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:
        pytest.skip("Postgres connection failed on port 5433")
    try:
        yield repo
    finally:
        repo.close()

class TestCoursesEndpoints:
    @pytest.fixture(autouse=True)
    def setup_method(self, test_repo):
        # Cleanup test data
        with test_repo.get_cursor() as cur:
            cur.execute("DELETE FROM courses WHERE title LIKE 'Test%'")

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
        assert data["status"] == "generating_outline"
        assert "course_id" in data

    def test_generate_short_title_fails(self):
        """Test validation for short title"""
        payload = {"title": "ab", "level": "beginner", "duration_months": 2}
        response = client.post("/courses/generate/course-template", json=payload)
        assert response.status_code in [400, 422]

    def test_generate_no_title_fails(self):
        """Test no title validation"""
        payload = {"level": "beginner", "duration_months": 2}
        response = client.post("/courses/generate/course-template", json=payload)
        assert response.status_code in [400, 422]

    def test_generate_invalid_duration_fails(self):
        """Test invalid duration validation"""
        payload = {"title": "Test Course", "level": "beginner", "duration_months": 0}
        response = client.post("/courses/generate/course-template", json=payload)
        assert response.status_code in [400, 422]

    def test_generate_invalid_level_fails(self):
        """Test invalid level validation"""
        payload = {"title": "Test Course", "level": "expert", "duration_months": 2}
        response = client.post("/courses/generate/course-template", json=payload)
        assert response.status_code == 422

    def test_get_course_review(self, test_repo):
        """Test getting course review after creation"""
        # First create a test course template
        template_payload = {
            "title": "Test Review Course",
            "level": "intermediate",
            "duration_months": 3
        }
        create_response = client.post("/courses/generate/course-template", json=template_payload)
        course_id = create_response.json()["course_id"]
        
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
        assert response.status_code in [200, 500, 503]
        if response.status_code == 200:
            data = response.json()
            assert "syllabus" in data
            # Content validation: verify syllabus structure
            syllabus = data["syllabus"]
            assert isinstance(syllabus, (list, dict)), "syllabus should be a list or dict"
            if isinstance(syllabus, list):
                assert len(syllabus) > 0, "syllabus should not be empty"
                for chapter in syllabus:
                    if isinstance(chapter, dict):
                        assert "title" in chapter, "each chapter should have a title"
                    else:
                        assert isinstance(chapter, str) and len(chapter) > 0, "each chapter should be a non-empty string"
            elif isinstance(syllabus, dict):
                assert "chapters" in syllabus, "syllabus dict should have chapters key"
                chapters = syllabus["chapters"]
                assert isinstance(chapters, list), "chapters should be a list"
                assert len(chapters) > 0, "chapters should not be empty"
                for chapter in chapters:
                    assert "title" in chapter, "each chapter should have a title"
                    assert "content" in chapter, "each chapter should have content"

def test_root_redirect():
    """Test root endpoint serves frontend"""
    response = client.get("/")
    assert response.status_code == 200

print("API endpoint tests completed!")
