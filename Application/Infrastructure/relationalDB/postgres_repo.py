import psycopg2
from typing import List, Dict, Optional, Any

class PostgresRepository:
    def __init__(self, dbname: str, user: str, password: str, host: str = "localhost", port: int = 5433):
        self.conn_params = {
            'dbname': dbname,
            'user': user,
            'password': password,
            'host': host,
            'port': port
        }
        self.conn = psycopg2.connect(**self.conn_params)

    def init_schema(self) -> None:
        """Initialize the full PostgreSQL schema with all tables and indexes."""
        schema_sql = """
-- Core Tables
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    audience VARCHAR(255),
    created_by INT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'
);

CREATE TABLE chapters (
    chapter_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    chapter_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'
);

CREATE TABLE syllabus (
    syllabus_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'
);

-- Workflow Tables
CREATE TABLE runs (
    run_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    workflow_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'
);

CREATE TABLE run_agents (
    run_agent_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'
);

CREATE TABLE logs (
    log_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    message TEXT NOT NULL,
    level VARCHAR(50) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Approval Tables
CREATE TABLE approvals (
    approval_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    chapter_id INT REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    approver_id INT REFERENCES users(user_id),
    status VARCHAR(50) DEFAULT 'pending',
    comments TEXT,
    approved_at TIMESTAMP
);

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    chapter_id INT REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    reviewer_id INT REFERENCES users(user_id),
    feedback TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metrics Tables
CREATE TABLE metrics (
    metric_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    metric_name VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE costs (
    cost_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    cost_type VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Artifact Tables
CREATE TABLE artifacts (
    artifact_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exports (
    export_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    artifact_id INT REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'
);

-- Indexes
CREATE INDEX idx_courses_created_by ON courses(created_by);
CREATE INDEX idx_courses_status ON courses(status);
CREATE INDEX idx_chapters_course_id ON chapters(course_id);
CREATE INDEX idx_chapters_order ON chapters(chapter_order);
CREATE INDEX idx_runs_course_id ON runs(course_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_logs_run_id ON logs(run_id);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_approvals_run_id ON approvals(run_id);
CREATE INDEX idx_approvals_chapter_id ON approvals(chapter_id);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_metrics_run_id ON metrics(run_id);
CREATE INDEX idx_metrics_agent_name ON metrics(agent_name);
CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);
        """
        cur = self.conn.cursor()
        cur.execute(schema_sql)

    # Existing methods (updated column names to match schema)
    def create_course(self, title: str, audience: str, description: Optional[str] = None, created_by: Optional[int] = None) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO courses (title, description, audience, created_by) 
            VALUES (%s, %s, %s, %s) RETURNING course_id
            """,
            (title, description, audience, created_by)
        )
        course_id = cur.fetchone()[0]
        return course_id

    def get_chapters(self, course_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT chapter_id, title, content, chapter_order, status 
            FROM chapters 
            WHERE course_id = %s 
            ORDER BY chapter_order
            """,
            (course_id,)
        )
        columns = ["chapter_id", "title", "content", "chapter_order", "status"]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def log_run(self, run_id: int, agent_name: str, message: str, level: str = "info") -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO logs (run_id, agent_name, message, level) 
            VALUES (%s, %s, %s, %s)
            """,
            (run_id, agent_name, message, level)
        )

    # Example query methods from task
    def get_chapters_for_course(self, course_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT chapter_id, title, content, chapter_order, status
            FROM chapters
            WHERE course_id = %s
            ORDER BY chapter_order
            """,
            (course_id,)
        )
        columns = ["chapter_id", "title", "content", "chapter_order", "status"]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_approvals_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT a.approval_id, u.username AS approver, a.status, a.comments, a.approved_at
            FROM approvals a
            JOIN users u ON a.approver_id = u.user_id
            WHERE a.run_id = %s
            """,
            (run_id,)
        )
        columns = ["approval_id", "approver", "status", "comments", "approved_at"]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_metrics_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT metric_name, value, created_at
            FROM metrics
            WHERE run_id = %s
            ORDER BY created_at
            """,
            (run_id,)
        )
        columns = ["metric_name", "value", "created_at"]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_logs_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT agent_name, message, level, created_at
            FROM logs
            WHERE run_id = %s
            ORDER BY created_at
            """,
            (run_id,)
        )
        columns = ["agent_name", "message", "level", "created_at"]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    # NEW METHODS FOR COURSE WORKFLOW
    def create_course_from_template(self, template: dict, created_by: Optional[int] = None) -> int:
        """Create course + save template as syllabus JSON"""
        import json
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO courses (title, description, audience, created_by, status) 
            VALUES (%s, %s, %s, %s, %s) RETURNING course_id
            """,
            (
                template.get("title", "Untitled Course"),
                template.get("description"),
                template.get("audience", template.get("level")),
                created_by,
                "draft"
            )
        )
        course_id = cur.fetchone()[0]
        
        cur.execute(
            "INSERT INTO syllabus (course_id, content, status) VALUES (%s, %s::jsonb, %s)",
            (course_id, json.dumps(template), "draft")
        )
        
        cur.execute(
            "INSERT INTO runs (course_id, workflow_name, status) VALUES (%s, %s, %s)",
            (course_id, "template_generation", "completed")
        )
        self.conn.commit()
        return course_id

    def get_course_review(self, course_id: int) -> Dict[str, Any]:
        """Get full course review data for frontend"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT course_id, title, audience, status, created_at FROM courses WHERE course_id = %s",
            (course_id,)
        )
        course_row = cur.fetchone()
        if not course_row:
            raise ValueError(f"Course {course_id} not found")
        course = dict(zip(["course_id", "title", "audience", "status", "created_at"], course_row))

        cur.execute(
            "SELECT content FROM syllabus WHERE course_id = %s ORDER BY syllabus_id DESC LIMIT 1",
            (course_id,)
        )
        syllabus_row = cur.fetchone()
        template = syllabus_row[0] if syllabus_row else {}

        cur.execute(
            "SELECT status, workflow_name FROM runs WHERE course_id = %s ORDER BY run_id DESC LIMIT 1",
            (course_id,)
        )
        run_row = cur.fetchone()
        run_status = dict(zip(["status", "workflow_name"], run_row)) if run_row else {}

        scraping_result = template.get("scraping_result", {})
        course_status = course.get("status", "draft")
        has_real_content = course_status in ("completed", "published")

        return {
            "course": course,
            "template": template,
            "run_status": run_status,
            "scraping_result": scraping_result,
            "metadata": {
                "status": course_status,
                "run_status": run_status.get("status", "unknown"),
                "has_real_content": has_real_content,
                "is_real_data": scraping_result.get("is_real_data", False),
                "total_sources": scraping_result.get("total_sources", 0),
                "quality_score": scraping_result.get("quality_score", 85),
                "total_content_words": scraping_result.get("total_content", "N/A"),
                "sources": scraping_result.get("sources", []),
            }
        }

    def create_approval(self, course_id: int, approved: bool, comments: Optional[str] = None, created_by: Optional[int] = None) -> int:
        """Create approval record and update course status"""
        # Get latest run_id
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO runs (course_id, workflow_name, status) 
            VALUES (%s, %s, %s) RETURNING run_id
            """,
            (course_id, "approval", "running")
        )
        run_id = cur.fetchone()[0]
        
        # Log approval
        cur.execute(
            """
            INSERT INTO approvals (run_id, status, comments, approver_id) 
            VALUES (%s, %s, %s, %s)
            """,
            (run_id, "approved" if approved else "rejected", comments, created_by)
        )
        
        self.conn.commit()
        return run_id

    def update_course_status(self, course_id: int, status: str) -> None:
        """Update course status"""
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE courses SET status = %s WHERE course_id = %s
            """,
            (status, course_id)
        )
        self.conn.commit()

    def update_course_metadata(self, course_id: int, metadata: Dict[str, Any]) -> None:
        """Update course metadata (JSON column or latest syllabus)"""
        import json
        cur = self.conn.cursor()
        if 'status' in metadata:
            cur.execute(
                "UPDATE courses SET status = %s WHERE course_id = %s",
                (metadata['status'], course_id)
            )
        # Update latest syllabus row using a subquery (PostgreSQL doesn't support ORDER BY/LIMIT in UPDATE)
        cur.execute(
            """
            UPDATE syllabus SET content = content || %s::jsonb
            WHERE syllabus_id = (
                SELECT syllabus_id FROM syllabus WHERE course_id = %s ORDER BY syllabus_id DESC LIMIT 1
            )
            """,
            (json.dumps(metadata), course_id)
        )
        self.conn.commit()

    def log_message(self, run_id: int, agent_name: str, message: str, level: str = "info") -> None:
        """Log message for run"""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO logs (run_id, agent_name, message, level) 
            VALUES (%s, %s, %s, %s)
            """,
            (run_id, agent_name, message, level)
        )
        self.conn.commit()

    def get_course_status(self, course_id: int) -> Dict[str, Any]:
        """Lightweight status check — only fetches status, no syllabus content"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT status FROM courses WHERE course_id = %s",
            (course_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Course {course_id} not found")
        return {"course_id": course_id, "status": row[0]}

    def search_courses(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Search courses by title or audience"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT c.course_id, c.title, c.audience, c.status, c.created_at,
                   s.content->>'level' AS level, s.content->>'duration_months' AS duration_months
            FROM courses c
            LEFT JOIN LATERAL (
                SELECT content FROM syllabus WHERE course_id = c.course_id ORDER BY syllabus_id DESC LIMIT 1
            ) s ON true
            WHERE c.title ILIKE %s OR c.audience ILIKE %s
            ORDER BY c.created_at DESC
            LIMIT %s
            """,
            (f'%{query}%', f'%{query}%', limit)
        )
        columns = ["course_id", "title", "audience", "status", "created_at", "level", "duration_months"]
        rows = cur.fetchall()
        results = []
        for row in rows:
            r = dict(zip(columns, row))
            results.append({
                "course_id": r["course_id"],
                "title": r["title"],
                "level": r["level"] or r["audience"] or "beginner",
                "duration_months": int(r["duration_months"]) if r["duration_months"] else 3,
                "preview": f"Existing course: {r['title']} ({r['status']})",
            })
        return results

    def close(self):
        """Close DB connection"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


# Usage example:
# repo = PostgresRepository(dbname="ai_gen_db", user="postgres", password="password")
# repo.init_schema()

