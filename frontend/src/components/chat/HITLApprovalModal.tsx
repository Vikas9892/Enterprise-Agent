"use client";

import React, { useState } from "react";
import { AgentSession } from "@/lib/types";
import { resumeAgentSession } from "@/lib/api";
import { AlertTriangle, Check, X, ShieldAlert, Loader2 } from "lucide-react";

interface HITLApprovalModalProps {
  session: AgentSession;
  onResolved: (updatedSession: AgentSession) => void;
}

export default function HITLApprovalModal({ session, onResolved }: HITLApprovalModalProps) {
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDecision = async (approved: boolean) => {
    setIsSubmitting(true);
    try {
      const updated = await resumeAgentSession(session.session_id, approved, feedback);
      onResolved(updated);
    } catch (err) {
      console.error("Failed to submit approval:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const actionDetails = session.pending_action?.details || {};
  const reason = actionDetails.reason || "Action exceeds automated compliance limits and requires human sign-off.";
  const approver = actionDetails.recommended_approver || "Operations Supervisor";

  return (
    <div
      style={{
        marginTop: "16px",
        padding: "18px 20px",
        borderRadius: "var(--radius-lg)",
        background: "linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%)",
        border: "1px solid rgba(245, 158, 11, 0.4)",
        boxShadow: "var(--glow-warning)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
        <ShieldAlert size={20} color="var(--status-warning)" />
        <h3 style={{ fontSize: "1rem", color: "var(--status-warning)", fontWeight: 700 }}>
          Human-In-The-Loop Approval Required
        </h3>
      </div>

      <p style={{ fontSize: "0.88rem", color: "var(--text-primary)", marginBottom: "12px", lineHeight: 1.5 }}>
        {reason}
      </p>

      <div
        style={{
          display: "flex",
          gap: "16px",
          padding: "8px 12px",
          background: "rgba(0, 0, 0, 0.3)",
          borderRadius: "var(--radius-sm)",
          fontSize: "0.78rem",
          marginBottom: "14px",
          border: "1px solid rgba(255, 255, 255, 0.05)",
        }}
      >
        <div>
          <span style={{ color: "var(--text-muted)" }}>Target Action: </span>
          <span className="font-mono" style={{ color: "#fef08a", fontWeight: 600 }}>
            {session.pending_action?.tool || "Sensitive Operation"}
          </span>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Recommended Sign-off: </span>
          <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{approver}</span>
        </div>
      </div>

      {/* Optional feedback notes */}
      <div style={{ marginBottom: "14px" }}>
        <label
          htmlFor="hitl-feedback-input"
          style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "6px" }}
        >
          Supervisor Steering Feedback (Optional):
        </label>
        <input
          id="hitl-feedback-input"
          type="text"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="e.g. Verified customer RMA documents. Approved."
          disabled={isSubmitting}
          style={{
            width: "100%",
            padding: "8px 12px",
            background: "rgba(0, 0, 0, 0.4)",
            border: "1px solid var(--border-medium)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
          }}
        />
      </div>

      {/* Action Buttons */}
      <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
        <button
          onClick={() => handleDecision(false)}
          disabled={isSubmitting}
          className="btn-danger"
          style={{ padding: "8px 16px", fontSize: "0.85rem" }}
        >
          {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : <X size={15} />}
          <span>Reject Action</span>
        </button>

        <button
          onClick={() => handleDecision(true)}
          disabled={isSubmitting}
          className="btn-primary"
          style={{
            background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
            boxShadow: "0 4px 14px rgba(16, 185, 129, 0.4)",
            padding: "8px 18px",
            fontSize: "0.85rem",
          }}
        >
          {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : <Check size={15} />}
          <span>Approve Action</span>
        </button>
      </div>
    </div>
  );
}
