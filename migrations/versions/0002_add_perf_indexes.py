"""Add performance indexes for high-impact queries

Revision ID: 0002_add_perf_indexes
Revises: 0001_initial_schema
Create Date: Performance optimization
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_add_perf_indexes'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # High-impact indexes for frequent queries (logs/run_id, courses/title/status, chapters/course_id+status)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_run_id_created ON logs (run_id, created_at DESC);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_level ON logs (level);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_courses_title ON courses (title);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_courses_status ON courses (status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chapters_course_status ON chapters (course_id, status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_runs_status ON runs (status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_runs_course_id ON runs (course_id);
    """)
    print("✅ Added performance indexes")

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_logs_run_id_created;
        DROP INDEX IF EXISTS idx_logs_level;
        DROP INDEX IF EXISTS idx_courses_title;
        DROP INDEX IF EXISTS idx_courses_status;
        DROP INDEX IF EXISTS idx_chapters_course_status;
        DROP INDEX IF EXISTS idx_runs_status;
        DROP INDEX IF EXISTS idx_runs_course_id;
    """)

