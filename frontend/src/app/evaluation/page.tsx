"use client";

import React, { useState, useEffect } from "react";
import { BenchmarkReport, EvalDataset } from "@/lib/types";
import { fetchEvaluationDatasets, triggerBenchmarkRun } from "@/lib/api";
import { Award, Play, CheckCircle2, XCircle, Clock, ShieldCheck, Wrench, FileText, Loader2, Sparkles } from "lucide-react";

export default function EvaluationPage() {
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("customer_support_eval");
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    async function load() {
      const data = await fetchEvaluationDatasets();
      setDatasets(data);
    }
    load();
  }, []);

  const handleRun = async () => {
    setIsRunning(true);
    try {
      const res = await triggerBenchmarkRun(selectedDatasetId);
      setReport(res);
    } catch (err) {
      console.error("Benchmark failed:", err);
    } finally {
      setIsRunning(false);
    }
  };

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId) || datasets[0];

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
            Agent Evaluation & Benchmarking Suites
          </h2>
          <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            Execute automated offline evaluation suites scoring factual accuracy, tool precision, safety, and HITL governance.
          </p>
        </div>

        <button
          onClick={handleRun}
          disabled={isRunning}
          className="btn-primary"
          style={{ padding: "10px 22px" }}
        >
          {isRunning ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          <span>{isRunning ? "Running Suite..." : "Run Benchmark Suite"}</span>
        </button>
      </div>

      {/* Dataset Selection Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "16px",
        }}
      >
        {datasets.map((d) => {
          const isSelected = d.id === selectedDatasetId;
          return (
            <div
              key={d.id}
              onClick={() => setSelectedDatasetId(d.id)}
              className="glass-card"
              style={{
                cursor: "pointer",
                borderColor: isSelected ? "#6366f1" : "var(--border-subtle)",
                background: isSelected ? "var(--brand-gradient-subtle)" : "var(--bg-card)",
                transition: "all 0.2s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    color: isSelected ? "#a5b4fc" : "var(--text-muted)",
                  }}
                >
                  {d.category}
                </span>
                {isSelected && (
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: "var(--radius-full)",
                      background: "rgba(99, 102, 241, 0.2)",
                      color: "#c7d2fe",
                      fontSize: "0.7rem",
                      fontWeight: 700,
                    }}
                  >
                    Selected
                  </span>
                )}
              </div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 700, marginBottom: "6px" }}>{d.name}</h3>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>{d.description}</p>
            </div>
          );
        })}
      </div>

      {/* Benchmark Report Card */}
      {report ? (
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                <Award size={22} color="#818cf8" />
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>{report.dataset_name} — Results</h3>
              </div>
              <span className="font-mono" style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                ID: {report.benchmark_id} • Executed at: {new Date(report.created_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Overall Score Dial */}
            <div style={{ display: "flex", gap: "24px", alignItems: "center" }}>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Pass Rate</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--status-success)" }}>
                  {report.pass_rate}%
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Mean Score</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "#818cf8" }}>
                  {(report.mean_score * 100).toFixed(1)}%
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Avg Latency</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  {report.mean_latency_seconds}s
                </div>
              </div>
            </div>
          </div>

          {/* Test Case Breakdown Table */}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left", color: "var(--text-muted)" }}>
                  <th style={{ padding: "10px 14px" }}>Scenario</th>
                  <th style={{ padding: "10px 14px" }}>Outcome</th>
                  <th style={{ padding: "10px 14px" }}>Compound Score</th>
                  <th style={{ padding: "10px 14px" }}>Tools Executed</th>
                  <th style={{ padding: "10px 14px" }}>Duration</th>
                </tr>
              </thead>
              <tbody>
                {report.results.map((r, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      background: idx % 2 === 0 ? "transparent" : "rgba(255, 255, 255, 0.01)",
                    }}
                  >
                    <td style={{ padding: "12px 14px" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{r.test_id}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {r.actual_final_answer || "Completed analysis."}
                      </div>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      {r.passed ? (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            padding: "2px 8px",
                            borderRadius: "var(--radius-full)",
                            background: "var(--status-success-bg)",
                            color: "var(--status-success)",
                            fontWeight: 700,
                            fontSize: "0.75rem",
                          }}
                        >
                          <CheckCircle2 size={12} /> PASSED
                        </span>
                      ) : (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            padding: "2px 8px",
                            borderRadius: "var(--radius-full)",
                            background: "var(--status-danger-bg)",
                            color: "var(--status-danger)",
                            fontWeight: 700,
                            fontSize: "0.75rem",
                          }}
                        >
                          <XCircle size={12} /> FAILED
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span className="font-mono" style={{ fontWeight: 700, color: "#a5b4fc" }}>
                        {(r.score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                        {r.actual_tools_called.map((t) => (
                          <span
                            key={t}
                            className="font-mono"
                            style={{
                              padding: "2px 6px",
                              borderRadius: "var(--radius-sm)",
                              background: "rgba(255, 255, 255, 0.04)",
                              fontSize: "0.72rem",
                              color: "var(--text-secondary)",
                            }}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span className="font-mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {r.latency_seconds}s
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div
          className="glass-card"
          style={{
            padding: "48px",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
          }}
        >
          <Award size={40} color="#6366f1" style={{ opacity: 0.6 }} />
          <h3 style={{ fontSize: "1.1rem" }}>No Benchmark Run Executed Yet</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", maxWidth: "480px" }}>
            Select one of the standard benchmark datasets above and click &quot;Run Benchmark Suite&quot; to evaluate the agent orchestrator across accuracy, tool recall, and safety.
          </p>
        </div>
      )}
    </div>
  );
}
