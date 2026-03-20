# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NEXUS is a Multi-INT Fusion OSINT platform. Monorepo with Python backend (FastAPI) and Electron+React desktop frontend, connected via REST/WebSocket/GraphQL to Neo4j, PostgreSQL, Redis, Elasticsearch, Kafka, and MinIO. Includes a real-time live feed engine (23+ OSINT sources) that runs in-process — no Celery worker needed.

## Common Commands

### Infrastructure
```bash
cd infra && docker compose up -d          # Start all services (Neo4j, PostgreSQL, Redis, ES, Kafka, MinIO, Prometheus, Grafana)
cd infra && docker compose logs -f api    # Follow API logs
docker exec nexus-postgres psql -U nexus -d nexus  # Connect to PostgreSQL (DB name is "nexus", NOT "nexus_db")
```

### Backend (apps/api/)
```bash
cd apps/api
uv pip install --system .                 # Install Python dependencies
JWT_SECRET=dev-secret uvicorn nexus.main:sio_asgi_app --reload  # Run dev server (note: sio_asgi_app, not app)
pytest                                    # Run all tests
pytest tests/test_entities.py -v          # Run single test file
pytest -k "test_create_entity"            # Run single test by name
ruff check nexus/                         # Lint
ruff format nexus/                        # Format
pyright                                   # Type check
```

### Frontend (apps/desktop/)
```bash
cd apps/desktop
pnpm install                              # Install JS dependencies
pnpm dev                                  # Vite dev server (port 5173)
pnpm typecheck                            # TypeScript check (tsc --noEmit)
pnpm lint                                 # ESLint
pnpm build                                # Full build: tsc + vite + electron-builder
```

### Monorepo (root)
```bash
pnpm install                              # Install all workspaces
pnpm build                                # Turborepo: build all packages
pnpm lint                                 # Turborepo: lint all packages
pnpm format                               # Prettier: format all files
```

## Architecture

### Two Data Paths

NEXUS has two distinct data paths that must not be confused:

**1. Collection Pipeline (query-based, persistent)**
```
API Request → Celery Task → Collector.collect() → entity_factory.normalized_to_entities()
  → Neo4j (knowledge graph) + PostgreSQL (jobs) + Elasticsearch (index)
  → Redis pub/sub → WebSocket → Frontend
```

**2. Live Feed Pipeline (in-process scheduler, no Celery needed)**
```
main.py lifespan → _run_live_feed_scheduler() → asyncio background task
  → Fast tier (60s): flights, military, satellites
  → Slow tier (300s): news, earthquakes, fires, weather, stocks, GDELT, infrastructure
  → Redis (nexus:live:{key}, TTL 120-600s) → WebSocket push + REST polling → Frontend
  → [selective] Neo4j (tracked aircraft, risk≥6 news, mag≥4 earthquakes only)
```

The live feed scheduler starts automatically when the API server boots — it sets `nexus:live:active` in Redis after 5 seconds and begins collecting. Frontend also polls `GET /api/v1/live/fast` and `/slow` every 15 seconds as fallback.

### Backend Structure (apps/api/nexus/)
- **Entry point**: `main.py` exports `sio_asgi_app` (Socket.IO wrapping FastAPI). Contains `_run_live_feed_scheduler()` — an asyncio background task that replaces Celery Beat for live feed collection.
- **Routes**: `api/routes/` — REST endpoints under `/api/v1`. Each file is a FastAPI router. GraphQL at `/graphql`. Key live feed routes: `/live/fast`, `/live/slow`, `/live/start`, `/live/stop`, `/live/health`. News: `/news/latest`, `/news/feeds`. Radio: `/radio/top`, `/radio/nearest`.
- **WebSocket**: `api/websocket/handlers.py` — Socket.IO event handlers. Redis pub/sub channel `nexus:ws:events` bridges events to WebSocket clients. Room `"live-feed"` for real-time data. All `livefeed:*` events are forwarded via prefix match.
- **Dependencies**: `dependencies.py` — FastAPI `Depends()` injectors for Neo4j, PostgreSQL pool, Redis, etc. IDE shows false "unused import" warnings for these.
- **Collectors**:
  - `collectors/{cybint,socmint,sigint,geoint}/` — Query-based. Each INT type has a `manager.py` with async `collect()`.
  - `collectors/sigint/adsb_live_collector.py` — Multi-source ADS-B (adsb.lol + OpenSky + supplemental). Has gap-fill timeout (10s) and route enrichment timeout (5s) to prevent blocking.
  - `collectors/sigint/military_classifier.py` — Military aircraft + UAV classification.
  - `collectors/osint_feeds/` — Live feed collectors. NOT BaseCollector subclasses. Standalone async functions returning data directly: `news_collector.py`, `earth_observation.py`, `financial.py`, `satellites.py`, `geopolitics.py`, `infrastructure.py`, `radio_intercept.py`, `reference_data.py`.
- **Tasks**: `tasks/live_feed_tasks.py` — `_fast_collect()` and `_slow_collect()` are pure async functions callable from both Celery and the in-process scheduler. `collection_tasks.py` is the query-based pipeline.
- **Knowledge graph**: `knowledge/` — `neo4j_client.py` (driver wrapper), `repository.py` (CRUD), `graph_algorithms.py` (GDS projections, Louvain, centrality).
- **Processing**: `processing/entity_factory.py` — `normalized_to_entities()` for collection results; `live_flight_to_entities()`, `live_news_to_entity()`, `live_earthquake_to_entity()` for selective live → Neo4j persistence. `infer_live_relationships()` creates ORIGINATES_FROM, TERMINATES_AT, OCCURRED_AT edges.
- **Services**: `services/live_store.py` (Redis-backed live data, key pattern `nexus:live:{key}`), `services/chat_engine.py` (RAG chat with Neo4j + Redis live context), `services/plane_alert.py` (VIP aircraft enrichment — data at `apps/api/data/`, path uses `parents[2]`), `services/flight_analytics.py` (trails, GPS jamming, holding patterns), `services/news_feed_config.py` (RSS feed management, config at `apps/api/config/news_feeds.json`).
- **Config**: `config.py` — Pydantic BaseSettings, loaded from `.env`. JWT_SECRET is required (server refuses to start without it).

### Frontend Structure (apps/desktop/)
- **Electron**: `electron/main.ts` — main process, custom titlebar, GPU flags for deck.gl.
- **React app**: `src/` — React 19 with Vite.
- **State**: `stores/` — Zustand stores. `useLiveFeedStore` is the hub for all real-time data (flights, news, earthquakes, fires, stocks, satellites, GDELT, infrastructure). Has `pollLiveData()` that fetches `/live/fast` and `/live/slow` every 15 seconds. `startLiveFeed()` calls `POST /live/start` and starts polling interval.
- **API client**: `services/api.ts` — `request()` helper with JWT auth. API objects: `entities`, `collection`, `monitoring`, `analytics`, `liveFeed`.
- **WebSocket**: `services/websocket.ts` — Socket.IO client. Subscribes to `live-feed` room on connect. Handles `livefeed:flights`, `livefeed:military`, `livefeed:news`, `livefeed:earthquakes`, `livefeed:fires`, `livefeed:stocks`, `livefeed:oil`, `livefeed:jamming`, `livefeed:weather`, `livefeed:satellites`, `livefeed:gdelt`, `livefeed:frontlines`, `livefeed:outages`, `livefeed:status`.
- **Map**: `components/map/` — Deck.gl + MapLibre for 2D, CesiumJS for 3D. Layer files in `layers/`: `FlightLayers.ts`, `EarthObservationLayers.ts`, `SatelliteLayers.ts`, `InfrastructureLayers.ts`. Default visible layers set in `useMapStore.ts`.
- **News**: `components/news/NewsFeedPanel.tsx` (risk-scored display), `NewsFeedConfig.tsx` (RSS feed management). NewsFeedPanel is rendered as overlay in `MapContainer.tsx`.
- **Dashboard widgets**: `components/dashboard/widgets/` — DefenseStocksWidget, OilPricesWidget, SpaceWeatherWidget, LiveFeedStatusWidget, LiveFeedWidget.
- **Auto-start**: `AppShell.tsx` calls `useLiveFeedStore.startLiveFeed()` after WebSocket connects.

### Database Schema
- **Neo4j**: POLE ontology — 24 entity types, 20+ relationship types. Schema in `infra/neo4j/init-schema.cypher`. Includes fulltext index on Event entities for live feed search.
- **PostgreSQL**: Tables in `infra/postgres/init.sql` — users, investigations, collection_jobs, entity_embeddings, watch_targets, alerts, audit_log. TimescaleDB + pgvector.

### Live Feed Data Sources (23+)
- **Fast tier (60s)**: ADS-B flights (adsb.lol 6 regions + OpenSky gap-fill + supplemental), military aircraft, satellites (CelesTrak TLE + SGP4)
- **Slow tier (300s)**: 19 RSS news feeds, USGS earthquakes, NASA FIRMS fires, RainViewer weather, NOAA space weather, yfinance stocks/oil, GDELT geopolitics, DeepStateMap frontlines, IODA internet outages, KiwiSDR receivers, global airports, military bases, datacenters, power plants
- **On-demand**: Broadcastify radio feeds, OpenMHz trunked radio
- **Data files**: `apps/api/data/` — plane_alert_db.json (16K aircraft), tracked_names.json, sat_gp_cache.json, military_bases.json, datacenters_geocoded.json, power_plants.json. `apps/api/config/news_feeds.json`.

## Key Patterns

- **Logging**: structlog everywhere in Python. Never use `print()` or stdlib `logging` directly. On Windows, logger.py forces UTF-8 output to prevent `cp949` codec errors with unicode characters in log messages.
- **Live feed collectors**: NOT BaseCollector subclasses. Standalone async functions (e.g., `fetch_news()`, `fetch_all_flights()`) returning data directly.
- **Plane Alert enrichment**: `enrich_with_plane_alert()` and `enrich_with_tracked_names()` are synchronous — do NOT `await` them.
- **HTTP client**: Use `nexus.utils.http_client.fetch_json()` for external API calls (async, retry + circuit breaker). Never use `requests` directly.
- **Data file paths**: Services in `nexus/services/` use `Path(__file__).resolve().parents[2] / "data"` to reach `apps/api/data/`. `parents[2]` NOT `parents[3]`.
- **ADS-B timeout protection**: `adsb_live_collector.py` wraps gap-fill in `asyncio.wait_for(timeout=10)` and route enrichment in `timeout=5` to prevent blocking when external APIs are slow/down.
- **In-process scheduler**: `main.py` runs `_run_live_feed_scheduler()` as an asyncio background task during lifespan. It auto-activates the live feed flag in Redis after 5 seconds. This eliminates the need for separate Celery workers for live data.
- **REST on-demand fallback**: `GET /live/fast` and `/live/slow` check if Redis is empty + live feed is active, and call collectors directly if needed (for first-request scenarios).
- **Auth**: JWT (python-jose). Token blacklisting via Redis. Electron encrypts tokens via `safeStorage`.
- **Caching**: Redis key pattern `nexus:{domain}:{key}`. Live data: `nexus:live:{data_key}`.
- **Async in Celery**: Celery tasks use `_run_async()` helper (creates event loop per invocation).
- **Metrics**: Prometheus at `/metrics`.

## Environment Setup

Copy `.env.example` to `.env` at root. `JWT_SECRET` is required — server refuses to start without it. All API keys are optional — unconfigured collectors are disabled, live feed works without any keys.

Key env vars:
- `JWT_SECRET` — **Required**. Strong random value (min 32 chars).
- `SHODAN_API_KEY`, `VIRUSTOTAL_API_KEY`, `ABUSEIPDB_API_KEY`, `OTX_API_KEY`, `SECURITYTRAILS_API_KEY` — CYBINT
- `TWITTER_BEARER_TOKEN` — SOCMINT
- `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET` — SIGINT gap-fill (OAuth2)
- `MAPBOX_ACCESS_TOKEN` — GEOINT
- `OPENAI_API_KEY` — AI chat engine

## Testing

Backend tests use mocked Neo4j, PostgreSQL, and Redis (see `tests/conftest.py`). Integration tests in `tests/integration/` require running infrastructure. Always set `JWT_SECRET` env var when running tests.

## Code Style

- **Python**: Ruff (line-length 120, Python 3.12 target). Rules: E, F, I, W, UP, S, B.
- **TypeScript**: ESLint + Prettier (singleQuote, printWidth 100, trailingComma all). Underscore-prefixed unused vars are allowed.
- **Path aliases**: `@/` maps to `src/` in frontend TypeScript.
