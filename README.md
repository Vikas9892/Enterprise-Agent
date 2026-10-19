# Enterprise Agentic AI Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.7+-e92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev)
[![Code Style](https://img.shields.io/badge/Code%20Style-Production-black.svg)](https://peps.python.org/pep-0008/)

## 1. Project Purpose

The **Enterprise Agentic AI Platform** is a production-grade, extensible framework engineered for autonomous enterprise agents. It delivers enterprise-ready reliability, security, multi-model LLM routing, and asynchronous state-machine workflows.

### Planned Platform Capabilities
- **FastAPI Backend**: Async, typed, high-throughput REST & streaming API gateway.
- **PostgreSQL & Redis**: Hybrid state persistence, session caching, and pub/sub messaging.
- **Security & RBAC**: JWT authentication, fine-grained role-based access control, and tenant isolation.
- **MCP Client/Server Architecture**: Model Context Protocol integration for dynamic enterprise tool discovery and context grounding.
- **Graph/State-Based Agent Orchestration**: Graph-based cyclical reasoning, state persistence, and human-in-the-loop validation.
- **LiteLLM Gateway**: Multi-provider resilience with automatic fallbacks, rate-limit retries, exponential backoff, and jitter.
- **Observability & Evaluation**: OpenTelemetry and LangSmith tracing, audit logging, and automated eval benchmarks.
- **Next.js Frontend**: Real-time conversational interface with streaming responses and execution graph visualization.

---

## 2. High-Level Architecture

The platform follows a clean **Monorepo** design dividing concerns into three isolated domains:

```
Enterprise-Agent/
├── backend/            # Core FastAPI backend, agents, LLM, auth & observability
├── mcp-server/         # Model Context Protocol server (tools & resource provider)
├── frontend/           # Next.js conversational web interface
├── .env.example        # Root environment template
└── .gitignore          # Repository git ignore rules
```

### Monorepo Structure

```mermaid
graph TD
    Client[Next.js Frontend / External Clients] -->|REST / SSE / WebSockets| Gateway[FastAPI Gateway :8000]
    Gateway --> Auth[Auth & RBAC]
    Gateway --> Agent[Graph Agent Orchestrator]
    Agent --> LLM[LiteLLM Gateway + Retries]
    Agent --> Tools[Tool Execution Registry]
    Agent --> MCP[MCP Client]
    MCP -->|JSON-RPC / SSE| MCPServer[MCP Server :8001]
    Gateway --> DB[(PostgreSQL + Redis)]
    Gateway --> Observability[LangSmith & Structured Logging]
```

### Phase 1: Architectural Foundation

Phase 1 establishes the rock-solid foundational core without premature complexity:
- Modular package boundaries (`api`, `agent`, `auth`, `llm`, `mcp`, `database`, `tools`, `evaluation`, `observability`).
- Immutable configuration management using `pydantic-settings`.
- Structured JSON logging with standardized fields (`timestamp`, `level`, `module`, `function`, `line_number`, `extra`).
- Zero-overhead `/health` liveness probe.
- Fully typed Python code with complete `pytest` coverage.

---

## 3. Directory Layout & Package Roles

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, lifespan, CORS, middleware
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings (BaseSettings)
│   │   └── logging.py              # Structured JSON logging formatter & handler setup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py               # Master API router (/api)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # v1 API router (/api/v1)
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── health.py       # Health check schema & endpoint implementation
│   ├── agent/                      # Graph- & state-based agent orchestration workflows
│   ├── auth/                       # JWT authentication, token decoding, and RBAC
│   ├── llm/                        # LiteLLM client, streaming, retries, jitter
│   ├── mcp/                        # Model Context Protocol (MCP) client & transport
│   ├── database/                   # PostgreSQL async engine, Redis clients, Alembic
│   ├── tools/                      # Tool registry, schemas, and execution sandboxes
│   ├── evaluation/                 # LangSmith datasets, evals, and benchmark suites
│   └── observability/              # Distributed tracing, OpenTelemetry, audit logs
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures and test dependency overrides
│   └── test_health.py              # Health check unit and integration tests
├── .env.example                    # Environment variable template
├── pyproject.toml                  # Project metadata, build settings, and pytest config
├── requirements.txt                # Pinned production and test dependencies
└── README.md                       # Backend specific documentation
```

---

## 4. Getting Started

### Prerequisites
- Python 3.11 or higher
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Vikas9892/Enterprise-Agent.git
cd Enterprise-Agent
```

### 2. Set Up Python Virtual Environment
```bash
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```
*(On Windows PowerShell, use `Copy-Item .env.example .env`)*

---

## 5. Running the Application

### Start the FastAPI Development Server
```bash
# From within the backend/ directory with .venv active:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Alternatively, run directly with Python:
```bash
python -m app.main
```

The application will start on `http://localhost:8000`.

### Interactive API Documentation
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 6. Verifying the Health Endpoint

### Direct Root Check:
```bash
curl -X GET http://localhost:8000/health
```

### Versioned API Check:
```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Expected JSON Response (HTTP 200 OK):**
```json
{
  "status": "healthy",
  "app_name": "Enterprise Agent Platform",
  "version": "0.1.0",
  "environment": "development"
}
```

---

## 7. Running Database Migrations & Seeding

### Apply Alembic Migrations
```bash
# Apply all pending schema migrations
alembic upgrade head
```

### Seed Demo Data
Populate the database with enterprise customers, products, inventory, orders, invoices, support tickets, users, and RBAC roles:
```bash
python scripts/seed_data.py
```

---

## 8. Running the Test Suite

Execute the full suite covering API endpoints, database models, and repository operations:

```bash
# From within the backend/ directory with .venv active:
pytest -v
```

To run with concise output:
```bash
pytest -ra -q
```

---

## 9. Full-Stack Container & Kubernetes Deployment

### Docker Compose Quickstart
Run the entire production-grade topology (PostgreSQL, Redis, MCP Server, Backend, Frontend) with a single command:

```bash
docker compose up --build -d
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend & API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MCP Tool Server**: [http://localhost:8001/tools](http://localhost:8001/tools)
- **PostgreSQL 16**: `localhost:5432`
- **Redis 7**: `localhost:6379`

### Kubernetes Deployment
Deploy the platform into any standard Kubernetes or Minikube cluster:

```bash
kubectl apply -f k8s/
```

Includes:
- **`backend-deployment.yaml`**: Multi-replica backend Deployment with ConfigMap, HPA (Horizontal Pod Autoscaler), and health probes.
- **`frontend-deployment.yaml`**: Next.js frontend Deployment and ClusterIP Service.
- **`mcp-deployment.yaml`**: MCP tool server Deployment and Service.
- **`ingress.yaml`**: Nginx Ingress Controller rules routing `/api`, `/docs`, and `/` traffic.

---

## 10. Multi-Agent Swarm Collaboration

The platform includes a supervisor-orchestrated multi-agent swarm architecture:
- **Supervisor Agent**: Decomposes complex user queries into domain-specific subtasks and synthesizes consensus.
- **Support Agent**: Handles customer issues, CRM inquiries, ticket lookups, and escalations.
- **Logistics Agent**: Manages shipping, tracking numbers, stock reservations, and carrier schedules.
- **Compliance Agent**: Validates enterprise policies, GDPR constraints, and spending approval thresholds.
- **Blackboard Memory**: Shared thread state allowing specialist agents to share structured artifacts and debate findings.

Test the swarm via REST or SSE streaming:
```bash
# REST execution
curl -X POST http://localhost:8000/api/v1/swarm/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Customer CUST-001 needs an expedited return on damaged shipment TRK-992 with policy review"}'
```

---

## 11. Enterprise Knowledge Retrieval & Hybrid RAG

The platform features an enterprise-grade document ingestion and hybrid retrieval engine:
- **Multi-Format Ingestion**: Ingests Markdown, plaintext, CSV tables, and structured JSON with recursive semantic chunking, fixed window, and markdown header hierarchy preservation.
- **Dense Vector Embeddings**: High-throughput normalized 128-dimensional semantic embeddings with cosine similarity and metadata filtering.
- **Sparse BM25 Okapi Index**: Robertson-Spärck Jones IDF keyword retrieval with term saturation and stopword elimination.
- **Reciprocal Rank Fusion (RRF)**: Merges dense vector and sparse lexical ranks using $RRF(d) = \sum \frac{w_i}{k + rank_i(d)}$ with configurable $\alpha$ balance.
- **Maximal Marginal Relevance (MMR)**: Re-ranks candidate passages to minimize semantic redundancy and maximize information diversity.
- **Grounding Guardrails & Citation Attribution**: Verifies that LLM statements are factually grounded in source passages and detects hallucinations with automated confidence scoring.

---

## 12. Multi-Tenant Administration & Dynamic Governance

Production-ready enterprise isolation and policy enforcement:
- **Multi-Tenant Workspaces**: Organization-level isolation, project workspaces, and per-tenant configurations.
- **Cryptographic API Key Management**: Secure `ea_live_...` secrets hashed with SHA-256 digests and fine-grained authorization scopes.
- **Sliding-Window Rate Limiting & Token Quotas**: Minute-level request rate limiting (RPM) and monthly token/spend budget enforcement.
- **Real-Time PII Masking**: Automatically redacts credit cards, SSNs, email addresses, phone numbers, and API tokens before persistence or external dispatch.
- **Adversarial Prompt Injection Defense**: Heuristic detectors identifying system overrides, jailbreak attempts, and safety bypass instructions.
- **Dynamic Policy Engine**: Runtime configurable rules governing financial spend caps, tool permissions by role, and mandatory HITL approval checkpoints.
- **Immutable Audit Trail**: Centralized logging recording all governed actions, rule violations, and PII redactions for compliance auditing.

---

## 13. Phase Evolution Roadmap

| Phase | Milestone | Status | Description |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Foundation** | Done | Clean monorepo, FastAPI skeleton, Pydantic settings, structured logging, tests |
| **Phase 2** | **Database & Domain Foundation** | Done | PostgreSQL, SQLAlchemy 2.x, Alembic, 11 models, 8 repositories, migrations & seed |
| **Phase 3** | **Security & Authentication** | Done | JWT authentication, bcrypt password hashing, auth endpoints, and RBAC dependencies |
| **Phase 4** | **LLM Gateway & MCP** | Done | LiteLLM routing, exponential backoff with jitter, MCP client and MCP server |
| **Phase 5** | **Agent Orchestrator** | Done | State-machine graph engine, cyclical reflection loops, HITL approval checkpoints, tool execution, session persistence |
| **Phase 6** | **Observability & Eval** | Done | OpenTelemetry distributed tracing, Prometheus metrics, LangSmith run exporter, audit middleware, benchmark suites |
| **Phase 7** | **Frontend Experience** | Done | Next.js 14 App Router, glassmorphic dark mode, real-time chat, tool trace inspector, HITL controls, observability & benchmark UI |
| **Phase 8** | **Multi-Agent Swarms & Production Deployment** | Done | Multi-agent swarm orchestration, supervisor delegation, Docker Compose, Kubernetes manifests, CI/CD automation |
| **Phase 9** | **Enterprise Knowledge Retrieval & Hybrid RAG** | Done | Semantic chunking, vector embeddings, BM25 Okapi, Reciprocal Rank Fusion, MMR reranking, grounding guardrails, UI |
| **Phase 10** | **Multi-Tenant Administration & Governance Portal** | Done | Organization workspaces, API key quotas, rate limiting, real-time PII masking, policy engine, swarm visualizer & admin UI |

---

## 14. License & Authorship

- **Author**: vikas9892 ([vikast4843@gmail.com](mailto:vikast4843@gmail.com))
- **Repository**: [https://github.com/Vikas9892/Enterprise-Agent](https://github.com/Vikas9892/Enterprise-Agent)


