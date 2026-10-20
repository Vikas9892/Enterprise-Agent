"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Activity,
  Award,
  Terminal,
  Layers,
  Cpu,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  Network,
  ShieldCheck,
  Workflow,
  Sparkles,
} from "lucide-react";
import { checkBackendHealth } from "@/lib/api";

interface NavGroup {
  label: string;
  items: Array<{
    name: string;
    href: string;
    icon: React.ElementType;
    badge?: string;
  }>;
}

export default function SidebarNav() {
  const pathname = usePathname();
  const [healthStatus, setHealthStatus] = useState<"online" | "offline" | "checking">("checking");
  const [latencyMs, setLatencyMs] = useState<number>(0);

  useEffect(() => {
    async function updateHealth() {
      const { status, latency_ms } = await checkBackendHealth();
      setHealthStatus(status as "online" | "offline");
      setLatencyMs(latency_ms);
    }
    updateHealth();
    const interval = setInterval(updateHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const navGroups: NavGroup[] = [
    {
      label: "AGENT ORCHESTRATION",
      items: [
        { name: "Agent Chat", href: "/", icon: Bot },
        { name: "Agent Swarm", href: "/swarm", icon: Network, badge: "Swarm" },
      ],
    },
    {
      label: "ENTERPRISE INTELLIGENCE",
      items: [
        { name: "Knowledge & RAG", href: "/knowledge", icon: BookOpen, badge: "Hybrid" },
      ],
    },
    {
      label: "OBSERVABILITY & QUALITY",
      items: [
        { name: "Observability", href: "/observability", icon: Activity },
        { name: "Evaluation & Benchmarks", href: "/evaluation", icon: Award },
      ],
    },
    {
      label: "ENTERPRISE GOVERNANCE",
      items: [
        { name: "Enterprise Admin", href: "/admin", icon: ShieldCheck, badge: "RBAC" },
      ],
    },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        </div>
        <div>
          <div className="brand-title">EnterpriseAgent</div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
            <span className="brand-badge">v0.2.0</span>
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Platform Core</span>
          </div>
        </div>
      </div>

      {/* Navigation Sections */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px", marginTop: "14px" }}>
        {navGroups.map((group) => (
          <div key={group.label}>
            <div
              style={{
                fontSize: "0.68rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                letterSpacing: "0.06em",
                padding: "4px 12px",
                marginBottom: "4px",
              }}
            >
              {group.label}
            </div>

            <nav className="sidebar-nav" style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`nav-link ${isActive ? "active" : ""}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <Icon size={17} />
                      <span style={{ fontSize: "0.85rem", fontWeight: isActive ? 600 : 500 }}>{item.name}</span>
                    </div>
                    {item.badge && (
                      <span
                        style={{
                          fontSize: "0.65rem",
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: "4px",
                          background: isActive ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.06)",
                          color: isActive ? "#fff" : "var(--text-muted)",
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Footer Backend Status Card */}
      <div className="sidebar-footer">
        <div className="backend-status-card">
          <div className="status-indicator">
            {healthStatus === "online" ? (
              <div className="pulse-dot" />
            ) : (
              <AlertCircle size={12} color="var(--status-warning)" />
            )}
            <span style={{ fontWeight: 600, color: healthStatus === "online" ? "var(--status-success)" : "var(--status-warning)" }}>
              {healthStatus === "online" ? "FastAPI Online" : "Backend Standby"}
            </span>
          </div>
          <span className="font-mono" style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
            {latencyMs}ms
          </span>
        </div>

        <div style={{ padding: "4px 8px", fontSize: "0.7rem", color: "var(--text-muted)", textAlign: "center" }}>
          PostgreSQL 16 • Redis 7 • MCP 8001
        </div>
      </div>
    </aside>
  );
}
