"use client";

import React from "react";
import { Persona } from "@/lib/types";
import { X, Check, Shield, Wrench, Sparkles, UserCheck } from "lucide-react";

interface PersonaSelectorModalProps {
  personas: Persona[];
  selectedId: string;
  onSelect: (personaId: string) => void;
  onClose: () => void;
}

export default function PersonaSelectorModal({
  personas,
  selectedId,
  onSelect,
  onClose,
}: PersonaSelectorModalProps) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        background: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "600px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-medium)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-lg)",
          padding: "24px",
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Sparkles size={20} color="#818cf8" />
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Select Operational Persona</h2>
          </div>
          <button
            onClick={onClose}
            style={{
              color: "var(--text-muted)",
              padding: "4px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "20px" }}>
          Specialized personas constrain the state machine's tool execution boundaries and apply domain-tailored system instructions.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {personas.map((p) => {
            const isSelected = p.id === selectedId;
            return (
              <div
                key={p.id}
                onClick={() => {
                  onSelect(p.id);
                  onClose();
                }}
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  border: isSelected ? "1px solid #6366f1" : "1px solid var(--border-subtle)",
                  background: isSelected ? "var(--brand-gradient-subtle)" : "rgba(255, 255, 255, 0.02)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.95rem" }}>
                      {p.name}
                    </span>
                    <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      ({p.id})
                    </span>
                  </div>
                  {isSelected && (
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        color: "#a5b4fc",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                      }}
                    >
                      <Check size={14} /> Active
                    </span>
                  )}
                </div>

                <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "10px", lineHeight: 1.4 }}>
                  {p.role_description}
                </p>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {p.recommended_tools.map((tool) => (
                    <span
                      key={tool}
                      className="font-mono"
                      style={{
                        padding: "2px 8px",
                        borderRadius: "var(--radius-sm)",
                        background: "rgba(255, 255, 255, 0.04)",
                        border: "1px solid var(--border-subtle)",
                        fontSize: "0.7rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
