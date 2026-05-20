import os
from .postgres_orm_repo import PostgresORMRepository
from psycopg2 import pool
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from Domain.course import Chapter

class PostgresRepository(PostgresORMRepository):
    def __init__(self, dbname: str, user: str, password: str, host: str = "localhost", port: int = 5432):
        # Sync environment variables so the parent ORM repository uses the same connection parameters
        os.environ['POSTGRES_DBNAME'] = dbname
        os.environ['POSTGRES_USER'] = user
        os.environ['POSTGRES_PASSWORD'] = password
        os.environ['POSTGRES_HOST'] = host
        os.environ['POSTGRES_PORT'] = str(port)
        
        super().__init__()
        
        self.conn_params = {
            'dbname': dbname,
            'user': user,
            'password': password,
            'host': host,
            'port': port
        }
        # Initialize a thread-safe connection pool
        self.pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,  # Allows up to 20 parallel agent operations
            **self.conn_params
        )

    @contextmanager
    def get_cursor(self):
        """Context manager to get a connection from the pool and return it."""
        conn = self.pool.getconn()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.putconn(conn)

    def init_schema(self) -> None:
        """Initialize the full PostgreSQL schema with all tables and indexes matching models.py."""
        schema_sql = """
-- Complete schema from models.py
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    course_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    audience VARCHAR(255),
    created_by INT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS chapters (
    chapter_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    chapter_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft',
    UNIQUE(course_id, chapter_order)
);

CREATE TABLE IF NOT EXISTS syllabus (
    syllabus_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS runs (
    run_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS run_agents (
    run_agent_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS logs (
    log_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    agent_name VARCHAR(255),
    message TEXT NOT NULL,
    level VARCHAR(50) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    chapter_id INT REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    approver_id INT REFERENCES users(user_id),
    status VARCHAR(50) DEFAULT 'pending',
    comments TEXT,
    approved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    chapter_id INT REFERENCES chapters(chapter_id) ON DELETE CASCADE NOT NULL,
    reviewer_id INT REFERENCES users(user_id) NOT NULL,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    agent_name VARCHAR(255),
    metric_name VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS costs (
    cost_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    agent_name VARCHAR(255),
    cost_type VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    artifact_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exports (
    export_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE NOT NULL,
    artifact_id INT REFERENCES artifacts(artifact_id) ON DELETE CASCADE NOT NULL,
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Performance indexes matching models
CREATE INDEX IF NOT EXISTS idx_courses_created_by ON courses(created_by);
CREATE INDEX IF NOT EXISTS idx_courses_status ON courses(status);
CREATE INDEX IF NOT EXISTS idx_chapters_course_id ON chapters(course_id);
CREATE INDEX IF NOT EXISTS idx_chapters_order ON chapters(chapter_order);
CREATE INDEX IF NOT EXISTS idx_runs_course_id ON runs(course_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_logs_run_id ON logs(run_id);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_approvals_run_id ON approvals(run_id);
CREATE INDEX IF NOT EXISTS idx_approvals_chapter_id ON approvals(chapter_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_agent_name ON metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);

-- Partition logs table by date for scalability (optional)
    -- Some existing DBs (including some test DBs) may have a non-partitioned `logs` table.
    -- Attempting to attach a partition then fails with: "logs" is not partitioned.
    --
    -- The app works fine without partitions; streaming reads from the base `logs` table.
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_partitioned_table pt ON pt.partrelid = c.oid
            WHERE c.relname = 'logs'
        ) THEN
            CREATE TABLE IF NOT EXISTS logs_daily PARTITION OF logs
              FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
        END IF;
        ALTER TABLE logs SET (autovacuum_enabled = true);
    END $$;
        """
        with self.get_cursor() as cur:
            cur.execute(schema_sql)
            print("✅ Full Postgres schema initialized")

    def create_course(self, title: str, audience: str, description: Optional[str] = None, created_by: Optional[int] = None) -> int:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO courses (title, description, audience, created_by) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (title) DO UPDATE SET updated_at = CURRENT_TIMESTAMP RETURNING course_id
                """,
                (title, description, audience, created_by)
            )
            return cur.fetchone()[0]

    def get_chapters(self, course_id: int) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
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

    def get_chapters_for_course(self, course_id: int) -> List[Dict[str, Any]]:
        return self.get_chapters(course_id)

    def create_course_from_template(self, template: Dict[str, Any]) -> int:
        """Insert a course from a CourseTemplate dict, store chapters as draft rows."""
        import json
        status = template.get('status', 'draft')
        with self.get_cursor() as cur:
            # Ensure ON CONFLICT uses a matching UNIQUE constraint.
            # The schema defines `courses.title` as UNIQUE, so this upsert is valid.
            cur.execute(
                """
INSERT INTO courses (title, description, audience, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (title) DO UPDATE SET
                    description = EXCLUDED.description,
                    audience = EXCLUDED.audience,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING course_id
                """,
                (template['title'], str(template.get('learning_objectives', [])), template.get('level', 'general'), status)
            )
            course_id = cur.fetchone()[0]
            for i, ch in enumerate(template.get('chapters', [])):
                title = ch['title'] if isinstance(ch, dict) else str(ch)
                # Only safe to use ON CONFLICT if a unique constraint exists on (course_id, chapter_order).
                # If schema migrations haven't created it, this statement will fail.
                cur.execute(
                    """
INSERT INTO chapters (course_id, title, content, chapter_order, status)
VALUES (%s, %s, %s, %s, 'draft')
ON CONFLICT DO NOTHING
""",
                    (course_id, title, '', i + 1)
                )
            cur.execute(
                "INSERT INTO syllabus (course_id, content, status) VALUES (%s, %s, 'draft')",
                (course_id, json.dumps(template))
            )
            return course_id

    def create_run(self, course_id: int, workflow_name: str) -> int:
        """Create a new run record for tracking progress."""
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO runs (course_id, workflow_name, status) VALUES (%s, %s, 'running') RETURNING run_id",
                (course_id, workflow_name)
            )
            return cur.fetchone()[0]

    def update_course_template(self, course_id: int, template: Dict[str, Any]) -> None:
        """Update the course syllabus and sync the chapters table with the generated outline."""
        import json
        with self.get_cursor() as cur:
            # 1. Update the structured syllabus
            cur.execute(
                "UPDATE syllabus SET content = %s, updated_at = CURRENT_TIMESTAMP WHERE course_id = %s",
                (json.dumps(template), course_id)
            )
            # 2. Sync chapters table (delete old draft placeholders and insert new ones)
            cur.execute("DELETE FROM chapters WHERE course_id = %s AND status = 'draft'", (course_id,))
            for i, ch in enumerate(template.get('chapters', [])):
                # Accept multiple template chapter schemas:
                #   1) ["Intro", "Setup"]
                #   2) [{"title": "Intro"}, {"title": "Setup"}]
                #   3) [{"title": "Intro", "content": "..."}, ...]
                if isinstance(ch, dict):
                    chapter_title = ch.get('title', '')
                else:
                    chapter_title = str(ch)
                cur.execute(
                    """
                    INSERT INTO chapters (course_id, title, content, chapter_order, status)
                    VALUES (%s, %s, %s, %s, 'draft')
                    """,
                    (course_id, chapter_title, '', i + 1)
                )

    def update_run_status(self, run_id: int, status: str) -> None:
        with self.get_cursor() as cur:
            cur.execute("UPDATE runs SET status = %s, completed_at = CASE WHEN %s IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE completed_at END WHERE run_id = %s", (status, status, run_id))

    def get_course_status(self, course_id: int) -> Dict[str, Any]:
        with self.get_cursor() as cur:
            cur.execute("SELECT course_id, title, status, created_at, updated_at FROM courses WHERE course_id = %s", (course_id,))
            row = cur.fetchone()
            if not row:
                return {'error': 'Course not found', 'course_id': course_id}
            return dict(zip(['course_id', 'title', 'status', 'created_at', 'updated_at'], row))

    def get_course_review(self, course_id: int) -> Dict[str, Any]:
        import json
        with self.get_cursor() as cur:
            cur.execute("SELECT course_id, title, status, created_at, updated_at FROM courses WHERE course_id = %s", (course_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Course {course_id} not found")
            course = dict(zip(['course_id', 'title', 'status', 'created_at', 'updated_at'], row))
            cur.execute("SELECT content FROM syllabus WHERE course_id = %s ORDER BY syllabus_id DESC LIMIT 1", (course_id,))
            syl_row = cur.fetchone()
            template = syl_row[0] if syl_row else {}
            chapters = self.get_chapters(course_id)
            return {
                'course_id': course_id,
                'course': course,
                'template': template,
                'metadata': {'chapters_count': len(chapters)},
                'chapters': chapters
            }

    def create_approval(self, course_id: int, approved: bool, comments: Optional[str] = None) -> int:
        """Create an approval record linked to the latest run for this course."""
        with self.get_cursor() as cur:
            cur.execute("SELECT run_id FROM runs WHERE course_id = %s ORDER BY run_id DESC LIMIT 1", (course_id,))
            row = cur.fetchone()
            if row:
                run_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO runs (course_id, workflow_name, status) VALUES (%s, 'approval', 'running') RETURNING run_id",
                    (course_id,)
                )
                run_id = cur.fetchone()[0]
            status = 'approved' if approved else 'rejected'
            cur.execute(
                "INSERT INTO approvals (run_id, status, comments) VALUES (%s, %s, %s) RETURNING approval_id",
                (run_id, status, comments)
            )
            return cur.fetchone()[0]

    def update_course_status(self, course_id: int, status: str) -> None:
        with self.get_cursor() as cur:
            cur.execute("UPDATE courses SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE course_id = %s", (status, course_id))

    def get_latest_error(self, course_id: int) -> Optional[str]:
        """Retrieve the most recent error message for a course."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT l.message FROM logs l 
                JOIN runs r ON l.run_id = r.run_id 
                WHERE r.course_id = %s AND l.level = 'error' 
                ORDER BY l.created_at DESC LIMIT 1
            """, (course_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def log_message(self, run_id: int, agent_name: str, message: str, level: str = 'info') -> None:
        if not run_id or run_id <= 0:
            return
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO logs (run_id, agent_name, message, level) VALUES (%s, %s, %s, %s)",
                (run_id, agent_name, message, level)
            )

    def log_run(self, run_id: int, agent_name: str, message: str, level: str = 'info') -> None:
        """Alias for log_message."""
        self.log_message(run_id, agent_name, message, level)

    def get_logs_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT log_id, agent_name, message, level, created_at FROM logs WHERE run_id = %s ORDER BY log_id",
                (run_id,)
            )
            columns = ["log_id", "agent_name", "message", "level", "created_at"]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def search_courses(self, query: str) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT course_id, title, status FROM courses WHERE title ILIKE %s ORDER BY course_id",
                (f"%{query}%",)
            )
            columns = ["course_id", "title", "status"]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_metrics_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT metric_id, agent_name, metric_name, value, created_at FROM metrics WHERE run_id = %s ORDER BY metric_id",
                (run_id,)
            )
            columns = ["metric_id", "agent_name", "metric_name", "value", "created_at"]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def log_metric(self, run_id: int, metric_name: str, value: float, agent_name: Optional[str] = None) -> None:
        """Log a single metric value to the metrics table."""
        if not run_id or run_id <= 0:
            return
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO metrics (run_id, agent_name, metric_name, value) VALUES (%s, %s, %s, %s)",
                (run_id, agent_name, metric_name, value)
            )

    def save_full_course_chapters(self, course_id: int, chapters: List) -> None:
        """Save full generated chapters from workflow to chapters table"""
        with self.get_cursor() as cur:
            # Clear previous generated chapters
            cur.execute("DELETE FROM chapters WHERE course_id = %s AND status = 'generated'", (course_id,))
            for i, ch_dict in enumerate(chapters):
                cur.execute(
                    """
                    INSERT INTO chapters (course_id, title, content, chapter_order, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (course_id, ch_dict['title'], ch_dict['content'], i+1, 'generated')
                )
            print(f"✅ Saved {len(chapters)} chapters for course {course_id}")

    def get_logs_after(self, run_id: int, last_log_id: int = 0) -> List[Dict[str, Any]]:
        """Get logs for a run after a specific log_id for incremental streaming."""
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT log_id, agent_name, message, level 
                FROM logs 
                WHERE run_id = %s AND log_id > %s 
                ORDER BY log_id
                """,
                (run_id, last_log_id)
            )
            columns = ["log_id", "agent_name", "message", "level"]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions from the database. Returns count of deleted rows."""
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP")
            return cur.rowcount


    def close(self):
        """Close the database connection."""
        super().close()
        if self.pool:
            self.pool.closeall()
