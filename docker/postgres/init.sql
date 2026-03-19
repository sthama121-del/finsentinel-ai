-- FinSentinel AI - PostgreSQL Init
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create Airflow database
CREATE DATABASE airflow;

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event VARCHAR(100) NOT NULL,
    task_id UUID,
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    error TEXT,
    retries INT DEFAULT 0,
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    submitted_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON agent_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON agent_tasks(created_at DESC);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(255) NOT NULL,
    risk_score INT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    recommended_action VARCHAR(50) NOT NULL,
    fraud_patterns JSONB DEFAULT '[]',
    reasoning TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_risk_level ON fraud_alerts(risk_level);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON fraud_alerts(resolved);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO users (email, role) VALUES
    ('analyst@finsentinel.com', 'analyst'),
    ('admin@finsentinel.com', 'admin'),
    ('auditor@finsentinel.com', 'auditor')
ON CONFLICT (email) DO NOTHING;

CREATE TABLE IF NOT EXISTS llm_eval_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255),
    provider VARCHAR(50),
    model VARCHAR(100),
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    hallucination_score FLOAT,
    relevance_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
