-- NEXUS OSINT Platform — PostgreSQL Initialization

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Users table (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Investigations table
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    target_ints TEXT[] NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    progress SMALLINT NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    entity_count INTEGER NOT NULL DEFAULT 0,
    relationship_count INTEGER NOT NULL DEFAULT 0,
    report JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Collection jobs table
CREATE TABLE IF NOT EXISTS collection_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    int_type VARCHAR(20) NOT NULL,
    query TEXT NOT NULL,
    scan_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    progress SMALLINT NOT NULL DEFAULT 0,
    result_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    investigation_id UUID REFERENCES investigations(id),
    parent_job_id UUID REFERENCES collection_jobs(id),
    pivot_depth SMALLINT NOT NULL DEFAULT 0,
    pivot_entity_type VARCHAR(50),
    auto_pivot BOOLEAN NOT NULL DEFAULT FALSE,
    entity_ids TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Entity embeddings for vector search
CREATE TABLE IF NOT EXISTS entity_embeddings (
    entity_id VARCHAR(255) PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_name TEXT NOT NULL,
    embedding vector(1536),
    source_int VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create vector index
CREATE INDEX IF NOT EXISTS idx_entity_embedding
ON entity_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Intelligence events (time-series)
CREATE TABLE IF NOT EXISTS intelligence_events (
    id UUID DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    entity_id VARCHAR(255),
    source_int VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('intelligence_events', 'timestamp', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_status ON collection_jobs(status);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_investigation ON collection_jobs(investigation_id);
CREATE INDEX IF NOT EXISTS idx_events_entity ON intelligence_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON intelligence_events(event_type);

-- Pivot chain index
CREATE INDEX IF NOT EXISTS idx_collection_jobs_parent ON collection_jobs(parent_job_id);

-- Watch targets for persistent monitoring
CREATE TABLE IF NOT EXISTS watch_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR(255),
    entity_name TEXT NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    int_type VARCHAR(20) NOT NULL,
    scan_type VARCHAR(50) NOT NULL,
    query TEXT NOT NULL,
    interval_hours INTEGER NOT NULL DEFAULT 24 CHECK (interval_hours >= 1),
    auto_pivot BOOLEAN NOT NULL DEFAULT FALSE,
    last_collected_at TIMESTAMPTZ,
    next_collection_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_watch_targets_next ON watch_targets(next_collection_at) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_watch_targets_entity ON watch_targets(entity_id);

-- Persistent alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR(255),
    entity_name TEXT,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium'
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    title TEXT NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    source_job_id UUID REFERENCES collection_jobs(id),
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alerts(entity_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_unacked ON alerts(acknowledged) WHERE acknowledged = FALSE;
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);

-- Alert rules
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL
        CHECK (rule_type IN ('new_entity', 'high_risk', 'entity_change', 'pivot_depth', 'anomaly')),
    conditions JSONB NOT NULL DEFAULT '{}',
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit log for request tracking
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,
    user_id UUID REFERENCES users(id),
    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    status_code SMALLINT NOT NULL,
    duration_ms NUMERIC(10,2) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_path ON audit_log(path);

-- Insert default admin user (password: admin — change immediately)
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@nexus.local', '$2b$12$q6Xp9hExsUk8CIo/rbLoi.3BaCOrFm5QWNMmfPK7CjbqqQ0h3TS/q', 'admin')
ON CONFLICT (username) DO NOTHING;
