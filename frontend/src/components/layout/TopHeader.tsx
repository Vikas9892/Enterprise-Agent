"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sparkles, ExternalLink, ShieldCheck, User } from "lucide-react";

export default function TopHeader() {
  const pathname = usePathname();

  const getTitle = () => {
    if (pathname === "/observability") return "Observability & System Telemetry";
    if (pathname === "/evaluation") return "Agent Evaluation & Benchmarking";
    return "Autonomous Agent Orchestrator";
  };

  return (
    <header className="top-header">
      <div className="header-left">
        <h1 className="page-title">{getTitle()}</h1>
      </div>

      <div className="header-right">
        <div className="persona-badge-chip">
          <Sparkles size={14} color="#818cf8" />
          <span>Multi-Domain Orchestration Active</span>
        </div>

        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary"
          style={{ padding: "6px 12px", fontSize: "0.8rem", textDecoration: "none" }}
          title="Open FastAPI Swagger Interactive Docs"
        >
          <span>API Docs</span>
          <ExternalLink size={13} />
        </a>

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
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "white",
            }}
          >
            EA
          </div>
          <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Operator</span>
        </div>
      </div>
    </header>
  );
}
