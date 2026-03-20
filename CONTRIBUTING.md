# Contributing to NEXUS

Thank you for your interest in contributing to NEXUS! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for everyone. We pledge to make participation in our project a harassment-free experience, regardless of age, body size, disability, ethnicity, gender identity, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Standards

**Expected behavior:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Unacceptable behavior:**
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your feature or fix
4. **Make changes** following our coding standards
5. **Test** your changes thoroughly
6. **Submit** a pull request

---

## Development Setup

### Prerequisites

| Tool | Version | Installation |
|------|---------|-------------|
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| pnpm | 9+ | `npm install -g pnpm` |
| Python | 3.12+ | [python.org](https://python.org) |
| uv | latest | `pip install uv` |
| Docker | 24+ | [docker.com](https://docker.com) |

### Setup Steps

```bash
# 1. Clone your fork
git clone https://github.com/<your-username>/nexus-msint.git
cd nexus-msint

# 2. Configure environment
cp .env.example .env

# 3. Start infrastructure
cd infra && docker compose up -d && cd ..

# 4. Install backend dependencies
cd apps/api
uv pip install --system .
cd ../..

# 5. Install frontend dependencies
cd apps/desktop
pnpm install
cd ../..

# 6. Verify setup
cd apps/api && JWT_SECRET=dev-secret pytest && cd ../..
cd apps/desktop && pnpm typecheck && cd ../..
```

---

## Project Structure

```
nexus-msint/
├── apps/api/          # Python backend (FastAPI)
│   ├── nexus/         # Application source
│   └── tests/         # Backend tests
├── apps/desktop/      # Electron + React frontend
│   ├── electron/      # Electron main process
│   └── src/           # React application
├── packages/          # Shared packages
├── infra/             # Docker infrastructure
├── ontology/          # POLE/STIX ontology
└── docs/              # Documentation
```

### Key Directories

| Directory | Language | Description |
|-----------|----------|-------------|
| `apps/api/nexus/collectors/` | Python | INT collection modules (CYBINT, SOCMINT, SIGINT, GEOINT) |
| `apps/api/nexus/knowledge/` | Python | Neo4j knowledge graph client and algorithms |
| `apps/api/nexus/api/routes/` | Python | REST API endpoints |
| `apps/desktop/src/components/` | TypeScript | React UI components |
| `apps/desktop/src/stores/` | TypeScript | Zustand state management |
| `apps/desktop/src/services/` | TypeScript | API and WebSocket clients |

---

## Development Workflow

### Branch Naming

Use descriptive branch names with prefixes:

```
feature/   — New features          (feature/add-whois-collector)
fix/       — Bug fixes             (fix/websocket-reconnection)
refactor/  — Code refactoring      (refactor/entity-factory)
docs/      — Documentation         (docs/api-guide-update)
test/      — Test additions        (test/graph-algorithms)
chore/     — Maintenance tasks     (chore/update-dependencies)
```

### Running Development Servers

```bash
# Backend (auto-reload)
cd apps/api
uvicorn nexus.main:sio_asgi_app --reload --host 0.0.0.0 --port 8000

# Frontend (Vite dev server)
cd apps/desktop
pnpm dev
```

### Running Tests

```bash
# Backend tests
cd apps/api
JWT_SECRET=dev-secret pytest                    # All tests
JWT_SECRET=dev-secret pytest tests/test_entities.py -v  # Single file
JWT_SECRET=dev-secret pytest -k "test_create"   # By name pattern

# Frontend checks
cd apps/desktop
pnpm typecheck    # TypeScript
pnpm lint         # ESLint
```

---

## Coding Standards

### Python (Backend)

- **Formatter/Linter**: Ruff (line-length 120, Python 3.12 target)
- **Type Checker**: Pyright
- **Rules**: E, F, I, W, UP, S, B
- **Logging**: Use `structlog` — never `print()` or stdlib `logging`
- **Models**: Pydantic v2 with strict validation
- **Async**: Use `async/await` for I/O operations

```bash
# Run before submitting
cd apps/api
ruff check nexus/
ruff format nexus/
pyright
```

### TypeScript (Frontend)

- **Linter**: ESLint 9 with flat config
- **Formatter**: Prettier (singleQuote, printWidth 100, trailingComma all)
- **Path aliases**: `@/` maps to `src/`
- **State management**: Zustand stores
- **Data fetching**: TanStack Query v5
- **Unused vars**: Underscore-prefixed variables (`_unused`) are allowed

```bash
# Run before submitting
cd apps/desktop
pnpm lint
pnpm typecheck
```

### General Guidelines

- Write self-documenting code with clear variable and function names
- Keep functions focused — single responsibility principle
- Add type annotations to all public functions
- Handle errors gracefully — use structured error responses
- Follow existing patterns in the codebase

---

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Code refactoring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies, tooling |
| `ci` | CI/CD configuration |

### Scopes

| Scope | Description |
|-------|-------------|
| `api` | Backend API |
| `desktop` | Frontend Electron app |
| `cybint` | CYBINT collectors |
| `socmint` | SOCMINT collectors |
| `sigint` | SIGINT collectors |
| `geoint` | GEOINT collectors |
| `graph` | Knowledge graph / Neo4j |
| `infra` | Infrastructure / Docker |
| `deps` | Dependencies |

### Examples

```
feat(cybint): add Censys collector for certificate search
fix(desktop): resolve WebSocket reconnection loop on network change
refactor(graph): optimize Louvain community detection query
docs(api): update REST endpoint documentation
test(api): add integration tests for entity merge
```

---

## Pull Request Process

### Before Submitting

1. **Sync** your branch with the latest `main`
2. **Run** all linters and formatters
3. **Run** the full test suite
4. **Verify** your changes don't break existing functionality

```bash
# Backend
cd apps/api
ruff check nexus/ && ruff format --check nexus/ && JWT_SECRET=dev-secret pytest

# Frontend
cd apps/desktop
pnpm lint && pnpm typecheck
```

### PR Requirements

- **Title**: Clear and descriptive, following commit convention format
- **Description**: Explain what changed and why
- **Tests**: Include tests for new features and bug fixes
- **Documentation**: Update relevant documentation if needed
- **Screenshots**: Include screenshots for UI changes
- **Single concern**: Each PR should address one feature or fix

### PR Template

```markdown
## Summary
Brief description of the changes.

## Changes
- List of specific changes made

## Testing
- How the changes were tested
- New test cases added

## Screenshots (if applicable)
Before/after screenshots for UI changes
```

### Review Process

1. A maintainer will review your PR
2. Address any requested changes
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release

---

## Reporting Issues

### Bug Reports

When filing a bug report, include:

- **Title**: Clear, concise description
- **Environment**: OS, Node.js version, Python version, browser
- **Steps to reproduce**: Numbered steps to trigger the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs/Screenshots**: Relevant error messages or screenshots

### Feature Requests

When requesting a feature, include:

- **Use case**: Why this feature is needed
- **Proposed solution**: How you envision it working
- **Alternatives**: Other solutions you've considered
- **INT discipline**: Which intelligence discipline it relates to (if applicable)

---

## Questions?

If you have questions about contributing, feel free to:

- Open a [Discussion](https://github.com/your-org/nexus-msint/discussions) on GitHub
- Check existing [Issues](https://github.com/your-org/nexus-msint/issues)

---

Thank you for contributing to NEXUS!
