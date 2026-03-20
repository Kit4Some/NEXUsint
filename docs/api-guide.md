# NEXUS OSINT Platform — API Guide

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints except `/auth/login` and `/health` require a Bearer JWT token.

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Response: {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}

# Use token in subsequent requests
curl http://localhost:8000/api/v1/entities?limit=10 \
  -H "Authorization: Bearer eyJ..."

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"

# Logout (revokes token)
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

## Entity Search

```bash
# Search all entities
curl "http://localhost:8000/api/v1/entities?limit=20&offset=0"

# Filter by type and source
curl "http://localhost:8000/api/v1/entities?type=ThreatActor&source_int=CYBINT&min_confidence=0.7"

# Full-text search
curl "http://localhost:8000/api/v1/entities?query=APT-28&limit=10"

# Get entity graph (2-hop neighborhood)
curl "http://localhost:8000/api/v1/entities/{id}/graph?depth=2"

# Get entity timeline
curl "http://localhost:8000/api/v1/entities/{id}/timeline"
```

## Investigations

```bash
# Create investigation
curl -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{"query": "APT-28 infrastructure", "target_ints": ["CYBINT", "SOCMINT"], "priority": "high"}'

# Execute investigation (triggers LangGraph agent pipeline)
curl -X POST http://localhost:8000/api/v1/investigations/{id}/execute

# Check status
curl http://localhost:8000/api/v1/investigations/{id}/status
```

## Collection Jobs

```bash
# CYBINT collection
curl -X POST http://localhost:8000/api/v1/collect/cybint \
  -d '{"query": "example.com", "scan_type": "domain_scan"}'

# SOCMINT collection
curl -X POST http://localhost:8000/api/v1/collect/socmint \
  -d '{"query": "username123", "scan_type": "username_search"}'

# Check job status
curl http://localhost:8000/api/v1/collect/status/{job_id}
```

## Analytics

```bash
# Community detection
curl http://localhost:8000/api/v1/analytics/communities/enhanced

# Anomaly detection
curl "http://localhost:8000/api/v1/analytics/anomalies/advanced?methods=statistical,graph"

# Temporal analysis
curl http://localhost:8000/api/v1/analytics/temporal/{entity_id}
```

## STIX 2.1

```bash
# Export investigation as STIX bundle
curl http://localhost:8000/api/v1/stix/export/investigation/{id}

# Export entity with relationships
curl "http://localhost:8000/api/v1/stix/export/entity/{id}?depth=2"

# Import STIX bundle
curl -X POST http://localhost:8000/api/v1/stix/import \
  -H "Content-Type: application/json" \
  -d @bundle.json

# Validate bundle
curl -X POST http://localhost:8000/api/v1/stix/validate \
  -d @bundle.json
```

## Reports

```bash
# Generate report
curl -X POST "http://localhost:8000/api/v1/reports/generate/{investigation_id}?format=json"

# Preview report (HTML)
curl http://localhost:8000/api/v1/reports/{investigation_id}/preview

# Get report in specific format
curl "http://localhost:8000/api/v1/reports/{investigation_id}?format=pdf"
```

## WebSocket (Socket.IO)

Connect with JWT token for real-time updates:

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000', {
  query: { token: 'eyJ...' }
});

// Subscribe to investigation progress
socket.emit('join_investigation', { investigationId: 'inv-123' });
socket.on('investigation:progress', (data) => console.log(data));

// Subscribe to live map updates
socket.emit('subscribe_live_map', {});
socket.on('entity:new', (entity) => console.log('New entity:', entity));

// Subscribe to alerts
socket.emit('subscribe_alerts', {});
socket.on('alert:received', (alert) => console.log('Alert:', alert));
```

## GraphQL

Available at `http://localhost:8000/graphql` with GraphiQL explorer.

```graphql
query {
  entities(filter: { type: ThreatActor, minConfidence: 0.7, limit: 10 }) {
    id
    name
    type
    confidence
    sourceInt
  }
}
```
