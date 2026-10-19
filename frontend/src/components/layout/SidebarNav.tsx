"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Activity, Award, Terminal, Layers, Cpu, CheckCircle2, AlertCircle, BookOpen } from "lucide-react";
import { checkBackendHealth } from "@/lib/api";

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

  const navItems = [
    { name: "Agent Chat", href: "/", icon: Bot },
    { name: "Knowledge & RAG", href: "/knowledge", icon: BookOpen },
    { name: "Observability", href: "/observability", icon: Activity },
    { name: "Evaluation & Benchmarks", href: "/evaluation", icon: Award },
  ];


  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <Cpu size={22} />
        </div>
        <div>
          <div className="brand-title">EnterpriseAgent</div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
            <span className="brand-badge">v0.1.0</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Platform</span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`nav-link ${isActive ? "active" : ""}`}
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Backend Status */}
      <div className="sidebar-footer">
        <div className="backend-status-card">
          <div className="status-indicator">
            {healthStatus === "online" ? (
              <div className="pulse-dot" />
            ) : (
              <AlertCircle size={12} color="var(--status-warning)" />
            )}
            <span style={{ fontWeight: 600, color: healthStatus === "online" ? "var(--status-success)" : "var(--status-warning)" }}>
              {healthStatus === "online" ? "Backend Online" : "Backend Standby"}
            </span>
          </div>
          <span className="font-mono" style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
            {latencyMs}ms
          </span>
        </div>

        <div style={{ padding: "4px 8px", fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
          Enterprise Agentic AI Platform
        </div>
      </div>
    </aside>
  );
}
