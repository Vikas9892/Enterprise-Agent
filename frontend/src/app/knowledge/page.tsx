"use client";

import React, { useState, useEffect } from "react";
import {
  BookOpen,
  Search,
  Sliders,
  PlusCircle,
  FileText,
  Layers,
  Sparkles,
  CheckCircle2,
  Bookmark,
  Share2,
  Trash2,
  ShieldCheck,
  Tag,
  Loader2,
} from "lucide-react";
import {
  fetchKnowledgeDocuments,
  queryKnowledge,
  ingestKnowledgeDocument,
  KnowledgeDoc,
  KnowledgeQueryResponse,
  KnowledgeSearchResult,
} from "@/lib/api";

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<"search" | "documents" | "ingest">("search");
  const [documents, setDocuments] = useState<KnowledgeDoc[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // Search state
  const [query, setQuery] = useState("enterprise refund policy for damaged shipment");
  const [alpha, setAlpha] = useState<number>(0.5);
  const [useMmr, setUseMmr] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResponse, setSearchResponse] = useState<KnowledgeQueryResponse | null>(null);

  // Ingestion form state
  const [docTitle, setDocTitle] = useState("");
  const [docCategory, setDocCategory] = useState("finance");
  const [docContent, setDocContent] = useState("");
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoadingDocs(true);
      const docs = await fetchKnowledgeDocuments();
      setDocuments(docs);
      setLoadingDocs(false);
    }
    load();
    handleSearch();
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const res = await queryKnowledge(query, {
        alpha,
        use_mmr: useMmr,
        category: selectedCategory === "all" ? undefined : selectedCategory,
      });
      setSearchResponse(res);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docTitle.trim() || !docContent.trim()) return;
    setIsIngesting(true);
    setIngestSuccess(null);
    try {
      const newDoc = await ingestKnowledgeDocument({
        title: docTitle,
        category: docCategory,
        content: docContent,
      });
      if (newDoc) {
        setDocuments((prev) => [newDoc, ...prev]);
        setIngestSuccess(`Successfully indexed "${docTitle}" (${newDoc.chunk_count} chunks created)`);
        setDocTitle("");
        setDocContent("");
      }
    } catch (err) {
      console.error("Ingestion failed:", err);
    } finally {
      setIsIngesting(false);
    }
  };

  const loadSampleDoc = () => {
    setDocTitle("Datacenter High-Availability & Disaster Recovery Runbook");
    setDocCategory("infrastructure");
    setDocContent(
      "# Datacenter High-Availability SLA\n\n" +
        "## 1. Failover Protocols\n" +
        "When health probes detect primary cluster node packet loss exceeding 5% for 60 seconds, " +
        "the automated supervisor initiates geo-redundant traffic rerouting to secondary cold standby pods in us-east-2.\n\n" +
        "## 2. Recovery Time Objective (RTO)\n" +
        "The mandated RTO for Tier-1 mission-critical customer databases is strictly 120 seconds. " +
        "Backups are verified with SHA-256 checksums and automated restore validation drills."
    );
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
      {/* Top Banner */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "4px", display: "flex", alignItems: "center", gap: "10px" }}>
            <BookOpen size={24} color="var(--accent-primary)" />
            Enterprise Knowledge Base & Hybrid RAG
          </h2>
          <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            Dense semantic embeddings combined with sparse BM25 keyword matching via Reciprocal Rank Fusion (RRF) and Maximal Marginal Relevance.
          </p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: "flex", background: "var(--bg-card)", padding: "4px", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
          <button
            onClick={() => setActiveTab("search")}
            className={`btn-secondary ${activeTab === "search" ? "active" : ""}`}
            style={{
              padding: "6px 14px",
              fontSize: "0.85rem",
              background: activeTab === "search" ? "var(--accent-primary)" : "transparent",
              color: activeTab === "search" ? "#fff" : "var(--text-secondary)",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            Hybrid Search
          </button>
          <button
            onClick={() => setActiveTab("documents")}
            className={`btn-secondary ${activeTab === "documents" ? "active" : ""}`}
            style={{
              padding: "6px 14px",
              fontSize: "0.85rem",
              background: activeTab === "documents" ? "var(--accent-primary)" : "transparent",
              color: activeTab === "documents" ? "#fff" : "var(--text-secondary)",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            Documents ({documents.length})
          </button>
          <button
            onClick={() => setActiveTab("ingest")}
            className={`btn-secondary ${activeTab === "ingest" ? "active" : ""}`}
            style={{
              padding: "6px 14px",
              fontSize: "0.85rem",
              background: activeTab === "ingest" ? "var(--accent-primary)" : "transparent",
              color: activeTab === "ingest" ? "#fff" : "var(--text-secondary)",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            + Ingest New Doc
          </button>
        </div>
      </div>

      {/* TAB 1: HYBRID SEARCH */}
      {activeTab === "search" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Query Bar & Controls */}
          <div
            style={{
              background: "var(--bg-card)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", gap: "12px" }}>
              <div style={{ flex: 1, position: "relative" }}>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="Ask a question or enter keywords to retrieve enterprise policies and specs..."
                  style={{
                    width: "100%",
                    padding: "12px 16px 12px 42px",
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    color: "var(--text-primary)",
                    fontSize: "0.95rem",
                  }}
                />
                <Search
                  size={18}
                  style={{
                    position: "absolute",
                    left: "14px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--text-muted)",
                  }}
                />
              </div>

              <button
                onClick={handleSearch}
                disabled={isSearching}
                style={{
                  padding: "0 22px",
                  background: "var(--accent-primary)",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                {isSearching ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
                Search
              </button>
            </div>

            {/* Retrieval Tuning Controls */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: "20px",
                background: "rgba(255,255,255,0.02)",
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid rgba(255,255,255,0.05)",
                alignItems: "center",
              }}
            >
              {/* Alpha slider */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  <span>Lexical BM25 (0.0)</span>
                  <span style={{ fontWeight: 600, color: "var(--accent-primary)" }}>Alpha: {alpha}</span>
                  <span>Dense Vector (1.0)</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={alpha}
                  onChange={(e) => setAlpha(parseFloat(e.target.value))}
                  style={{ width: "100%", accentColor: "var(--accent-primary)", cursor: "pointer" }}
                />
              </div>

              {/* Category selector */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Category:</span>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  style={{
                    padding: "6px 12px",
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    color: "var(--text-primary)",
                    fontSize: "0.85rem",
                    flex: 1,
                  }}
                >
                  <option value="all">All Domains</option>
                  <option value="finance">Finance & Refunds</option>
                  <option value="logistics">Logistics & Shipping</option>
                  <option value="compliance">Compliance & GDPR</option>
                  <option value="infrastructure">Infrastructure</option>
                </select>
              </div>

              {/* MMR Toggle */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px", justifyContent: "flex-end" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  <input
                    type="checkbox"
                    checked={useMmr}
                    onChange={(e) => setUseMmr(e.target.checked)}
                    style={{ accentColor: "var(--accent-primary)", width: "16px", height: "16px" }}
                  />
                  <span>MMR Diversity Re-ranking</span>
                </label>
              </div>
            </div>
          </div>

          {/* Results Display */}
          {searchResponse && (
            <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "20px" }}>
              {/* Passages List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Sparkles size={16} color="var(--accent-primary)" />
                  Retrieved Passages ({searchResponse.results.length})
                </div>

                {searchResponse.results.map((res: KnowledgeSearchResult, idx: number) => (
                  <div
                    key={res.chunk_id || idx}
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
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            background: "rgba(99, 102, 241, 0.15)",
                            color: "var(--accent-primary)",
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "4px",
                          }}
                        >
                          #{idx + 1}
                        </span>
                        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{res.title}</span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "0.72rem",
                            textTransform: "uppercase",
                            padding: "2px 8px",
                            borderRadius: "4px",
                            fontWeight: 600,
                            background:
                              res.match_type === "hybrid"
                                ? "rgba(16, 185, 129, 0.15)"
                                : res.match_type === "vector"
                                ? "rgba(139, 92, 246, 0.15)"
                                : "rgba(245, 158, 11, 0.15)",
                            color:
                              res.match_type === "hybrid"
                                ? "#10b981"
                                : res.match_type === "vector"
                                ? "#a78bfa"
                                : "#f59e0b",
                          }}
                        >
                          {res.match_type}
                        </span>
                        <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--status-success)" }}>
                          {(res.score * 100).toFixed(1)}% match
                        </span>
                      </div>
                    </div>

                    <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                      {res.content}
                    </p>

                    <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {res.metadata?.category && (
                        <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <Tag size={12} /> {res.metadata.category}
                        </span>
                      )}
                      {res.citation && <span>{res.citation}</span>}
                    </div>
                  </div>
                ))}
              </div>

              {/* Grounded Context Block */}
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "10px",
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  height: "fit-content",
                }}
              >
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
                  <ShieldCheck size={16} color="var(--status-success)" />
                  Grounded LLM Prompt Context
                </div>

                <div
                  style={{
                    background: "rgba(0,0,0,0.4)",
                    padding: "12px",
                    borderRadius: "8px",
                    fontSize: "0.78rem",
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                    color: "#cbd5e1",
                    maxHeight: "380px",
                    overflowY: "auto",
                    lineHeight: 1.45,
                  }}
                >
                  {searchResponse.grounded_context}
                </div>

                <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "10px" }}>
                  <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Attribution Footnotes:</span>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "6px" }}>
                    {searchResponse.citations.map((c) => (
                      <div key={c.index} style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        <span style={{ fontWeight: 600, color: "var(--accent-primary)" }}>[{c.index}]</span> {c.title} (Score: {c.score})
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: DOCUMENTS CATALOG */}
      {activeTab === "documents" && (
        <div
          style={{
            background: "var(--bg-card)",
            borderRadius: "12px",
            border: "1px solid var(--border-color)",
            padding: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Indexed Enterprise Knowledge Corpus</h3>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{documents.length} Total Documents</span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)", textAlign: "left" }}>
                  <th style={{ padding: "10px 14px" }}>Title</th>
                  <th style={{ padding: "10px 14px" }}>Category</th>
                  <th style={{ padding: "10px 14px" }}>Format</th>
                  <th style={{ padding: "10px 14px" }}>Chunks</th>
                  <th style={{ padding: "10px 14px" }}>Tenant</th>
                  <th style={{ padding: "10px 14px" }}>Source</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.document_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                    <td style={{ padding: "12px 14px", fontWeight: 600, color: "var(--text-primary)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <FileText size={16} color="var(--accent-primary)" />
                        {doc.title}
                      </div>
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span
                        style={{
                          background: "rgba(255,255,255,0.06)",
                          padding: "3px 8px",
                          borderRadius: "4px",
                          fontSize: "0.78rem",
                          textTransform: "capitalize",
                        }}
                      >
                        {doc.metadata?.category || "general"}
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                      {doc.content_type}
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span style={{ fontWeight: 600, color: "var(--status-success)" }}>{doc.chunk_count}</span>
                    </td>
                    <td style={{ padding: "12px 14px", color: "var(--text-secondary)" }}>
                      {doc.metadata?.tenant_id || "default"}
                    </td>
                    <td style={{ padding: "12px 14px", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                      {doc.metadata?.source || "direct"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: INGEST PORTAL */}
      {activeTab === "ingest" && (
        <div
          style={{
            background: "var(--bg-card)",
            borderRadius: "12px",
            border: "1px solid var(--border-color)",
            padding: "24px",
            maxWidth: "800px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <PlusCircle size={20} color="var(--accent-primary)" /> Ingest & Index New Document
            </h3>
            <button
              onClick={loadSampleDoc}
              style={{
                fontSize: "0.78rem",
                color: "var(--accent-primary)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Fill Sample Runbook
            </button>
          </div>

          {ingestSuccess && (
            <div
              style={{
                padding: "12px 16px",
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "var(--status-success)",
                borderRadius: "8px",
                fontSize: "0.85rem",
                marginBottom: "16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <CheckCircle2 size={16} /> {ingestSuccess}
            </div>
          )}

          <form onSubmit={handleIngest} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Document Title
                </label>
                <input
                  type="text"
                  required
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="e.g. Enterprise Security Governance Policy"
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    color: "var(--text-primary)",
                    fontSize: "0.9rem",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Domain Category
                </label>
                <select
                  value={docCategory}
                  onChange={(e) => setDocCategory(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    color: "var(--text-primary)",
                    fontSize: "0.9rem",
                  }}
                >
                  <option value="finance">Finance</option>
                  <option value="logistics">Logistics</option>
                  <option value="compliance">Compliance</option>
                  <option value="infrastructure">Infrastructure</option>
                  <option value="general">General</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
                Markdown / Text Content (will be decomposed into semantic chunks)
              </label>
              <textarea
                required
                rows={10}
                value={docContent}
                onChange={(e) => setDocContent(e.target.value)}
                placeholder="Paste markdown content, procedures, policies, or technical specifications here..."
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  background: "rgba(0,0,0,0.3)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "6px",
                  color: "var(--text-primary)",
                  fontSize: "0.85rem",
                  fontFamily: "monospace",
                  lineHeight: 1.45,
                }}
              />
            </div>

            <button
              type="submit"
              disabled={isIngesting}
              style={{
                padding: "12px 24px",
                background: "var(--accent-primary)",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
              }}
            >
              {isIngesting ? <Loader2 size={16} className="spin" /> : <PlusCircle size={16} />}
              Ingest & Generate Embeddings
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
