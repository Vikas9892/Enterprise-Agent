"use client";

import React, { useState } from "react";
import { AgentSession, AgentStepTrace } from "@/lib/types";
import { CheckCircle2, ChevronDown, ChevronRight, Clock, Database, Layers, Terminal, AlertTriangle } from "lucide-react";

interface StepTraceViewerProps {
  session: AgentSession;
}

export default function StepTraceViewer({ session }: StepTraceViewerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"trace" | "scratchpad" | "plan">("trace");

  return (
    <div
      style={{
        marginTop: "12px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        background: "rgba(10, 15, 26, 0.6)",
        overflow: "hidden",
      }}
    >
      {/* Header bar toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: "100%",
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: "var(--text-secondary)",
          fontSize: "0.85rem",
          fontWeight: 600,
          background: "rgba(255, 255, 255, 0.02)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Layers size={15} color="#818cf8" />
          <span>Execution Trace & Memory</span>
          <span
            style={{
              padding: "2px 8px",
              background: "rgba(99, 102, 241, 0.15)",
              color: "#a5b4fc",
              borderRadius: "var(--radius-full)",
              fontSize: "0.75rem",
            }}
          >
            {session.steps?.length || 0} steps
          </span>
          {session.requires_human_approval && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "2px 8px",
                background: "var(--status-warning-bg)",
                color: "var(--status-warning)",
                borderRadius: "var(--radius-full)",
                fontSize: "0.75rem",
              }}
            >
              <AlertTriangle size={12} />
              HITL Checkpoint
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Session: {session.session_id.substring(0, 14)}...
          </span>
          {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      {/* Expanded body */}
      {isOpen && (
        <div style={{ padding: "14px", borderTop: "1px solid var(--border-subtle)" }}>
          {/* Tab Selector */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
            <button
              onClick={() => setActiveTab("trace")}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
                fontWeight: 600,
                background: activeTab === "trace" ? "rgba(99, 102, 241, 0.2)" : "transparent",
                color: activeTab === "trace" ? "#c7d2fe" : "var(--text-muted)",
                border: activeTab === "trace" ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid transparent",
              }}
            >
              Node Transitions
            </button>
            <button
              onClick={() => setActiveTab("scratchpad")}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
                fontWeight: 600,
                background: activeTab === "scratchpad" ? "rgba(99, 102, 241, 0.2)" : "transparent",
                color: activeTab === "scratchpad" ? "#c7d2fe" : "var(--text-muted)",
                border: activeTab === "scratchpad" ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid transparent",
              }}
            >
              Working Memory (Scratchpad)
            </button>
            <button
              onClick={() => setActiveTab("plan")}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
                fontWeight: 600,
                background: activeTab === "plan" ? "rgba(99, 102, 241, 0.2)" : "transparent",
                color: activeTab === "plan" ? "#c7d2fe" : "var(--text-muted)",
                border: activeTab === "plan" ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid transparent",
              }}
            >
              Planned Steps
            </button>
          </div>

          {/* Trace Tab */}
          {activeTab === "trace" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {session.steps && session.steps.length > 0 ? (
                session.steps.map((st: AgentStepTrace, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      padding: "8px 12px",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      fontSize: "0.8rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        className="font-mono"
                        style={{
                          width: "20px",
                          height: "20px",
                          borderRadius: "50%",
                          background: "rgba(99, 102, 241, 0.2)",
                          color: "#a5b4fc",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "0.7rem",
                          fontWeight: 700,
                        }}
                      >
                        {st.step_number}
                      </span>
                      <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                        {st.node_name}
                      </span>
                      {st.action && (
                        <span style={{ color: "var(--text-muted)" }}>• {st.action}</span>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span
                        className="font-mono"
                        style={{ color: "var(--text-muted)", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "4px" }}
                      >
                        <Clock size={12} />
                        {st.latency_ms}ms
                      </span>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          padding: "2px 6px",
                          borderRadius: "var(--radius-sm)",
                          background: st.status === "completed" ? "var(--status-success-bg)" : "rgba(255, 255, 255, 0.05)",
                          color: st.status === "completed" ? "var(--status-success)" : "var(--text-secondary)",
                          textTransform: "uppercase",
                          fontWeight: 700,
                        }}
                      >
                        {st.status || "ok"}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No steps recorded yet.</div>
              )}
            </div>
          )}

          {/* Scratchpad Tab */}
          {activeTab === "scratchpad" && (
            <pre
              className="font-mono"
              style={{
                padding: "12px",
                background: "rgba(0, 0, 0, 0.4)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.75rem",
                color: "#93c5fd",
                overflowX: "auto",
                maxHeight: "220px",
              }}
            >
              {JSON.stringify(session.scratchpad || {}, null, 2)}
            </pre>
          )}

          {/* Plan Tab */}
          {activeTab === "plan" && (
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "6px" }}>
              {session.plan && session.plan.length > 0 ? (
                session.plan.map((p, idx) => (
                  <li
                    key={idx}
                    style={{
                      fontSize: "0.8rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: "var(--text-secondary)",
                    }}
                  >
                    <CheckCircle2 size={14} color="var(--status-success)" />
                    <span>{p}</span>
                  </li>
                ))
              ) : (
                <li style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>No plan steps declared.</li>
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
