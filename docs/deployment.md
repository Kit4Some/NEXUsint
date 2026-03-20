# NEXUS OSINT Platform — Deployment Guide

## Prerequisites

- Docker & Docker Compose v2
- Python 3.12+
- Node.js 20+
- pnpm 9+

## Quick Start (Development)

```bash
# 1. Start infrastructure
cd infra && docker compose up -d

# 2. Start API
cd apps/api
cp .env.example .env  # Configure API keys
uv sync && uv run uvicorn nexus.main:sio_asgi_app --reload --host 0.0.0.0

# 3. Start desktop app
cd apps/desktop
pnpm install && pnpm dev
```

## Production Deployment

### Environment Variables

All required environment variables must be set. See `.env.production.example` for the full list.

**Critical secrets (must be changed from defaults):**

| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | JWT signing key — use `openssl rand -hex 32` to generate |
| `NEO4J_PASSWORD` | Neo4j database password |
| `POSTGRES_PASSWORD` | PostgreSQL database password |
| `MINIO_SECRET_KEY` | MinIO object storage secret |

### Security Checklist

- [ ] JWT_SECRET set to a strong random value (min 32 characters)
- [ ] All database passwords changed from defaults
- [ ] CORS_ORIGINS restricted to your domain
- [ ] NEXUS_ENV=production set (enables config validation)
- [ ] TLS/HTTPS configured via reverse proxy (nginx, Caddy, etc.)
- [ ] Rate limiting configured appropriately for your traffic
- [ ] Audit logging enabled (AUDIT_LOG_ENABLED=true)
- [ ] Grafana admin password changed

### Infrastructure

```bash
# Production with monitoring
cd infra && docker compose up -d

# Verify services
docker compose ps
curl http://localhost:8000/health
curl http://localhost:9090/-/healthy   # Prometheus
curl http://localhost:3001/api/health  # Grafana
```

### Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin — change on first login)
  - Pre-provisioned dashboards: "NEXUS OSINT — Overview" and "NEXUS OSINT — Performance"

### Desktop App

Build for your platform:

```bash
cd apps/desktop
pnpm build           # Build for current platform
```

Auto-update is configured via GitHub Releases. Tag a release (`v0.2.0`) to trigger the release workflow.

## Scaling Considerations

- **Neo4j**: Increase heap/pagecache for large graphs (>100K entities)
- **PostgreSQL**: Increase max_connections and shared_buffers
- **Redis**: Default 256MB LRU cache — increase for high-traffic deployments
- **Kafka**: Add partitions for higher throughput on collection topics
