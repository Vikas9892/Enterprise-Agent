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

# 4. Run database migrations
alembic upgrade head

# 5. Seed realistic enterprise data
python scripts/seed_data.py

# 6. Run tests
pytest -v

# 7. Start development server
uvicorn app.main:app --reload --port 8000
```

## Structure
- `app/core/`: Configuration via `pydantic-settings` and structured JSON logging.
- `app/api/`: Versioned API routing (`/api/v1`) and root endpoints (`/health`).
- `app/database/`: PostgreSQL connection, session management, models, and repositories.
  - `models/`: User, Role, Permission, Customer, Product, Inventory, Order, OrderItem, Invoice, SupportTicket, AuditLog.
  - `repositories/`: CustomerRepository, OrderRepository, ProductRepository, InvoiceRepository, SupportTicketRepository, UserRepository, AuditLogRepository.
- `app/agent/`: State & graph agent orchestration (Future phase).
- `app/auth/`: JWT authentication & RBAC (Phase 3 Active - JWT, bcrypt, RBAC dependencies).
- `app/llm/`: LiteLLM gateway with retries & jitter (Future phase).
- `app/mcp/`: Model Context Protocol client (Future phase).
- `app/tools/`: Tool registry & execution (Future phase).
- `app/evaluation/`: LangSmith evaluation benchmarks (Future phase).
- `app/observability/`: Distributed tracing & audit logging (Future phase).
- `alembic/`: Schema migration versions and environment runner.
- `scripts/`: Seed data scripts.
- `tests/`: Pytest fixtures and unit/integration test cases.
