"use client";

import React, { useState, useEffect, useRef } from "react";
import { AgentSession, ChatMessage, Persona } from "@/lib/types";
import { executeAgentTask, fetchPersonas, FALLBACK_PERSONAS } from "@/lib/api";
import StepTraceViewer from "./StepTraceViewer";
import HITLApprovalModal from "./HITLApprovalModal";
import PersonaSelectorModal from "./PersonaSelectorModal";
import { Send, Bot, User, Sparkles, RefreshCw, Layers, ShieldAlert, CheckCircle2, ArrowRight } from "lucide-react";

export default function ChatInterface() {
  const [personas, setPersonas] = useState<Persona[]>(FALLBACK_PERSONAS);
  const [activePersonaId, setActivePersonaId] = useState<string>("coordinator");
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-msg",
      role: "assistant",
      content:
        "Greetings! I am the Enterprise Autonomous Agent Orchestrator. Select a specialized persona or try one of the operational scenarios below to dispatch tool-augmented workflows with cyclical self-reflection.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      const data = await fetchPersonas();
      setPersonas(data);
    }
    load();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const activePersona = personas.find((p) => p.id === activePersonaId) || personas[0];

  const quickPrompts = [
    { label: "Apex Customer Lookup", query: "Please look up customer profile for Apex Global Logistics" },
    { label: "Track Freight & Inventory", query: "Verify shipment for order ORD-2026-9001 and check inventory for SKU-SRV-01" },
    { label: "Large Refund (HITL Test)", query: "Request a refund of 1500 for damaged shipment items" },
    { label: "Ticket Triage", query: "Triage support ticket TCK-8801 for customer issue" },
  ];

  const handleSend = async (queryToSend?: string) => {
    const text = (queryToSend || inputValue).trim();
    if (!text || isLoading) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    try {
      const session = await executeAgentTask(text, activePersonaId);

      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        role: "assistant",
        content: session.final_answer || (session.status === "waiting_for_human"
          ? "Execution paused at Human-In-The-Loop checkpoint: Sensitive enterprise operation requires supervisor authorization."
          : "Task completed successfully."),
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        session,
      };

      setMessages((prev) => [...prev, agentMsg]);
    } catch (err) {
      console.error("Agent execution error:", err);
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        content: "An operational error occurred while executing the state machine graph. Please check backend connectivity.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSessionUpdated = (updatedSession: AgentSession, messageId: string) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === messageId) {
          return {
            ...msg,
            content: updatedSession.final_answer || msg.content,
            session: updatedSession,
          };
        }
        return msg;
      })
    );
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        position: "relative",
        background: "radial-gradient(ellipse at top, rgba(99, 102, 241, 0.05) 0%, transparent 70%)",
      }}
    >
      {/* Top Context Subheader */}
      <div
        style={{
          padding: "12px 28px",
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(10, 15, 26, 0.4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Current Persona:</span>
          <button
            onClick={() => setIsPersonaModalOpen(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              background: "rgba(99, 102, 241, 0.15)",
              border: "1px solid rgba(99, 102, 241, 0.4)",
              borderRadius: "var(--radius-sm)",
              color: "#c7d2fe",
              fontSize: "0.82rem",
              fontWeight: 600,
            }}
          >
            <span>{activePersona.name}</span>
            <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>▼</span>
          </button>
        </div>

        <button
          onClick={() => {
            setMessages([
              {
                id: "welcome-reset",
                role: "assistant",
                content: "Workspace cleared. Ready for next enterprise operational inquiry.",
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            color: "var(--text-muted)",
            fontSize: "0.8rem",
            padding: "4px 8px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <RefreshCw size={12} />
          <span>Reset Session</span>
        </button>
      </div>

      {/* Messages Timeline */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px 28px",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              style={{
                display: "flex",
                gap: "14px",
                alignSelf: isUser ? "flex-end" : "flex-start",
                maxWidth: isUser ? "75%" : "85%",
              }}
            >
              {!isUser && (
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    background: "var(--brand-gradient)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    boxShadow: "0 0 12px rgba(99, 102, 241, 0.3)",
                    color: "white",
                  }}
                >
                  <Bot size={20} />
                </div>
              )}

              <div style={{ flex: 1 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    marginBottom: "4px",
                    justifyContent: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                    {isUser ? "You" : activePersona.name}
                  </span>
                  <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{msg.timestamp}</span>
                </div>

                <div
                  style={{
                    padding: "14px 18px",
                    borderRadius: isUser ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                    background: isUser
                      ? "linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)"
                      : "rgba(17, 24, 39, 0.75)",
                    border: isUser ? "1px solid rgba(129, 140, 248, 0.4)" : "1px solid var(--border-subtle)",
                    backdropFilter: "blur(12px)",
                    boxShadow: isUser ? "0 4px 14px rgba(79, 70, 229, 0.3)" : "var(--shadow-sm)",
                    color: "var(--text-primary)",
                    fontSize: "0.92rem",
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.content}

                  {/* If Human-In-The-Loop approval is needed */}
                  {msg.session && msg.session.requires_human_approval && (
                    <HITLApprovalModal
                      session={msg.session}
                      onResolved={(updated) => handleSessionUpdated(updated, msg.id)}
                    />
                  )}

                  {/* State machine node trace inspector */}
                  {msg.session && <StepTraceViewer session={msg.session} />}
                </div>
              </div>

              {isUser && (
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    background: "rgba(255, 255, 255, 0.1)",
                    border: "1px solid var(--border-medium)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    color: "var(--text-primary)",
                  }}
                >
                  <User size={18} />
                </div>
              )}
            </div>
          );
        })}

        {/* Live reasoning spinner indicator */}
        {isLoading && (
          <div style={{ display: "flex", gap: "14px", alignSelf: "flex-start", maxWidth: "80%" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-md)",
                background: "var(--brand-gradient)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                color: "white",
              }}
            >
              <Bot size={20} />
            </div>
            <div
              style={{
                padding: "12px 18px",
                borderRadius: "4px 16px 16px 16px",
                background: "rgba(17, 24, 39, 0.75)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                color: "var(--text-secondary)",
                fontSize: "0.85rem",
              }}
            >
              <div className="pulse-dot" />
              <span>Agent is deconstructing plan and querying enterprise tools...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar */}
      <div
        style={{
          padding: "8px 28px",
          display: "flex",
          gap: "8px",
          overflowX: "auto",
          background: "rgba(7, 9, 14, 0.8)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(p.query)}
            disabled={isLoading}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-full)",
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              fontSize: "0.78rem",
              whiteSpace: "nowrap",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "all 0.15s ease",
            }}
            onMouseOver={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(99, 102, 241, 0.5)";
              (e.currentTarget as HTMLElement).style.color = "var(--text-primary)";
            }}
            onMouseOut={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "var(--border-subtle)";
              (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)";
            }}
          >
            <Sparkles size={12} color="#818cf8" />
            <span>{p.label}</span>
          </button>
        ))}
      </div>

      {/* Input Composer */}
      <div
        style={{
          padding: "16px 28px 24px",
          background: "rgba(7, 9, 14, 0.95)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            background: "rgba(17, 24, 39, 0.9)",
            border: "1px solid var(--border-medium)",
            borderRadius: "var(--radius-lg)",
            padding: "8px 12px 8px 18px",
            boxShadow: "var(--shadow-md)",
            transition: "border-color 0.2s ease",
          }}
        >
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={`Instruct ${activePersona.name} (e.g. 'Look up customer profile for Apex Global')...`}
            disabled={isLoading}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              color: "var(--text-primary)",
              fontSize: "0.95rem",
              outline: "none",
            }}
          />

          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="btn-primary"
            style={{ padding: "8px 16px", borderRadius: "var(--radius-md)" }}
          >
            <span>Execute</span>
            <Send size={15} />
          </button>
        </form>
      </div>

      {/* Persona Selector Modal */}
      {isPersonaModalOpen && (
        <PersonaSelectorModal
          personas={personas}
          selectedId={activePersonaId}
          onSelect={(id) => setActivePersonaId(id)}
          onClose={() => setIsPersonaModalOpen(false)}
        />
      )}
    </div>
  );
}
