-- PostgreSQL Relational Database Schema for AI_GEN_course_build
-- Execute this to initialize the full schema

-- 1. Core Tables

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- admin, sme, user
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    audience VARCHAR(255),
    created_by INT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'  -- draft, published, archived
);

CREATE TABLE chapters (
    chapter_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    chapter_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'  -- draft, reviewed, approved
);

CREATE TABLE syllabus (
    syllabus_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    content JSONB NOT NULL,  -- Structured syllabus data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft'
);

-- 2. Workflow and Agent Tables

CREATE TABLE runs (
    run_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    workflow_name VARCHAR(255) NOT NULL,  -- e.g., "syllabus_generation"
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'  -- running, completed, failed
);

CREATE TABLE run_agents (
    run_agent_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255) NOT NULL,  -- e.g., "planner_agent"
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'  -- running, completed, failed
);

CREATE TABLE logs (
    log_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    message TEXT NOT NULL,
    level VARCHAR(50) DEFAULT 'info',  -- info, warning, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Approval and Review Tables

CREATE TABLE approvals (
    approval_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    chapter_id INT REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    approver_id INT REFERENCES users(user_id),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected
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

-- 4. Metrics and Performance Tables

CREATE TABLE metrics (
    metric_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    metric_name VARCHAR(255) NOT NULL,  -- e.g., "validation_score"
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE costs (
    cost_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    cost_type VARCHAR(255) NOT NULL,  -- e.g., "llm_tokens"
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Sessions Table (NEW)

CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_sessions_course ON sessions(course_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- 6. Artifact and Export Tables

CREATE TABLE artifacts (
    artifact_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,  -- e.g., "pdf", "docx"
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exports (
    export_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(run_id) ON DELETE CASCADE,
    artifact_id INT REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'  -- pending, completed, failed
);

-- 6. Indexes for Performance

-- Indexes for courses
CREATE INDEX idx_courses_created_by ON courses(created_by);
CREATE INDEX idx_courses_status ON courses(status);

-- Indexes for chapters
CREATE INDEX idx_chapters_course_id ON chapters(course_id);
CREATE INDEX idx_chapters_order ON chapters(chapter_order);

-- Indexes for runs
CREATE INDEX idx_runs_course_id ON runs(course_id);
CREATE INDEX idx_runs_status ON runs(status);

-- Indexes for logs
CREATE INDEX idx_logs_run_id ON logs(run_id);
CREATE INDEX idx_logs_level ON logs(level);

-- Indexes for approvals
CREATE INDEX idx_approvals_run_id ON approvals(run_id);
CREATE INDEX idx_approvals_chapter_id ON approvals(chapter_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- Indexes for metrics
CREATE INDEX idx_metrics_run_id ON metrics(run_id);
CREATE INDEX idx_metrics_agent_name ON metrics(agent_name);

-- Indexes for artifacts
CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);

-- Example Queries

/*
7.1. Get All Chapters for a Course
SELECT chapter_id, title, content, chapter_order, status
FROM chapters
WHERE course_id = 1
ORDER BY chapter_order;
*/

 /*
7.2. Get All Approvals for a Run
SELECT a.approval_id, u.username AS approver, a.status, a.comments, a.approved_at
FROM approvals a
JOIN users u ON a.approver_id = u.user_id
WHERE a.run_id = 1;
*/

 /*
7.3. Get Metrics for a Run
SELECT metric_name, value, created_at
FROM metrics
WHERE run_id = 1
ORDER BY created_at;
*/

 /*
7.4. Get Logs for a Run
SELECT agent_name, message, level, created_at
FROM logs
WHERE run_id = 1
ORDER BY created_at;
*/
