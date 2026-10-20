/**
 * TypeScript data models and contracts mirroring backend FastAPI schemas.
 */

export interface Persona {
  id: string;
  name: string;
  role_description: string;
  system_prompt: string;
  recommended_tools: string[];
  requires_approval_actions: string[];
}

export interface AgentStepTrace {
  step_number: number;
  node_name: string;
  action?: string | null;
  observation?: string | null;
  reflection?: string | null;
  latency_ms: number;
  status?: string;
}

export interface AgentSession {
  session_id: string;
  persona: string;
  status: "initialized" | "planning" | "executing_tool" | "reflecting" | "waiting_for_human" | "synthesizing" | "completed" | "failed";
  input_query: string;
  final_answer?: string | null;
  iterations: number;
  requires_human_approval: boolean;
  pending_action?: {
    tool?: string;
    action?: string;
    details?: any;
    name?: string;
    arguments?: any;
  } | null;
  plan: string[];
  scratchpad: Record<string, any>;
  steps: AgentStepTrace[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  session?: AgentSession | null;
  streaming?: boolean;
}

export interface MetricSummary {
  uptime_seconds: number;
  http: {
    total_requests: number;
    p50_duration_ms: number;
    p95_duration_ms: number;
    p99_duration_ms: number;
  };
  llm: {
    total_calls: number;
    total_tokens: number;
    p50_latency_ms: number;
    p95_latency_ms: number;
  };
  agent: {
    total_runs: number;
  };
}

export interface TraceSpan {
  name: string;
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  start_time: string;
  end_time?: string | null;
  duration_ms: number;
  status: string;
  error_message?: string | null;
  attributes: Record<string, any>;
}

export interface EvalTestCase {
  id: string;
  name: string;
  query: string;
  persona: string;
  expected_tools: string[];
  forbidden_tools: string[];
  expected_keywords: string[];
  forbidden_keywords: string[];
  requires_human_approval?: boolean | null;
  max_latency_seconds: number;
}

export interface EvalDataset {
  id: string;
  name: string;
  description: string;
  category: string;
  test_cases: EvalTestCase[];
}

export interface EvalMetricScore {
  metric_name: string;
  score: number;
  passed: boolean;
  details: string;
}

export interface EvalTestCaseResult {
  test_id: string;
  passed: boolean;
  score: number;
  metric_scores: EvalMetricScore[];
  actual_tools_called: string[];
  actual_status: string;
  actual_final_answer?: string | null;
  latency_seconds: number;
  requires_human_approval: boolean;
  error?: string | null;
}

export interface BenchmarkReport {
  benchmark_id: string;
  dataset_id: string;
  dataset_name: string;
  total_cases: number;
  passed_cases: number;
  pass_rate: number;
  mean_score: number;
  mean_latency_seconds: number;
  created_at: string;
  results: EvalTestCaseResult[];
}
