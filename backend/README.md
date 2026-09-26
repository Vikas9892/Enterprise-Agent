# Enterprise Agent Backend

Production-ready FastAPI backend for the Enterprise Agentic AI Platform.

## Quickstart

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment configuration
cp .env.example .env

# 4. Run tests
pytest -v

# 5. Start development server
uvicorn app.main:app --reload --port 8000
```

## Structure
- `app/core/`: Configuration via `pydantic-settings` and structured JSON logging.
- `app/api/`: Versioned API routing (`/api/v1`) and root endpoints (`/health`).
- `app/agent/`: State & graph agent orchestration (Future phase).
- `app/auth/`: JWT authentication & RBAC (Future phase).
- `app/llm/`: LiteLLM gateway with retries & jitter (Future phase).
- `app/mcp/`: Model Context Protocol client (Future phase).
- `app/database/`: PostgreSQL async engine & Redis client (Future phase).
- `app/tools/`: Tool registry & execution (Future phase).
- `app/evaluation/`: LangSmith evaluation benchmarks (Future phase).
- `app/observability/`: Distributed tracing & audit logging (Future phase).
- `tests/`: Pytest fixtures and endpoint test cases.
