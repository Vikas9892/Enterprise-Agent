"use client";

import React, { useState, useEffect } from "react";
import { MetricSummary, TraceSpan } from "@/lib/types";
import { fetchDistributedTraces, fetchPlatformStats } from "@/lib/api";
import { Activity, Cpu, Layers, Clock, Zap, ArrowUpRight, Search, RefreshCw, Server } from "lucide-react";

export default function ObservabilityPage() {
  const [stats, setStats] = useState<MetricSummary | null>(null);
  const [traces, setTraces] = useState<TraceSpan[]>([]);
  const [searchTraceId, setSearchTraceId] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [s, t] = await Promise.all([fetchPlatformStats(), fetchDistributedTraces()]);
      setStats(s);
      setTraces(t);
    } catch (err) {
      console.error("Failed to load observability data:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredTraces = searchTraceId.trim()
    ? traces.filter((t) => t.trace_id.toLowerCase().includes(searchTraceId.toLowerCase()) || t.name.toLowerCase().includes(searchTraceId.toLowerCase()))
    : traces;

  return (
    <div
      style={{
        padding: "28px 32px",
        height: "100%",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: "24px",
      }}
    >
      {/* Top Banner */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "4px" }}>
            Telemetry, Traces & Prometheus Metrics
          </h2>
          <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            Real-time distributed tracing, latency percentiles, LLM token utilization, and compliance logs.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <a
            href="http://localhost:8000/api/v1/observability/metrics"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
            style={{ fontSize: "0.85rem", padding: "8px 14px" }}
          >
            <Server size={14} />
            <span>Raw Prometheus Feed</span>
          </a>

          <button
            onClick={loadData}
            disabled={isRefreshing}
            className="btn-secondary"
            style={{ fontSize: "0.85rem", padding: "8px 14px" }}
          >
            <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Stat Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "18px",
        }}
      >
        {/* Card 1: HTTP Traffic */}
        <div className="glass-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
              HTTP Throughput
            </span>
            <div style={{ padding: "6px", background: "rgba(59, 130, 246, 0.15)", borderRadius: "var(--radius-sm)", color: "#60a5fa" }}>
              <Zap size={16} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {stats?.http.total_requests.toLocaleString() || "0"}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "8px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
            <span>p50: <strong style={{ color: "var(--text-primary)" }}>{stats?.http.p50_duration_ms}ms</strong></span>
            <span>•</span>
            <span>p95: <strong style={{ color: "#f59e0b" }}>{stats?.http.p95_duration_ms}ms</strong></span>
          </div>
        </div>

        {/* Card 2: LLM Gateway */}
        <div className="glass-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
              LLM Invocations
            </span>
            <div style={{ padding: "6px", background: "rgba(139, 92, 246, 0.15)", borderRadius: "var(--radius-sm)", color: "#a78bfa" }}>
              <Cpu size={16} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {stats?.llm.total_calls.toLocaleString() || "0"}
          </div>
          <div style={{ marginTop: "8px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
            Tokens: <strong style={{ color: "#38bdf8" }}>{stats?.llm.total_tokens.toLocaleString()}</strong> across providers
          </div>
        </div>

        {/* Card 3: Agent Orchestrator Runs */}
        <div className="glass-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
              Agent Workflows
            </span>
            <div style={{ padding: "6px", background: "rgba(16, 185, 129, 0.15)", borderRadius: "var(--radius-sm)", color: "#34d399" }}>
              <Layers size={16} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {stats?.agent.total_runs.toLocaleString() || "0"}
          </div>
          <div style={{ marginTop: "8px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
            State Machine Graphs Executed
          </div>
        </div>

        {/* Card 4: Platform Uptime */}
        <div className="glass-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
              Platform Uptime
            </span>
            <div style={{ padding: "6px", background: "rgba(245, 158, 11, 0.15)", borderRadius: "var(--radius-sm)", color: "#fbbf24" }}>
              <Clock size={16} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {stats ? `${Math.floor(stats.uptime_seconds / 60)}m ${Math.floor(stats.uptime_seconds % 60)}s` : "0s"}
          </div>
          <div style={{ marginTop: "8px", fontSize: "0.78rem", color: "var(--status-success)", display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="pulse-dot" /> Continuous Telemetry Feed
          </div>
        </div>
      </div>

      {/* Distributed Trace Explorer */}
      <div className="glass-card" style={{ padding: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
          <div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "2px" }}>
              Distributed Traces & Spans
            </h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              OpenTelemetry-compatible trace spans tracking execution latency across endpoints and state nodes.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "rgba(0, 0, 0, 0.4)",
              border: "1px solid var(--border-medium)",
              borderRadius: "var(--radius-md)",
              padding: "6px 12px",
              width: "280px",
            }}
          >
            <Search size={14} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search trace or span name..."
              value={searchTraceId}
              onChange={(e) => setSearchTraceId(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text-primary)",
                fontSize: "0.82rem",
                width: "100%",
              }}
            />
          </div>
        </div>

        {/* Traces Table */}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left", color: "var(--text-muted)" }}>
                <th style={{ padding: "10px 14px", fontWeight: 600 }}>Span Name</th>
                <th style={{ padding: "10px 14px", fontWeight: 600 }}>Trace ID</th>
                <th style={{ padding: "10px 14px", fontWeight: 600 }}>Duration</th>
                <th style={{ padding: "10px 14px", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "10px 14px", fontWeight: 600 }}>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filteredTraces.length > 0 ? (
                filteredTraces.map((sp, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      background: idx % 2 === 0 ? "transparent" : "rgba(255, 255, 255, 0.01)",
                    }}
                  >
                    <td style={{ padding: "12px 14px", fontWeight: 600, color: "var(--text-primary)" }}>
                      <span className="font-mono">{sp.name}</span>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span
                        className="font-mono"
                        style={{
                          fontSize: "0.75rem",
                          padding: "2px 6px",
                          borderRadius: "var(--radius-sm)",
                          background: "rgba(99, 102, 241, 0.12)",
                          color: "#c7d2fe",
                        }}
                      >
                        {sp.trace_id.substring(0, 14)}...
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span className="font-mono" style={{ color: sp.duration_ms > 500 ? "#f59e0b" : "#34d399", fontWeight: 600 }}>
                        {sp.duration_ms}ms
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: "var(--radius-full)",
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          background: sp.status === "ok" ? "var(--status-success-bg)" : "var(--status-danger-bg)",
                          color: sp.status === "ok" ? "var(--status-success)" : "var(--status-danger)",
                        }}
                      >
                        {sp.status}
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px", color: "var(--text-muted)", fontSize: "0.78rem" }}>
                      {new Date(sp.start_time).toLocaleTimeString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)" }}>
                    No distributed trace spans found matching search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
