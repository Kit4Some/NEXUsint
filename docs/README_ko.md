<p align="center">
  <h1 align="center">NEXUS</h1>
  <p align="center"><strong>Network EXploration & Unified Synthesis</strong></p>
  <p align="center">Multi-INT Fusion OSINT Platform</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/Electron-33-47848f?logo=electron&logoColor=white" alt="Electron">
  <img src="https://img.shields.io/badge/Neo4j-5.x-008CC1?logo=neo4j&logoColor=white" alt="Neo4j">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

<p align="center">
  <a href="../README.md">English</a> &nbsp;|&nbsp;
  <a href="README_ko.md"><strong>한국어</strong></a> &nbsp;|&nbsp;
  <a href="README_zh.md">中文</a> &nbsp;|&nbsp;
  <a href="README_ja.md">日本語</a>
</p>

---

**NEXUS**는 전문가급 Multi-INT(다중 정보) 융합 OSINT(공개출처정보) 플랫폼입니다. **CYBINT**, **SOCMINT**, **SIGINT**, **GEOINT** 수집, 처리, 분석, 시각화를 지식 그래프 기반의 단일 데스크톱 애플리케이션으로 통합합니다.

<p align="center">
  <img src="../pics/OSINT_2D.png" alt="NEXUS 2D 지도 뷰 — 다중 레이어 오버레이를 통한 글로벌 엔티티 관계 시각화" width="100%">
  <br>
  <em>2D 지도 뷰 — Deck.gl 다중 레이어 렌더링을 통한 글로벌 엔티티 네트워크 시각화</em>
</p>

<p align="center">
  <img src="../pics/OSINT_3D.png" alt="NEXUS 3D 글로브 뷰 — CesiumJS 글로브에서의 엔티티 검사 및 연결 분석" width="100%">
  <br>
  <em>3D 글로브 뷰 — 실시간 연결 분석이 포함된 엔티티 검사</em>
</p>

<p align="center">
  <img src="../pics/OSINT_3D_Find.png" alt="NEXUS AI 분석관 — RAG 채팅 인터페이스를 통한 AI 기반 지식 그래프 분석" width="100%">
  <br>
  <em>AI 분석관 — RAG 기반 지식 그래프 쿼리 및 정보 분석</em>
</p>

---

## 개요

NEXUS는 다중 소스 정보 데이터를 수집, 상관 분석 및 시각화해야 하는 정보 분석관, 보안 연구원, 조사팀을 위해 설계되었습니다. 다양한 데이터 소스에서 자동으로 지식 그래프를 구축하고, 그래프 알고리즘을 통해 숨겨진 관계를 식별하며, 2D/3D 지리공간 시각화와 AI 지원 분석을 제공합니다.

### NEXUS의 주요 기능

- **수집**: 4개 INT 분야에 걸쳐 15개 이상의 OSINT 소스에서 정보 수집
- **정규화**: 원시 데이터를 통합 POLE(인물-객체-위치-이벤트) 온톨로지로 변환
- **상관분석**: 그래프 알고리즘(커뮤니티 감지, 중심성 분석, 경로 탐색)을 통한 엔티티 상관관계 분석
- **시각화**: 인터랙티브 2D 지도(Deck.gl) 및 3D 글로브(CesiumJS)에서의 관계 시각화
- **분석**: AI 기반 RAG 채팅 엔진을 통한 자연어 데이터 쿼리
- **감시**: 자동화된 감시 목록 및 실시간 알림을 통한 타겟 모니터링
- **내보내기**: PDF, HTML, JSON, STIX 2.1 형식의 정보 산출물 생성

---

## 주요 기능

### 정보 수집 (Multi-INT)

| 분야 | 기능 | 소스 |
|:---:|---|---|
| **CYBINT** | IP/도메인 정찰, 위협 정보, 취약점 분석 | Shodan, VirusTotal, AbuseIPDB, OTX, SecurityTrails, CT |
| **SOCMINT** | 소셜 미디어 계정 분석, 네트워크 매핑 | Twitter/X API, 플랫폼별 수집기 |
| **SIGINT** | 항공기 추적(ADS-B), 선박 모니터링(AIS), RF 신호 분석 | OpenSky Network, ADS-B Exchange, AIS 피드 |
| **GEOINT** | 지리공간 정보, 위성 이미지, 지형 분석 | Mapbox, OpenStreetMap, CesiumJS 지형 제공자 |

### 지식 그래프 (POLE 스키마)

- **24개 엔티티 유형**: Person, Organization, IPAddress, Domain, Certificate, ThreatActor, Malware, Vulnerability, Vessel, Aircraft, SocialAccount, Location, Event 등
- **20개 관계 유형**: `RESOLVES_TO`, `HOSTS`, `ATTRIBUTED_TO`, `LOCATED_AT`, `TARGETS`, `COMMUNICATES_WITH` 등
- **메타데이터 풍부한 엣지**: 모든 관계에 신뢰도 점수, 소스 INT 유형, 타임스탬프, 수집 방법 포함
- **그래프 알고리즘**: Neo4j GDS를 통한 Louvain 커뮤니티 감지, 매개 중심성/PageRank, 최단 경로 분석

### 시각화

- **2D 지도**: Deck.gl + MapLibre GL JS — 아크, 산점도, 히트맵, 등고선, GeoJSON, 지형 레이어
- **3D 글로브**: CesiumJS — 엔티티 배치 및 비행/선박 궤적 재생이 포함된 3D 글로브
- **그래프 뷰**: Sigma.js(graphology) — 커뮤니티 기반 색상 분류가 포함된 엔티티 관계 그래프
- **대시보드**: Recharts 기반 실시간 분석 — 수집 통계, 엔티티 분포, 시간적 분석
- **타임라인**: 엔티티 필터링이 포함된 시간 순서 이벤트 재생

### AI 분석관

- 의도 분류가 포함된 RAG(검색 증강 생성) 채팅 엔진
- 근거 있는 응답을 위한 Neo4j + PostgreSQL 컨텍스트 검색
- 지식 그래프의 자연어 쿼리
- 자동화된 엔티티 경로 분석 및 관계 요약

### 정보 등급 (NATO Admiralty System)

- **신뢰성** (A–F): 소스 유형 및 과거 정확도 기반 소스 신뢰도
- **확실성** (1–6): 교차 소스 확증, 일관성, 최신성 기반 정보 확실도

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          프레젠테이션 레이어                               │
│         Electron 33 + React 19 + TailwindCSS 4 + Zustand              │
│    ┌──────────┬──────────┬───────────┬───────────┬──────────┐          │
│    │  2D 지도  │ 3D 글로브 │   그래프   │  대시보드  │ 타임라인  │          │
│    │ Deck.gl  │ CesiumJS │ Sigma.js  │ Recharts  │          │          │
│    └──────────┴──────────┴───────────┴───────────┴──────────┘          │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ REST / WebSocket / GraphQL
┌────────────────────────────┴────────────────────────────────────────────┐
│                          API 게이트웨이                                  │
│              FastAPI + Socket.IO + Strawberry GraphQL                   │
│         JWT 인증 │ 속도 제한 │ 감사 로깅 │ Prometheus                     │
└──────┬─────────┬──────────┬──────────┬──────────┬──────────────────────┘
       │         │          │          │          │
┌──────┴──┐ ┌────┴───┐ ┌───┴────┐ ┌───┴───┐ ┌───┴────┐
│  Neo4j  │ │  PgSQL │ │ Redis  │ │  ES   │ │ Kafka  │
│  (KG)   │ │ 17     │ │  7.x   │ │ 8.x   │ │  3.7   │
└─────────┘ └────────┘ └────────┘ └───────┘ └────────┘
```

---

## 기술 스택

| 레이어 | 기술 |
|:---:|---|
| **프론트엔드** | Electron 33, React 19, TypeScript 5.7, TailwindCSS 4, Zustand, TanStack Query v5 |
| **시각화** | Deck.gl v9 + MapLibre GL JS (2D), CesiumJS (3D), Sigma.js (그래프), Recharts |
| **백엔드** | Python 3.12, FastAPI, Strawberry GraphQL, Socket.IO, Celery, Pydantic v2 |
| **지식 그래프** | Neo4j 5.x + GDS + APOC + n10s |
| **데이터베이스** | PostgreSQL 17 (pgvector + TimescaleDB), Elasticsearch 8.x, Redis 7.x |
| **메시징** | Apache Kafka 3.7 |
| **스토리지** | MinIO (S3 호환 오브젝트 스토리지) |
| **모니터링** | Prometheus + Grafana |
| **빌드** | Turborepo, pnpm 9 (프론트엔드), uv (백엔드) |

---

## 빠른 시작

### 사전 요구 사항

| 도구 | 버전 | 용도 |
|------|------|------|
| Node.js | 20+ | 프론트엔드 런타임 |
| pnpm | 9+ | 프론트엔드 패키지 관리자 |
| Python | 3.12+ | 백엔드 런타임 |
| uv | 최신 | Python 패키지 관리자 |
| Docker | 24+ | 인프라 서비스 |
| Docker Compose | v2+ | 서비스 오케스트레이션 |

### 1. 클론 및 설정

```bash
git clone https://github.com/your-org/nexus-msint.git
cd nexus-msint
cp .env.example .env
# .env 파일에 API 키를 설정하세요
```

### 2. 인프라 시작

```bash
cd infra
docker compose up -d
```

### 3. 백엔드 시작

```bash
cd apps/api
uv pip install --system .
uvicorn nexus.main:sio_asgi_app --reload --host 0.0.0.0 --port 8000
```

### 4. 프론트엔드 시작

```bash
cd apps/desktop
pnpm install
pnpm dev
```

### 5. 테스트 실행

```bash
cd apps/api
JWT_SECRET=test-secret pytest
```

---

## 기여

커뮤니티의 기여를 환영합니다! 자세한 내용은 [기여 가이드](../CONTRIBUTING.md)를 참조해 주세요.

## 라이선스

이 프로젝트는 **MIT 라이선스**에 따라 라이선스가 부여됩니다 — 자세한 내용은 [LICENSE](../LICENSE) 파일을 참조하세요.

---

<p align="center">
  <strong>NEXUS</strong> — 다중 소스 정보를 실행 가능한 인사이트로 통합합니다.
</p>
