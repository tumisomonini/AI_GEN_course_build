"""Initial schema from schema.sql

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2024 (manual)

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

depends_on = None

schema_sql = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    level VARCHAR(50),
    duration_months INTEGER,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chapters (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    chapter_order INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL,
    agent_name VARCHAR(100),
    message TEXT,
    level VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chapters_course_id ON chapters(course_id);
CREATE INDEX IF NOT EXISTS idx_chapters_status ON chapters(status);
CREATE INDEX IF NOT EXISTS idx_logs_run_id ON logs(run_id);
"""

def upgrade() -> None:
    op.execute(sa.text(schema_sql))

def downgrade() -> None:
    op.execute(sa.text("""
        DROP TABLE IF EXISTS sessions;
        DROP TABLE IF EXISTS logs;
        DROP TABLE IF EXISTS chapters;
        DROP TABLE IF EXISTS courses;
        DROP TABLE IF EXISTS users;
    """))

