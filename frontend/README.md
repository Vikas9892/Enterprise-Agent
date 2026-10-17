# Enterprise Agent Platform — Frontend (Next.js)

Next-generation web application for autonomous multi-domain AI agent orchestration, real-time telemetry, Human-In-The-Loop supervisory control, and offline benchmarking.

---

## 1. Technology Architecture

- **Framework**: Next.js 14.x (App Router, React 18, TypeScript)
- **Styling**: Vanilla CSS Design System with midnight slate, cybernetic gradients, and glassmorphic panels
- **Icons**: Lucide React
- **API Proxy**: Next.js rewrites to `http://localhost:8000/api/v1`

---

## 2. Core Capabilities

### 🤖 Autonomous Agent Chat (`/`)
- Multi-turn conversational interface with real-time state machine feedback.
- **State Machine Trace Inspector**: Inspect node transitions (`plan` -> `execute_tools` -> `reflect` -> `synthesize`), per-step latency, and working memory scratchpad.
- **Human-In-The-Loop (HITL) Checkpoints**: Prompts supervisor approval when agents trigger sensitive enterprise actions (e.g., refund > $1,000 or cancellation), with approval/rejection and feedback steering.
- **Persona Switcher**: Seamlessly toggle between `Enterprise Triage Coordinator`, `Customer Support Specialist`, and `Logistics & Inventory Officer`.

### 📊 Observability & System Telemetry (`/observability`)
- Real-time KPI metrics: HTTP request counts, p50/p95 latency percentiles, and LLM token usage across models.
- Distributed Trace Spans table with trace ID search, status badges, and duration metrics.
- Direct link to raw Prometheus scraping endpoint.

### 🏆 Evaluation & Benchmarking Suites (`/evaluation`)
- Standardized offline evaluation suites:
  - `Customer Support & SLA Benchmark`
  - `Logistics & Inventory Fulfillment Benchmark`
  - `Governance & Human-In-The-Loop Benchmark`
- Compound test scoring evaluating **Accuracy**, **Tool Selection**, **Safety**, **HITL Policy Compliance**, and **Latency Budgets**.

---

## 3. Getting Started

### Install Dependencies
```bash
cd frontend
npm install
```

### Start Development Server
```bash
npm run dev
```

The application will start on **[http://localhost:3000](http://localhost:3000)**.

### Build for Production
```bash
npm run build
npm run start
```
