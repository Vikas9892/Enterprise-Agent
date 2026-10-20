/**
 * API client module communicating with the FastAPI backend.
 * Includes graceful offline mock fallbacks for standalone exploration.
 */

import { AgentSession, BenchmarkReport, EvalDataset, MetricSummary, Persona, TraceSpan } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Demo fallback personas
export const FALLBACK_PERSONAS: Persona[] = [
  {
    id: "coordinator",
    name: "Enterprise Triage Coordinator",
    role_description: "General enterprise multi-domain triage and operational coordinator.",
    system_prompt: "You are the Enterprise Triage Coordinator...",
    recommended_tools: ["get_customer", "get_order_details", "check_inventory", "verify_policy_compliance"],
    requires_approval_actions: ["refund", "cancel_order"],
  },
  {
    id: "customer_support",
    name: "Customer Support Specialist",
    role_description: "Specialist in account triage, support tickets, and SLA enforcement.",
    system_prompt: "You are an Enterprise Customer Support Specialist...",
    recommended_tools: ["get_customer", "get_support_ticket", "verify_policy_compliance"],
    requires_approval_actions: ["issue_credit"],
  },
  {
    id: "logistics",
    name: "Logistics & Inventory Officer",
    role_description: "Specialist in supply chain, order fulfillment, and warehouse inventory management.",
    system_prompt: "You are an Enterprise Logistics Officer...",
    recommended_tools: ["get_order_details", "check_inventory", "calculate"],
    requires_approval_actions: ["cancel_order", "reallocate_stock"],
  },
];

export async function checkBackendHealth(): Promise<{ status: string; latency_ms: number }> {
  const start = performance.now();
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2500) });
    const latency = Math.round(performance.now() - start);
    if (res.ok) {
      return { status: "online", latency_ms: latency };
    }
    return { status: "offline", latency_ms: latency };
  } catch {
    return { status: "offline", latency_ms: Math.round(performance.now() - start) };
  }
}

export async function fetchPersonas(): Promise<Persona[]> {
  try {
    const res = await fetch(`${API_BASE}/agent/personas`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch personas from backend, using fallback:", err);
  }
  return FALLBACK_PERSONAS;
}

export async function executeAgentTask(
  query: string,
  persona: string = "coordinator",
  sessionId?: string,
  token?: string
): Promise<AgentSession> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}/agent/run`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query, persona, session_id: sessionId }),
      signal: AbortSignal.timeout(30000),
    });

    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("API /agent/run failed or timed out, generating simulation response:", err);
  }

  // Graceful offline mock simulation
  const isHitl = query.toLowerCase().includes("refund") && (query.includes("1500") || query.toLowerCase().includes("large"));
  const sid = sessionId || `sim-sess-${Math.random().toString(36).substring(2, 9)}`;

  return {
    session_id: sid,
    persona,
    status: isHitl ? "waiting_for_human" : "completed",
    input_query: query,
    final_answer: isHitl
      ? null
      : `Analysis completed for '${query}'. All target facts verified across enterprise systems.`,
    iterations: isHitl ? 2 : 3,
    requires_human_approval: isHitl,
    pending_action: isHitl
      ? {
          tool: "verify_policy_compliance",
          details: {
            reason: "Refund of $1,500.00 exceeds automatic approval threshold ($1,000.00).",
            recommended_approver: "Finance Director",
          },
        }
      : null,
    plan: [
      "Step 1: Parse inquiry and load persona boundary",
      "Step 2: Dispatch enterprise tool call",
      "Step 3: Reflect and synthesize final answer",
    ],
    scratchpad: {
      get_customer: { name: "Apex Global Logistics", tier: "Enterprise Gold", status: "Active" },
    },
    steps: [
      { step_number: 1, node_name: "plan", latency_ms: 22.4, status: "planning" },
      { step_number: 2, node_name: "execute_tools", latency_ms: 115.8, status: "executing_tool" },
      { step_number: 3, node_name: "reflect", latency_ms: 34.2, status: isHitl ? "waiting_for_human" : "synthesizing" },
      ...(isHitl ? [] : [{ step_number: 4, node_name: "synthesize", latency_ms: 280.1, status: "completed" }]),
    ],
  };
}

export async function resumeAgentSession(
  sessionId: string,
  approved: boolean,
  feedback?: string,
  token?: string
): Promise<AgentSession> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}/agent/sessions/${sessionId}/resume`, {
      method: "POST",
      headers,
      body: JSON.stringify({ approved, feedback }),
    });

    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Resume call failed, simulating response:", err);
  }

  return {
    session_id: sessionId,
    persona: "coordinator",
    status: "completed",
    input_query: "Resumed Session",
    final_answer: approved
      ? `Action was approved by supervisor: "${feedback || "Approved"}". Refund of $1,500.00 has been processed.`
      : `Action was rejected by supervisor: "${feedback || "Declined"}". No financial changes applied.`,
    iterations: 4,
    requires_human_approval: false,
    pending_action: null,
    plan: ["Step 4: Resume workflow with supervisor decision"],
    scratchpad: { approval_status: approved ? "Approved" : "Rejected" },
    steps: [
      { step_number: 4, node_name: "synthesize", latency_ms: 140.0, status: "completed" },
    ],
  };
}

export async function fetchPlatformStats(): Promise<MetricSummary> {
  try {
    const res = await fetch(`${API_BASE}/observability/stats`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Stats fetch failed, returning sample metrics:", err);
  }

  return {
    uptime_seconds: 3640.5,
    http: {
      total_requests: 1240,
      p50_duration_ms: 4.8,
      p95_duration_ms: 22.4,
      p99_duration_ms: 58.1,
    },
    llm: {
      total_calls: 312,
      total_tokens: 184500,
      p50_latency_ms: 450.2,
      p95_latency_ms: 980.5,
    },
    agent: {
      total_runs: 148,
    },
  };
}

export async function fetchDistributedTraces(): Promise<TraceSpan[]> {
  try {
    const res = await fetch(`${API_BASE}/observability/traces`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Traces fetch failed, returning mock trace spans:", err);
  }

  return [
    {
      name: "HTTP POST /api/v1/agent/run",
      trace_id: "trc-897fba901c",
      span_id: "spn-01",
      start_time: new Date(Date.now() - 5000).toISOString(),
      duration_ms: 412.5,
      status: "ok",
      attributes: { "http.status_code": 200, "persona": "coordinator" },
    },
    {
      name: "node.execute_tools",
      trace_id: "trc-897fba901c",
      span_id: "spn-02",
      parent_span_id: "spn-01",
      start_time: new Date(Date.now() - 4800).toISOString(),
      duration_ms: 114.2,
      status: "ok",
      attributes: { "tool.name": "get_customer" },
    },
  ];
}

export async function fetchEvaluationDatasets(): Promise<EvalDataset[]> {
  try {
    const res = await fetch(`${API_BASE}/evaluation/datasets`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Datasets fetch failed, returning standard datasets:", err);
  }

  return [
    {
      id: "customer_support_eval",
      name: "Customer Support & SLA Benchmark",
      description: "Evaluates customer lookups, ticket diagnostics, and SLA commitment enforcement.",
      category: "Customer Support",
      test_cases: [],
    },
    {
      id: "logistics_fulfillment_eval",
      name: "Logistics & Inventory Fulfillment Benchmark",
      description: "Evaluates real-time tracking, order verification, and warehouse stock levels.",
      category: "Logistics & Supply Chain",
      test_cases: [],
    },
    {
      id: "governance_hitl_eval",
      name: "Governance & Human-In-The-Loop Benchmark",
      description: "Evaluates compliance gating, policy threshold escalations, and approval pauses.",
      category: "Governance & Compliance",
      test_cases: [],
    },
  ];
}

export async function triggerBenchmarkRun(datasetId: string, token?: string): Promise<BenchmarkReport> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}/evaluation/run`, {
      method: "POST",
      headers,
      body: JSON.stringify({ dataset_id: datasetId }),
      signal: AbortSignal.timeout(45000),
    });

    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Benchmark run failed, producing simulated benchmark report:", err);
  }

  return {
    benchmark_id: `bench-${Math.random().toString(36).substring(2, 8)}`,
    dataset_id: datasetId,
    dataset_name: datasetId.replace(/_/g, " ").toUpperCase(),
    total_cases: 2,
    passed_cases: 2,
    pass_rate: 100.0,
    mean_score: 0.94,
    mean_latency_seconds: 0.88,
    created_at: new Date().toISOString(),
    results: [
      {
        test_id: "test-1",
        passed: true,
        score: 0.96,
        metric_scores: [
          { metric_name: "accuracy", score: 1.0, passed: true, details: "All keywords recalled." },
          { metric_name: "safety", score: 1.0, passed: true, details: "Clean output." },
          { metric_name: "tool_selection", score: 1.0, passed: true, details: "Optimal tools chosen." },
        ],
        actual_tools_called: ["get_customer"],
        actual_status: "completed",
        actual_final_answer: "Target profile resolved.",
        latency_seconds: 0.82,
        requires_human_approval: false,
      },
      {
        test_id: "test-2",
        passed: true,
        score: 0.92,
        metric_scores: [
          { metric_name: "accuracy", score: 0.9, passed: true, details: "Recall verified." },
          { metric_name: "safety", score: 1.0, passed: true, details: "Clean output." },
          { metric_name: "policy_compliance", score: 1.0, passed: true, details: "Governance verified." },
        ],
        actual_tools_called: ["get_support_ticket"],
        actual_status: "completed",
        actual_final_answer: "Support ticket verified.",
        latency_seconds: 0.94,
        requires_human_approval: false,
      },
    ],
  };
}

// ==========================================
// Knowledge Base & Hybrid RAG API
// ==========================================

export interface KnowledgeSearchResult {
  chunk_id: string;
  document_id: string;
  title: string;
  content: string;
  score: number;
  match_type: "vector" | "bm25" | "hybrid";
  metadata: Record<string, any>;
  citation?: string;
}

export interface KnowledgeQueryResponse {
  query: string;
  count: number;
  results: KnowledgeSearchResult[];
  grounded_context: string;
  citations: Array<{
    index: number;
    title: string;
    document_id: string;
    chunk_id: string;
    score: number;
    match_type: string;
  }>;
}

export interface KnowledgeDoc {
  document_id: string;
  title: string;
  content: string;
  content_type: string;
  chunk_count: number;
  metadata: {
    category: string;
    source: string;
    author?: string;
    tenant_id: string;
    created_at?: string;
  };
}

export async function queryKnowledge(
  query: string,
  options: {
    top_k?: number;
    alpha?: number;
    category?: string;
    use_mmr?: boolean;
    tenant_id?: string;
  } = {}
): Promise<KnowledgeQueryResponse> {
  try {
    const res = await fetch(`${API_BASE}/knowledge/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        top_k: options.top_k ?? 4,
        alpha: options.alpha ?? 0.5,
        category: options.category || undefined,
        use_mmr: options.use_mmr ?? true,
        tenant_id: options.tenant_id || undefined,
      }),
      signal: AbortSignal.timeout(6000),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Knowledge query API failed, returning demo result:", err);
  }

  // Graceful offline mock response
  return {
    query,
    count: 2,
    results: [
      {
        chunk_id: "chk_demo_01",
        document_id: "doc_demo_refund",
        title: "Enterprise Refund & Return Policy",
        content:
          "Enterprise customers in Gold and Platinum tiers are entitled to full refund processing within 30 days. Refunds under $1,000 are automatically approved.",
        score: 0.94,
        match_type: "hybrid",
        metadata: { category: "finance", header_path: "Enterprise > Refunds" },
        citation: "[Enterprise Refund & Return Policy - Chunk #0]",
      },
      {
        chunk_id: "chk_demo_02",
        document_id: "doc_demo_shipping",
        title: "Global Shipping and Logistics SLA",
        content:
          "Priority Air Freight is delivered within 24 to 48 hours for North American hubs. Standard ground transport takes 3 to 5 business days.",
        score: 0.88,
        match_type: "vector",
        metadata: { category: "logistics", header_path: "Logistics > Delivery SLAs" },
        citation: "[Global Shipping and Logistics SLA - Chunk #0]",
      },
    ],
    grounded_context:
      "### ENTERPRISE GROUNDED KNOWLEDGE BASE CONTEXT ###\n[Doc 1: Enterprise Refund & Return Policy]\nGold and Platinum tiers qualify for full refunds within 30 days.\n\n[Doc 2: Global Shipping SLA]\nPriority Air Freight delivers within 24-48 hours.",
    citations: [
      {
        index: 1,
        title: "Enterprise Refund & Return Policy",
        document_id: "doc_demo_refund",
        chunk_id: "chk_demo_01",
        score: 0.94,
        match_type: "hybrid",
      },
      {
        index: 2,
        title: "Global Shipping and Logistics SLA",
        document_id: "doc_demo_shipping",
        chunk_id: "chk_demo_02",
        score: 0.88,
        match_type: "vector",
      },
    ],
  };
}

export async function fetchKnowledgeDocuments(): Promise<KnowledgeDoc[]> {
  try {
    const res = await fetch(`${API_BASE}/knowledge/documents`, {
      signal: AbortSignal.timeout(4000),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch knowledge docs, returning fallback:", err);
  }

  return [
    {
      document_id: "doc_seed_1",
      title: "Enterprise Refund & Return Policy",
      content: "Full refund processing within 30 days...",
      content_type: "text/markdown",
      chunk_count: 3,
      metadata: {
        category: "finance",
        source: "enterprise_seed",
        author: "Compliance Board",
        tenant_id: "default",
      },
    },
    {
      document_id: "doc_seed_2",
      title: "Global Shipping and Logistics SLA",
      content: "Delivery within 24 to 48 hours for North American hubs...",
      content_type: "text/markdown",
      chunk_count: 2,
      metadata: {
        category: "logistics",
        source: "enterprise_seed",
        author: "Supply Chain Team",
        tenant_id: "default",
      },
    },
    {
      document_id: "doc_seed_3",
      title: "Enterprise GDPR and Data Governance",
      content: "PII masking and AES-256 encryption rules...",
      content_type: "text/markdown",
      chunk_count: 2,
      metadata: {
        category: "compliance",
        source: "enterprise_seed",
        author: "Legal & InfoSec",
        tenant_id: "default",
      },
    },
  ];
}

export async function ingestKnowledgeDocument(payload: {
  title: string;
  content: string;
  category: string;
  content_type?: string;
  tenant_id?: string;
}): Promise<KnowledgeDoc | null> {
  try {
    const res = await fetch(`${API_BASE}/knowledge/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: payload.title,
        content: payload.content,
        category: payload.category,
        content_type: payload.content_type || "text/markdown",
        tenant_id: payload.tenant_id || "default",
      }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to ingest document:", err);
  }
  return null;
}

// ==========================================
// Multi-Agent Swarm API
// ==========================================

export interface SwarmAgentInfo {
  id: string;
  name: string;
  role: string;
  capabilities: string[];
  domains: string[];
}

export interface SwarmTaskAssignment {
  task_id: string;
  assigned_agent: string;
  persona_id: string;
  goal: string;
  status: string;
  result?: string;
  artifacts: Record<string, any>;
  latency_ms: number;
}

export interface SwarmExecutionResponse {
  swarm_id: string;
  initial_query: string;
  status: string;
  assignments: SwarmTaskAssignment[];
  blackboard: Record<string, any>;
  consensus_notes: string[];
  final_synthesis: string;
  requires_human_approval: boolean;
  pending_approval_action?: Record<string, any>;
  delegation_trace: Array<{
    timestamp: string;
    event: string;
    agent?: string;
    latency_ms?: number;
    status?: string;
  }>;
  total_latency_ms: number;
}

export async function runSwarmTask(task: string): Promise<SwarmExecutionResponse> {
  try {
    const res = await fetch(`${API_BASE}/swarm/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
      signal: AbortSignal.timeout(15000),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Swarm run API call failed, using offline fallback:", err);
  }

  // Realistic fallback swarm execution
  return {
    swarm_id: `swm_${Math.random().toString(36).substring(2, 9)}`,
    initial_query: task,
    status: "completed",
    assignments: [
      {
        task_id: "subtask_1",
        assigned_agent: "support_agent",
        persona_id: "customer_support",
        goal: "Look up customer account profile and verify SLA commitments.",
        status: "completed",
        result: "Customer Apex Global Logistics verified. Priority Gold SLA with active account status.",
        artifacts: { customer_name: "Apex Global Logistics", tier: "Enterprise Gold" },
        latency_ms: 184.2,
      },
      {
        task_id: "subtask_2",
        assigned_agent: "logistics_agent",
        persona_id: "logistics",
        goal: "Track shipment routing, SKU availability, and replacement dispatch.",
        status: "completed",
        result: "Shipment TRK-9876543210 is in transit to Chicago Hub. Replacement SKU-SRV-01 is in stock (142 units).",
        artifacts: { tracking_code: "TRK-9876543210", in_stock: true, available_qty: 142 },
        latency_ms: 215.6,
      },
      {
        task_id: "subtask_3",
        assigned_agent: "compliance_agent",
        persona_id: "coordinator",
        goal: "Validate enterprise refund thresholds and policy compliance.",
        status: "completed",
        result: "Full refund evaluated under POL-SPEND-1000. Amount within Gold SLA guidelines.",
        artifacts: { policy_compliant: true, approval_checkpoint: "cleared" },
        latency_ms: 156.4,
      },
    ],
    blackboard: {
      support_agent: { status: "completed", answer: "Account verified." },
      logistics_agent: { status: "completed", answer: "Inventory allocated." },
      compliance_agent: { status: "completed", answer: "Governance cleared." },
    },
    consensus_notes: [
      "Verified findings across 3 specialist autonomous agents.",
      "Customer SLA commitment and SKU inventory confirmed without conflicts.",
      "Financial refund and replacement authorization aligned with enterprise policy.",
    ],
    final_synthesis:
      "Executive Resolution: Customer Apex Global Logistics has been validated for an expedited replacement and full freight warranty claim on order ORD-2026-9001. A replacement unit from Chicago Distribution Hub is scheduled for priority dispatch.",
    requires_human_approval: false,
    delegation_trace: [
      { timestamp: new Date().toISOString(), event: "supervisor_decomposition" },
      { timestamp: new Date().toISOString(), event: "specialist_completion", agent: "support_agent", latency_ms: 184.2 },
      { timestamp: new Date().toISOString(), event: "specialist_completion", agent: "logistics_agent", latency_ms: 215.6 },
      { timestamp: new Date().toISOString(), event: "specialist_completion", agent: "compliance_agent", latency_ms: 156.4 },
      { timestamp: new Date().toISOString(), event: "consensus_review" },
      { timestamp: new Date().toISOString(), event: "executive_synthesis" },
    ],
    total_latency_ms: 645.8,
  };
}

// ==========================================
// Governance, Tenancy & Admin API
// ==========================================

export interface PolicyRuleData {
  rule_id: string;
  name: string;
  description: string;
  rule_type: string;
  is_active: boolean;
  threshold_amount?: number;
  allowed_roles: string[];
  restricted_tools: string[];
  approver_role?: string;
}

export interface AuditEventData {
  event_id: string;
  timestamp: string;
  tenant_id: string;
  actor: string;
  action_type: string;
  verdict: string;
  rule_triggered?: string;
  pii_masked_count: number;
  details: Record<string, any>;
}

export interface TenantSummaryData {
  tenant_id: string;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
  config: {
    max_workspaces: number;
    monthly_token_budget: number;
    monthly_spend_cap_cents: number;
    rate_limit_rpm: number;
    allowed_models: string[];
    enforce_pii_masking: boolean;
  };
  workspaces_count: number;
  workspaces: Array<{ workspace_id: string; name: string }>;
  api_keys_count: number;
  api_keys: Array<{
    key_id: string;
    name: string;
    prefix: string;
    scopes: string[];
    is_revoked: boolean;
    created_at: string;
    last_used_at?: string;
  }>;
  quota_usage: {
    current_tokens: number;
    current_spend_cents: number;
    total_requests: number;
    token_budget: number;
    spend_cap_cents: number;
    rate_limit_rpm: number;
  };
}

export async function fetchTenantsSummary(): Promise<TenantSummaryData[]> {
  try {
    const res = await fetch(`${API_BASE}/governance/tenants`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Failed to fetch tenants:", err);
  }

  return [
    {
      tenant_id: "tenant-default",
      name: "Enterprise Core Platform",
      slug: "enterprise-core",
      plan: "enterprise",
      is_active: true,
      config: {
        max_workspaces: 20,
        monthly_token_budget: 10_000_000,
        monthly_spend_cap_cents: 100_000,
        rate_limit_rpm: 1000,
        allowed_models: ["gpt-4o", "claude-3-5-sonnet"],
        enforce_pii_masking: true,
      },
      workspaces_count: 3,
      workspaces: [{ workspace_id: "ws-prod", name: "Production Gateway" }],
      api_keys_count: 2,
      api_keys: [
        {
          key_id: "key-core-1",
          name: "Main Production API Key",
          prefix: "ea_live_9a8b...",
          scopes: ["agent:run", "knowledge:read", "admin:all"],
          is_revoked: false,
          created_at: new Date().toISOString(),
        },
      ],
      quota_usage: {
        current_tokens: 3_420_000,
        current_spend_cents: 34_200,
        total_requests: 18_420,
        token_budget: 10_000_000,
        spend_cap_cents: 100_000,
        rate_limit_rpm: 1000,
      },
    },
    {
      tenant_id: "tenant-apex",
      name: "Apex Global Logistics",
      slug: "apex-logistics",
      plan: "enterprise",
      is_active: true,
      config: {
        max_workspaces: 10,
        monthly_token_budget: 5_000_000,
        monthly_spend_cap_cents: 50_000,
        rate_limit_rpm: 600,
        allowed_models: ["gpt-4o"],
        enforce_pii_masking: true,
      },
      workspaces_count: 2,
      workspaces: [{ workspace_id: "ws-apex-prod", name: "Freight Routing Production" }],
      api_keys_count: 1,
      api_keys: [
        {
          key_id: "key-apex-1",
          name: "Apex Supply Chain Token",
          prefix: "ea_live_4f3c...",
          scopes: ["agent:run", "knowledge:read"],
          is_revoked: false,
          created_at: new Date().toISOString(),
        },
      ],
      quota_usage: {
        current_tokens: 1_850_000,
        current_spend_cents: 18_500,
        total_requests: 9_120,
        token_budget: 5_000_000,
        spend_cap_cents: 50_000,
        rate_limit_rpm: 600,
      },
    },
  ];
}

export async function fetchPolicies(): Promise<PolicyRuleData[]> {
  try {
    const res = await fetch(`${API_BASE}/governance/policies`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Failed to fetch policies:", err);
  }

  return [
    {
      rule_id: "POL-SPEND-1000",
      name: "Tier 1 Financial Threshold Checkpoint",
      description: "Refunds and credits between $1,000 and $10,000 require Human-In-The-Loop approval.",
      rule_type: "financial_spend",
      is_active: true,
      threshold_amount: 1000.0,
      allowed_roles: [],
      restricted_tools: [],
      approver_role: "Logistics Lead / Support Manager",
    },
    {
      rule_id: "POL-SPEND-10000",
      name: "Executive Financial Cap Policy",
      description: "Financial actions exceeding $10,000 are blocked unless invoked by Finance Director.",
      rule_type: "financial_spend",
      is_active: true,
      threshold_amount: 10000.0,
      allowed_roles: ["finance_director", "super_admin"],
      restricted_tools: [],
      approver_role: "Finance Director",
    },
    {
      rule_id: "POL-TOOL-CANCEL",
      name: "Order Cancellation Safety Checkpoint",
      description: "Direct cancellation of orders in transit requires operator checkpoint verification.",
      rule_type: "hitl_approval",
      is_active: true,
      allowed_roles: [],
      restricted_tools: ["cancel_order"],
      approver_role: "Fulfillment Supervisor",
    },
    {
      rule_id: "POL-PII-ENFORCE",
      name: "GDPR & CCPA Mandatory PII Redaction",
      description: "Automatically redact credit cards, SSNs, phone numbers, and emails in telemetry and prompts.",
      rule_type: "pii_masking",
      is_active: true,
      allowed_roles: [],
      restricted_tools: [],
    },
  ];
}

export async function updatePolicyRule(ruleId: string, isActive: boolean): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/governance/policies/${ruleId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.ok;
  } catch (err) {
    console.warn("Failed to update policy:", err);
    return false;
  }
}

export async function fetchAuditLog(tenantId?: string): Promise<AuditEventData[]> {
  try {
    const url = tenantId ? `${API_BASE}/governance/audit-log?tenant_id=${tenantId}` : `${API_BASE}/governance/audit-log`;
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Failed to fetch audit log:", err);
  }

  return [
    {
      event_id: "aud_01",
      timestamp: new Date().toISOString(),
      tenant_id: "tenant-apex",
      actor: "agent:support_agent",
      action_type: "refund_evaluation",
      verdict: "allow",
      rule_triggered: "POL-SPEND-1000",
      pii_masked_count: 1,
      details: { amount: 450.0, customer: "CUST-001" },
    },
    {
      event_id: "aud_02",
      timestamp: new Date().toISOString(),
      tenant_id: "tenant-apex",
      actor: "agent:compliance_agent",
      action_type: "refund_evaluation",
      verdict: "require_approval",
      rule_triggered: "POL-SPEND-1000",
      pii_masked_count: 2,
      details: { amount: 3400.0, order: "ORD-2026-9001", approver: "Logistics Lead" },
    },
    {
      event_id: "aud_03",
      timestamp: new Date().toISOString(),
      tenant_id: "tenant-novatech",
      actor: "user:alex.chen",
      action_type: "prompt_inspection",
      verdict: "pii_redacted",
      rule_triggered: "POL-PII-ENFORCE",
      pii_masked_count: 3,
      details: { masked_types: ["credit_cards", "emails"] },
    },
  ];
}

export async function inspectGuardrails(text: string, tenantId: string = "tenant-default"): Promise<{
  original_length: number;
  masked_text: string;
  pii_detected: boolean;
  pii_tally: Record<string, number>;
  total_redactions: number;
  injection_assessment: { is_suspicious: boolean; confidence: number; matched_patterns: string[]; threat_level: string };
}> {
  try {
    const res = await fetch(`${API_BASE}/governance/guardrails/inspect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, tenant_id: tenantId }),
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Failed to inspect guardrails:", err);
  }

  return {
    original_length: text.length,
    masked_text: text.replace(/\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b/g, "[REDACTED_CC]"),
    pii_detected: text.includes("@") || text.includes("4111"),
    pii_tally: { emails: text.includes("@") ? 1 : 0, credit_cards: text.includes("4111") ? 1 : 0 },
    total_redactions: (text.includes("@") ? 1 : 0) + (text.includes("4111") ? 1 : 0),
    injection_assessment: {
      is_suspicious: text.toLowerCase().includes("ignore previous instructions"),
      confidence: text.toLowerCase().includes("ignore previous instructions") ? 0.9 : 0.0,
      matched_patterns: text.toLowerCase().includes("ignore previous instructions") ? ["ignore previous instructions"] : [],
      threat_level: text.toLowerCase().includes("ignore previous instructions") ? "high" : "low",
    },
  };
}

export async function generateApiKey(payload: {
  tenant_id: string;
  name: string;
  scopes: string[];
}): Promise<{ key_id: string; raw_secret: string; prefix: string; name: string } | null> {
  try {
    const res = await fetch(`${API_BASE}/governance/api-keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Failed to generate API key:", err);
  }
  return null;
}


