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
  <a href="README_ko.md">한국어</a> &nbsp;|&nbsp;
  <a href="README_zh.md"><strong>中文</strong></a> &nbsp;|&nbsp;
  <a href="README_ja.md">日本語</a>
</p>

---

**NEXUS** 是一款专业级 Multi-INT（多源情报）融合 OSINT（开源情报）平台。它将 **CYBINT**、**SOCMINT**、**SIGINT** 和 **GEOINT** 的收集、处理、分析和可视化整合到一个基于知识图谱的桌面应用程序中。

<p align="center">
  <img src="../pics/OSINT_2D.png" alt="NEXUS 2D 地图视图 — 通过多图层叠加实现全球实体关系可视化" width="100%">
  <br>
  <em>2D 地图视图 — 基于 Deck.gl 多图层渲染的全球实体网络可视化</em>
</p>

<p align="center">
  <img src="../pics/OSINT_3D.png" alt="NEXUS 3D 地球视图 — 在 CesiumJS 地球上进行实体检查和连接分析" width="100%">
  <br>
  <em>3D 地球视图 — 包含实时连接分析的实体检查</em>
</p>

<p align="center">
  <img src="../pics/OSINT_3D_Find.png" alt="NEXUS AI 分析师 — 基于 RAG 聊天界面的 AI 驱动知识图谱分析" width="100%">
  <br>
  <em>AI 分析师 — 基于 RAG 的知识图谱查询和情报分析</em>
</p>

---

## 概述

NEXUS 专为需要收集、关联和可视化多源情报数据的情报分析师、安全研究人员和调查团队而设计。平台自动从不同数据源构建知识图谱，通过图算法识别隐藏关系，并提供 2D/3D 地理空间可视化和 AI 辅助分析。

### NEXUS 的核心功能

- **收集**：从四个 INT 学科的 15+ OSINT 来源收集情报
- **标准化**：将原始数据转换为统一的 POLE（人物-对象-位置-事件）本体
- **关联分析**：通过图算法（社区检测、中心性分析、路径查找）关联实体
- **可视化**：在交互式 2D 地图（Deck.gl）和 3D 地球（CesiumJS）上展示关系
- **分析**：通过 AI 驱动的 RAG 聊天引擎进行自然语言数据查询
- **监控**：通过自动化监视列表和实时警报进行目标监控
- **导出**：生成 PDF、HTML、JSON 和 STIX 2.1 格式的情报产品

---

## 主要功能

### 情报收集 (Multi-INT)

| 学科 | 能力 | 来源 |
|:---:|---|---|
| **CYBINT** | IP/域名侦察、威胁情报、漏洞分析 | Shodan, VirusTotal, AbuseIPDB, OTX, SecurityTrails, CT |
| **SOCMINT** | 社交媒体账户分析、网络映射 | Twitter/X API, 平台特定收集器 |
| **SIGINT** | 飞机追踪(ADS-B)、船舶监控(AIS)、射频信号分析 | OpenSky Network, ADS-B Exchange, AIS 数据源 |
| **GEOINT** | 地理空间情报、卫星图像、地形分析 | Mapbox, OpenStreetMap, CesiumJS 地形提供商 |

### 知识图谱 (POLE 模式)

- **24 种实体类型**：Person, Organization, IPAddress, Domain, Certificate, ThreatActor, Malware, Vulnerability, Vessel, Aircraft, SocialAccount, Location, Event 等
- **20 种关系类型**：`RESOLVES_TO`, `HOSTS`, `ATTRIBUTED_TO`, `LOCATED_AT`, `TARGETS`, `COMMUNICATES_WITH` 等
- **元数据丰富的边**：每条关系都包含置信度评分、来源 INT 类型、时间戳和收集方法
- **图算法**：通过 Neo4j GDS 实现 Louvain 社区检测、介数/PageRank 中心性、最短路径分析

### 可视化

- **2D 地图**：Deck.gl + MapLibre GL JS — 弧线、散点图、热力图、等高线、GeoJSON、地形图层
- **3D 地球**：CesiumJS — 包含实体放置和飞行/船舶轨迹回放的 3D 地球
- **图视图**：Sigma.js (graphology) — 基于社区着色的交互式实体关系图
- **仪表板**：基于 Recharts 的实时分析 — 收集统计、实体分布、时序分析
- **时间线**：包含实体过滤的时间顺序事件回放

### AI 分析师

- 包含意图分类的 RAG（检索增强生成）聊天引擎
- Neo4j + PostgreSQL 上下文检索，确保有据可查的回答
- 知识图谱的自然语言查询
- 自动化实体路径分析和关系摘要

### 情报评级 (NATO Admiralty System)

- **可靠性** (A–F)：基于来源类型和历史准确性的来源可信度
- **可信度** (1–6)：基于交叉来源佐证、一致性和时效性的信息可信度

---

## 架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           表现层                                        │
│         Electron 33 + React 19 + TailwindCSS 4 + Zustand              │
│    ┌──────────┬──────────┬───────────┬───────────┬──────────┐          │
│    │  2D 地图  │ 3D 地球  │    图谱    │   仪表板   │  时间线   │          │
│    │ Deck.gl  │ CesiumJS │ Sigma.js  │ Recharts  │          │          │
│    └──────────┴──────────┴───────────┴───────────┴──────────┘          │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ REST / WebSocket / GraphQL
┌────────────────────────────┴────────────────────────────────────────────┐
│                          API 网关                                       │
│              FastAPI + Socket.IO + Strawberry GraphQL                   │
│         JWT 认证 │ 速率限制 │ 审计日志 │ Prometheus                       │
└──────┬─────────┬──────────┬──────────┬──────────┬──────────────────────┘
       │         │          │          │          │
┌──────┴──┐ ┌────┴───┐ ┌───┴────┐ ┌───┴───┐ ┌───┴────┐
│  Neo4j  │ │  PgSQL │ │ Redis  │ │  ES   │ │ Kafka  │
│  (KG)   │ │ 17     │ │  7.x   │ │ 8.x   │ │  3.7   │
└─────────┘ └────────┘ └────────┘ └───────┘ └────────┘
```

---

## 技术栈

| 层级 | 技术 |
|:---:|---|
| **前端** | Electron 33, React 19, TypeScript 5.7, TailwindCSS 4, Zustand, TanStack Query v5 |
| **可视化** | Deck.gl v9 + MapLibre GL JS (2D), CesiumJS (3D), Sigma.js (图谱), Recharts |
| **后端** | Python 3.12, FastAPI, Strawberry GraphQL, Socket.IO, Celery, Pydantic v2 |
| **知识图谱** | Neo4j 5.x + GDS + APOC + n10s |
| **数据库** | PostgreSQL 17 (pgvector + TimescaleDB), Elasticsearch 8.x, Redis 7.x |
| **消息队列** | Apache Kafka 3.7 |
| **存储** | MinIO（S3 兼容对象存储） |
| **监控** | Prometheus + Grafana |
| **构建** | Turborepo, pnpm 9（前端）, uv（后端） |

---

## 快速开始

### 前置要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Node.js | 20+ | 前端运行时 |
| pnpm | 9+ | 前端包管理器 |
| Python | 3.12+ | 后端运行时 |
| uv | 最新版 | Python 包管理器 |
| Docker | 24+ | 基础设施服务 |
| Docker Compose | v2+ | 服务编排 |

### 1. 克隆与配置

```bash
git clone https://github.com/your-org/nexus-msint.git
cd nexus-msint
cp .env.example .env
# 在 .env 文件中配置您的 API 密钥
```

### 2. 启动基础设施

```bash
cd infra
docker compose up -d
```

### 3. 启动后端

```bash
cd apps/api
uv pip install --system .
uvicorn nexus.main:sio_asgi_app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动前端

```bash
cd apps/desktop
pnpm install
pnpm dev
```

### 5. 运行测试

```bash
cd apps/api
JWT_SECRET=test-secret pytest
```

---

## 贡献

我们欢迎社区贡献！详情请阅读我们的[贡献指南](../CONTRIBUTING.md)。

## 许可证

本项目基于 **MIT 许可证** 授权 — 详见 [LICENSE](../LICENSE) 文件。

---

<p align="center">
  <strong>NEXUS</strong> — 将多源情报融合为可行动的洞察。
</p>
