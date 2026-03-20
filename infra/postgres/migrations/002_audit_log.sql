-- Audit log table for request tracking and compliance
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    request_id  UUID NOT NULL,
    user_id     UUID,
    method      VARCHAR(10) NOT NULL,
    path        VARCHAR(500) NOT NULL,
    status_code SMALLINT NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    ip_address  VARCHAR(45),
    user_agent  TEXT DEFAULT '',
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable('audit_log', 'timestamp', if_not_exists => TRUE);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_log_path ON audit_log (path, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_status ON audit_log (status_code) WHERE status_code >= 400;

-- Retention policy: keep audit logs for 90 days
SELECT add_retention_policy('audit_log', INTERVAL '90 days', if_not_exists => TRUE);
