-- Role permissions table for RBAC enforcement
-- Defines what each role (admin, analyst, viewer) can do

CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(role, resource, action)
);

-- Admin: full access
INSERT INTO role_permissions (role, resource, action) VALUES
    ('admin', 'entities', 'read'),
    ('admin', 'entities', 'create'),
    ('admin', 'entities', 'update'),
    ('admin', 'entities', 'delete'),
    ('admin', 'entities', 'resolve'),
    ('admin', 'investigations', 'read'),
    ('admin', 'investigations', 'create'),
    ('admin', 'investigations', 'execute'),
    ('admin', 'investigations', 'delete'),
    ('admin', 'collections', 'read'),
    ('admin', 'collections', 'create'),
    ('admin', 'analytics', 'read'),
    ('admin', 'analytics', 'execute'),
    ('admin', 'stix', 'export'),
    ('admin', 'stix', 'import'),
    ('admin', 'search', 'read'),
    ('admin', 'search', 'reindex'),
    ('admin', 'users', 'manage'),
    ('admin', 'dashboard', 'read')
ON CONFLICT (role, resource, action) DO NOTHING;

-- Analyst: create/modify entities and investigations, run collections
INSERT INTO role_permissions (role, resource, action) VALUES
    ('analyst', 'entities', 'read'),
    ('analyst', 'entities', 'create'),
    ('analyst', 'entities', 'update'),
    ('analyst', 'entities', 'resolve'),
    ('analyst', 'investigations', 'read'),
    ('analyst', 'investigations', 'create'),
    ('analyst', 'investigations', 'execute'),
    ('analyst', 'collections', 'read'),
    ('analyst', 'collections', 'create'),
    ('analyst', 'analytics', 'read'),
    ('analyst', 'analytics', 'execute'),
    ('analyst', 'stix', 'export'),
    ('analyst', 'stix', 'import'),
    ('analyst', 'search', 'read'),
    ('analyst', 'dashboard', 'read')
ON CONFLICT (role, resource, action) DO NOTHING;

-- Viewer: read-only access
INSERT INTO role_permissions (role, resource, action) VALUES
    ('viewer', 'entities', 'read'),
    ('viewer', 'investigations', 'read'),
    ('viewer', 'collections', 'read'),
    ('viewer', 'analytics', 'read'),
    ('viewer', 'stix', 'export'),
    ('viewer', 'search', 'read'),
    ('viewer', 'dashboard', 'read')
ON CONFLICT (role, resource, action) DO NOTHING;
