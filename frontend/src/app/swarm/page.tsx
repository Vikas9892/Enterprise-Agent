"use client";

import React, { useState } from "react";
import {
  Network,
  Users,
  Cpu,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Sparkles,
  ArrowRight,
  Bot,
  Layers,
  FileCheck,
  AlertTriangle,
  Play,
  Loader2,
  Copy,
  Check,
} from "lucide-react";
import { runSwarmTask, SwarmExecutionResponse } from "@/lib/api";

const PRESET_SCENARIOS = [
  {
    title: "Damaged Shipment Return Claim",
    task: "Customer Apex Global Logistics (CUST-001) received a damaged shipment TRK-9876543210. Verify customer tier, inspect inventory for SKU-SRV-01 replacement, and review enterprise refund policy compliance.",
  },
  {
    title: "High-Value Refund & Compliance Escalation",
    task: "NovaTech Dynamics (CUST-002) requests an immediate $14,250 credit refund on cancelled server order ORD-2026-9001. Assess financial policy caps and verify required human approver.",
  },
  {
    title: "Supply Chain Warehouse Reallocation",
    task: "Check stock availability across regional distribution hubs for 50 units of SKU-SRV-01 and verify priority air freight shipping SLAs for expedited dispatch.",
  },
];

export default function SwarmPage() {
  const [taskQuery, setTaskQuery] = useState(PRESET_SCENARIOS[0].task);
  const [isRunning, setIsRunning] = useState(false);
  const [swarmResult, setSwarmResult] = useState<SwarmExecutionResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const handleExecute = async () => {
    if (!taskQuery.trim()) return;
    setIsRunning(true);
    try {
      const res = await runSwarmTask(taskQuery);
      setSwarmResult(res);
    } catch (err) {
      console.error("Swarm execution failed:", err);
    } finally {
      setIsRunning(false);
    }
  };

  const copySynthesis = () => {
    if (swarmResult?.final_synthesis) {
      navigator.clipboard.writeText(swarmResult.final_synthesis);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

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
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "4px", display: "flex", alignItems: "center", gap: "10px" }}>
            <Network size={24} color="var(--accent-primary)" />
            Multi-Agent Swarm Collaboration & Supervisor Delegation
          </h2>
          <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            A supervisor orchestrator autonomously decomposes multi-domain enterprise queries, delegating subtasks to parallel specialist agents with a shared blackboard.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "0.78rem",
              background: "rgba(16, 185, 129, 0.15)",
              color: "var(--status-success)",
              padding: "4px 10px",
              borderRadius: "6px",
              fontWeight: 600,
            }}
          >
            ● Swarm Topology Active (3 Specialists)
          </span>
        </div>
      </div>

      {/* Task Input Card */}
      <div
        style={{
          background: "var(--bg-card)",
          borderRadius: "12px",
          border: "1px solid var(--border-color)",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-secondary)" }}>
            Enterprise Task or Operational Objective
          </span>
          <div style={{ display: "flex", gap: "8px" }}>
            {PRESET_SCENARIOS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => setTaskQuery(p.task)}
                style={{
                  fontSize: "0.75rem",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  background: taskQuery === p.task ? "var(--accent-primary)" : "rgba(255,255,255,0.05)",
                  color: taskQuery === p.task ? "#fff" : "var(--text-secondary)",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                {p.title}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px" }}>
          <textarea
            rows={3}
            value={taskQuery}
            onChange={(e) => setTaskQuery(e.target.value)}
            placeholder="Type a multi-domain enterprise task to trigger supervisor decomposition and swarm consensus..."
            style={{
              flex: 1,
              padding: "12px 16px",
              background: "rgba(0,0,0,0.3)",
              border: "1px solid var(--border-color)",
              borderRadius: "8px",
              color: "var(--text-primary)",
              fontSize: "0.9rem",
              fontFamily: "inherit",
              resize: "none",
            }}
          />

          <button
            onClick={handleExecute}
            disabled={isRunning}
            style={{
              padding: "0 24px",
              background: "var(--accent-primary)",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              fontWeight: 600,
              fontSize: "0.95rem",
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              minWidth: "120px",
            }}
          >
            {isRunning ? <Loader2 size={20} className="spin" /> : <Play size={20} />}
            <span>{isRunning ? "Running..." : "Run Swarm"}</span>
          </button>
        </div>
      </div>

      {/* Swarm Architecture Flow */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto 2.2fr", gap: "16px", alignItems: "center" }}>
        {/* Supervisor Card */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.08))",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            borderRadius: "12px",
            padding: "18px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Cpu size={20} color="var(--accent-primary)" />
            <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>Supervisor Orchestrator</span>
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.4 }}>
            Deconstructs complex goals into domain subtasks, dispatches parallel execution routines, and synthesizes final resolution.
          </p>
          <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
            <span style={{ fontSize: "0.72rem", background: "rgba(99, 102, 241, 0.2)", padding: "2px 6px", borderRadius: "4px", color: "var(--accent-primary)" }}>
              Decomposition
            </span>
            <span style={{ fontSize: "0.72rem", background: "rgba(99, 102, 241, 0.2)", padding: "2px 6px", borderRadius: "4px", color: "var(--accent-primary)" }}>
              Consensus Review
            </span>
          </div>
        </div>

        <ArrowRight size={20} color="var(--text-muted)" />

        {/* Specialist Agent Nodes */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
          {/* Agent 1 */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "10px",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Users size={16} color="#38bdf8" />
              <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>Customer Triage</span>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: 0 }}>
              CRM profiles, active support tickets, and customer SLA verification.
            </p>
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "auto" }}>
              Tools: get_customer, get_support_ticket
            </span>
          </div>

          {/* Agent 2 */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "10px",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={16} color="#10b981" />
              <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>Supply Chain Officer</span>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: 0 }}>
              Shipment route tracking, warehouse SKU inventory, and carrier routing.
            </p>
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "auto" }}>
              Tools: get_order_details, check_inventory
            </span>
          </div>

          {/* Agent 3 */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "10px",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <ShieldAlert size={16} color="#f59e0b" />
              <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>Compliance & Policy</span>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: 0 }}>
              Financial approval caps, GDPR data audit, and HITL checkpoints.
            </p>
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "auto" }}>
              Tools: verify_policy_compliance, search_knowledge
            </span>
          </div>
        </div>
      </div>

      {/* Execution Results View */}
      {swarmResult && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* HITL Notice Banner if triggered */}
          {swarmResult.requires_human_approval && (
            <div
              style={{
                background: "rgba(245, 158, 11, 0.15)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                padding: "14px 18px",
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <AlertTriangle size={20} color="#f59e0b" />
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f59e0b" }}>
                    Swarm Execution Paused: Human-In-The-Loop Approval Triggered
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                    Specialist agent requires operational confirmation before proceeding with sensitive action.
                  </div>
                </div>
              </div>
              <button
                style={{
                  background: "#f59e0b",
                  color: "#000",
                  fontWeight: 700,
                  fontSize: "0.82rem",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Approve Action
              </button>
            </div>
          )}

          {/* Parallel Specialist Execution Cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "8px" }}>
              <Clock size={16} /> Decomposed Specialist Subtasks ({swarmResult.assignments.length}) — Total Latency: {swarmResult.total_latency_ms}ms
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
              {swarmResult.assignments.map((assignment) => (
                <div
                  key={assignment.task_id}
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "10px",
                    padding: "16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.85rem", textTransform: "capitalize", color: "var(--accent-primary)" }}>
                      {assignment.assigned_agent.replace("_", " ")}
                    </span>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        background: "rgba(16, 185, 129, 0.15)",
                        color: "var(--status-success)",
                        fontWeight: 600,
                      }}
                    >
                      {assignment.latency_ms}ms
                    </span>
                  </div>

                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    Goal: {assignment.goal}
                  </div>

                  <div
                    style={{
                      background: "rgba(0,0,0,0.25)",
                      padding: "10px",
                      borderRadius: "6px",
                      fontSize: "0.82rem",
                      color: "var(--text-primary)",
                      lineHeight: 1.45,
                    }}
                  >
                    {assignment.result || "Processing completed."}
                  </div>

                  {assignment.artifacts && Object.keys(assignment.artifacts).length > 0 && (
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                      Artifacts: {Object.keys(assignment.artifacts).join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Blackboard & Consensus Review */}
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px" }}>
            {/* Shared Blackboard State */}
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                <Layers size={16} color="var(--accent-primary)" />
                Shared Blackboard State
              </div>
              <div
                style={{
                  background: "rgba(0,0,0,0.35)",
                  padding: "12px",
                  borderRadius: "8px",
                  fontFamily: "monospace",
                  fontSize: "0.78rem",
                  color: "#cbd5e1",
                  maxHeight: "180px",
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                }}
              >
                {JSON.stringify(swarmResult.blackboard, null, 2)}
              </div>
            </div>

            {/* Consensus Verification Notes */}
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                <FileCheck size={16} color="var(--status-success)" />
                Cross-Agent Consensus Verification
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {swarmResult.consensus_notes.map((note, idx) => (
                  <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    <CheckCircle2 size={14} color="var(--status-success)" style={{ marginTop: "2px", flexShrink: 0 }} />
                    <span>{note}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Final Executive Synthesis Card */}
          <div
            style={{
              background: "linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(16, 185, 129, 0.08))",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              borderRadius: "12px",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Sparkles size={18} color="var(--accent-primary)" />
                <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>Executive Synthesis Resolution</span>
              </div>
              <button
                onClick={copySynthesis}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border-color)",
                  color: "var(--text-secondary)",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                {copied ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
                <span>{copied ? "Copied!" : "Copy Synthesis"}</span>
              </button>
            </div>

            <p style={{ fontSize: "0.92rem", lineHeight: 1.6, color: "var(--text-primary)", margin: 0 }}>
              {swarmResult.final_synthesis}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
