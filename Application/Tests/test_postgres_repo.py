import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Infrastructure.relationalDB.postgres_repo import PostgresRepository

DB_PARAMS = {
    "dbname": "ai_gen_db",
    "user": "postgres",
    "password": "password123",
    "host": "localhost",
    "port": 5432,
}


@pytest.fixture(scope="module")
def repo():
    r = PostgresRepository(**DB_PARAMS)
    yield r
    r.close()


# @pytest.fixture(autouse=True)
# def cleanup(repo):
#     yield
#     repo.conn.rollback()  # Removed: uses pool


# ── Schema ────────────────────────────────────────────────────────────────────

def test_tables_exist(repo):
    with repo.get_cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = {row[0] for row in cur.fetchall()}
        expected = {"users", "courses", "chapters", "syllabus", "runs", "run_agents",
                    "logs", "approvals", "reviews", "metrics", "costs", "artifacts", "exports"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"



# ── create_course ─────────────────────────────────────────────────────────────

def test_create_course_returns_id(repo):
    course_id = repo.create_course("Test Course", "Beginners", "A test course")
    assert isinstance(course_id, int) and course_id > 0


def test_create_course_without_description(repo):
    course_id = repo.create_course("No Desc Course", "Advanced")
    assert course_id > 0


# ── create_course_from_template ───────────────────────────────────────────────

def test_create_course_from_template(repo):
    template = {
        "title": "Python Basics",
        "description": "Learn Python",
        "level": "Beginner",
        "chapters": [{"title": "Intro", "units": ["Unit 1"]}],
    }
    course_id = repo.create_course_from_template(template)
    assert course_id > 0


# ── get_course_review ─────────────────────────────────────────────────────────

def test_get_course_review(repo):
    template = {"title": "Review Test", "level": "Intermediate"}
    course_id = repo.create_course_from_template(template)

    result = repo.get_course_review(course_id)
    assert result["course"]["course_id"] == course_id
    assert result["course"]["title"] == "Review Test"
    assert "template" in result
    assert "metadata" in result


def test_get_course_review_not_found(repo):
    with pytest.raises(ValueError):
        repo.get_course_review(999999)


# ── get_chapters ──────────────────────────────────────────────────────────────

def test_get_chapters_empty(repo):
    course_id = repo.create_course("Empty Course", "All")
    chapters = repo.get_chapters(course_id)
    assert chapters == []


def test_get_chapters_ordered(repo):
    course_id = repo.create_course("Ordered Course", "All")
    with repo.get_cursor() as cur:
        cur.execute("DELETE FROM chapters WHERE course_id = %s", (course_id,))
        cur.execute(
            "INSERT INTO chapters (course_id, title, chapter_order) VALUES (%s, %s, %s), (%s, %s, %s)",
            (course_id, "Ch2", 2, course_id, "Ch1", 1),
        )
    chapters = repo.get_chapters(course_id)
    assert [c["chapter_order"] for c in chapters] == [1, 2]


# ── log_run / get_logs_for_run ────────────────────────────────────────────────

def test_log_and_retrieve(repo):
    course_id = repo.create_course("Log Course", "All")
    with repo.get_cursor() as cur:
        cur.execute(
            "INSERT INTO runs (course_id, workflow_name) VALUES (%s, %s) RETURNING run_id",
            (course_id, "test_workflow"),
        )
        run_id = cur.fetchone()[0]

    repo.log_run(run_id, "test_agent", "hello", "info")
    logs = repo.get_logs_for_run(run_id)
    assert len(logs) == 1
    assert logs[0]["message"] == "hello"
    assert logs[0]["level"] == "info"


# ── update_course_status ──────────────────────────────────────────────────────

def test_update_course_status(repo):
    course_id = repo.create_course("Status Course", "All")
    repo.update_course_status(course_id, "published")

    with repo.get_cursor() as cur:
        cur.execute("SELECT status FROM courses WHERE course_id = %s", (course_id,))
        assert cur.fetchone()[0] == "published"


# ── create_approval ───────────────────────────────────────────────────────────

def test_create_approval_approved(repo):
    course_id = repo.create_course("Approval Course", "All")
    run_id = repo.create_approval(course_id, approved=True, comments="Looks good")
    assert run_id > 0


def test_create_approval_rejected(repo):
    course_id = repo.create_course("Reject Course", "All")
    run_id = repo.create_approval(course_id, approved=False, comments="Needs work")
    assert run_id > 0


# ── search_courses ────────────────────────────────────────────────────────────

def test_search_courses(repo):
    repo.create_course_from_template({"title": "Machine Learning 101", "level": "Beginner"})
    results = repo.search_courses("Machine Learning")
    assert any("Machine Learning" in r["title"] for r in results)


def test_search_courses_no_match(repo):
    results = repo.search_courses("xyznonexistent12345")
    assert results == []


# ── get_metrics_for_run ───────────────────────────────────────────────────────

def test_get_metrics_empty(repo):
    course_id = repo.create_course("Metrics Course", "All")
    with repo.get_cursor() as cur:
        cur.execute(
            "INSERT INTO runs (course_id, workflow_name) VALUES (%s, %s) RETURNING run_id",
            (course_id, "metrics_test"),
        )
        run_id = cur.fetchone()[0]
    metrics = repo.get_metrics_for_run(run_id)
    assert metrics == []
