"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sparkles, ExternalLink, ShieldCheck, Layers, Cpu, Server } from "lucide-react";

export default function TopHeader() {
  const pathname = usePathname();

  const getPageInfo = () => {
    switch (pathname) {
      case "/swarm":
        return {
          title: "Multi-Agent Swarm Collaboration",
          subtitle: "Supervisor Delegation • Specialist Blackboard • Consensus Review",
          badge: "Swarm Topology",
        };
      case "/knowledge":
        return {
          title: "Enterprise Knowledge & Hybrid RAG",
          subtitle: "Dense Embeddings • BM25 Lexical • Reciprocal Rank Fusion • MMR",
          badge: "Knowledge Base",
        };
      case "/observability":
        return {
          title: "Observability & System Telemetry",
          subtitle: "OpenTelemetry Distributed Traces • Prometheus Metrics • Audit Logs",
          badge: "Telemetry Engine",
        };
      case "/evaluation":
        return {
          title: "Agent Evaluation & Benchmarking",
          subtitle: "LangSmith Test Suites • Tool Precision • Safety & Governance",
          badge: "Benchmark Suite",
        };
      case "/admin":
        return {
          title: "Enterprise Administration & Governance",
          subtitle: "Multi-Tenancy • API Keys • Quota Budgeting • Dynamic Policies",
          badge: "Governance Portal",
        };
      default:
        return {
          title: "Autonomous Agent Orchestrator",
          subtitle: "Cyclical Graph Engine • Reflection Loops • Human-In-The-Loop",
          badge: "Agent Gateway",
        };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <header className="top-header">
      <div className="header-left">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <h1 className="page-title">{pageInfo.title}</h1>
          <span
            style={{
              fontSize: "0.7rem",
              background: "rgba(99, 102, 241, 0.15)",
              color: "var(--accent-primary)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              padding: "2px 8px",
              borderRadius: "4px",
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            {pageInfo.badge}
          </span>
        </div>
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "2px" }}>
          {pageInfo.subtitle}
        </p>
      </div>

      <div className="header-right">
        {/* Model Router Gateway Chip */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "0.75rem",
            padding: "4px 10px",
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            color: "var(--text-secondary)",
          }}
        >
          <Cpu size={13} color="var(--accent-primary)" />
          <span>LiteLLM: <strong style={{ color: "var(--text-primary)" }}>gpt-4o</strong></span>
          <span style={{ color: "var(--text-muted)" }}>|</span>
          <span style={{ color: "var(--status-success)" }}>Active</span>
        </div>

        {/* API Docs Button */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary"
          style={{
            padding: "5px 12px",
            fontSize: "0.78rem",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
          title="Open FastAPI Swagger Interactive Documentation"
        >
          <span>API Docs</span>
          <ExternalLink size={12} />
        </a>

        {/* User Identity Chip */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "4px 10px",
            background: "rgba(255, 255, 255, 0.04)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-full)",
          }}
        >
          <div
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              background: "var(--brand-gradient)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.72rem",
              fontWeight: 700,
              color: "white",
            }}
          >
            EA
          </div>
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
            <span style={{ fontSize: "0.78rem", fontWeight: 600 }}>Operator</span>
            <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>Admin Role</span>
          </div>
        </div>
      </div>
    </header>
  );
}
