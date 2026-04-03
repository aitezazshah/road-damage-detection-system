"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from "recharts";
import dynamic from "next/dynamic";
import { formatDistanceToNow, format } from "date-fns";

// Dynamically import map to avoid SSR issues
const MapComponent = dynamic(() => import("./MapComponent"), { ssr: false });

// ─── CONSTANTS ──────────────────────────────────────────────
const URGENCY_ORDER = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3, NORMAL: 4 };
const URGENCY_COLORS = {
  URGENT: "#dc2626",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
  NORMAL: "#64748b",
};
const URGENCY_BG = {
  URGENT: "#450a0a",
  HIGH: "#431407",
  MEDIUM: "#422006",
  LOW: "#052e16",
  NORMAL: "#1e293b",
};
const URGENCY_ICONS = {
  URGENT: "🚨",
  HIGH: "🔴",
  MEDIUM: "🟠",
  LOW: "🟡",
  NORMAL: "✅",
};

// ─── HELPERS ────────────────────────────────────────────────
function UrgencyBadge({ u }) {
  return (
    <span
      style={{
        background: URGENCY_BG[u] || "#1e293b",
        color: URGENCY_COLORS[u] || "#64748b",
        border: `1px solid ${URGENCY_COLORS[u]}44`,
        padding: "0.2rem 0.65rem",
        borderRadius: "999px",
        fontSize: "0.72rem",
        fontFamily: "DM Mono, monospace",
        fontWeight: 600,
        letterSpacing: "0.06em",
        display: "inline-flex",
        alignItems: "center",
        gap: "0.3rem",
      }}
      className={u === "URGENT" ? "pulse-urgent" : ""}
    >
      {URGENCY_ICONS[u]} {u}
    </span>
  );
}

function StatCard({ num, label, color, sub }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "1.25rem",
        textAlign: "center",
        borderTop: `3px solid ${color}`,
      }}
    >
      <div
        style={{
          fontFamily: "Syne, sans-serif",
          fontSize: "2rem",
          fontWeight: 800,
          color,
          lineHeight: 1,
          marginBottom: "0.3rem",
        }}
      >
        {num}
      </div>
      <div
        style={{
          fontFamily: "DM Mono, monospace",
          fontSize: "0.68rem",
          color: "var(--muted)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {label}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "0.7rem",
            color: "var(--muted)",
            marginTop: "0.2rem",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function DamageBadge({ name }) {
  const n = name.toLowerCase();
  const isP = n.includes("pothole");
  const isC = n.includes("crack");
  return (
    <span
      style={{
        background: isP ? "#1a0a0a" : isC ? "#0c1a2e" : "#1a1500",
        color: isP ? "#f87171" : isC ? "#60a5fa" : "#fbbf24",
        border: `1px solid ${isP ? "#3b1f1f" : isC ? "#1e3a5f" : "#3d2f00"}`,
        padding: "0.2rem 0.6rem",
        borderRadius: 6,
        fontSize: "0.72rem",
        fontFamily: "DM Mono, monospace",
        margin: "0.15rem",
        display: "inline-block",
      }}
    >
      {isP ? "🕳️" : isC ? "⚡" : "⚠️"} {name}
    </span>
  );
}

const SectionHeader = ({ children }) => (
  <div
    style={{
      fontFamily: "DM Mono, monospace",
      fontSize: "0.68rem",
      fontWeight: 700,
      letterSpacing: "0.15em",
      textTransform: "uppercase",
      color: "var(--muted)",
      margin: "2rem 0 1rem",
      display: "flex",
      alignItems: "center",
      gap: "0.75rem",
    }}
  >
    {children}
    <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
  </div>
);

const customTooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--text)",
  fontFamily: "DM Mono, monospace",
  fontSize: "0.75rem",
};

// ─── MAIN DASHBOARD ─────────────────────────────────────────
export default function Dashboard() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");
  const [sortBy, setSortBy] = useState("newest");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("reports"); // reports | map | charts
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchReports = useCallback(async () => {
    const { data, error } = await supabase
      .from("reports")
      .select("*")
      .order("created_at", { ascending: false });
    if (!error) {
      setReports(data || []);
      setLastUpdated(new Date());
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchReports();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchReports, 30000);
    return () => clearInterval(interval);
  }, [fetchReports]);

  // ── Derived stats ──
  const total = reports.length;
  const urgent = reports.filter((r) => r.urgency === "URGENT").length;
  const high = reports.filter((r) => r.urgency === "HIGH").length;
  const medium = reports.filter((r) => r.urgency === "MEDIUM").length;
  const lowNorm = reports.filter((r) =>
    ["LOW", "NORMAL"].includes(r.urgency),
  ).length;
  const withGPS = reports.filter((r) => r.latitude && r.longitude).length;

  // ── Chart data ──
  const urgencyDist = ["URGENT", "HIGH", "MEDIUM", "LOW", "NORMAL"]
    .map((u) => ({
      name: u,
      count: reports.filter((r) => r.urgency === u).length,
      fill: URGENCY_COLORS[u],
    }))
    .filter((d) => d.count > 0);

  const classCount = {};
  reports.forEach((r) =>
    (r.detected || []).forEach((d) => {
      classCount[d] = (classCount[d] || 0) + 1;
    }),
  );
  const classData = Object.entries(classCount)
    .map(([name, count]) => ({ name: name.replace(" Crack", ""), count }))
    .sort((a, b) => b.count - a.count);

  // Timeline — last 7 days
  const timelineMap = {};
  reports.forEach((r) => {
    const day = format(new Date(r.created_at), "MM/dd");
    timelineMap[day] = (timelineMap[day] || 0) + 1;
  });
  const timelineData = Object.entries(timelineMap)
    .map(([date, count]) => ({ date, count }))
    .slice(-7);

  // ── Filtered reports ──
  let filtered = reports.filter((r) => {
    const matchFilter = filter === "All" || r.urgency === filter;
    const matchSearch =
      !search ||
      (r.location_str || "").toLowerCase().includes(search.toLowerCase()) ||
      (r.detected || [])
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      r.urgency.toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  });

  if (sortBy === "newest")
    filtered = [...filtered].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at),
    );
  if (sortBy === "oldest")
    filtered = [...filtered].sort(
      (a, b) => new Date(a.created_at) - new Date(b.created_at),
    );
  if (sortBy === "urgency")
    filtered = [...filtered].sort(
      (a, b) => URGENCY_ORDER[a.urgency] - URGENCY_ORDER[b.urgency],
    );
  if (sortBy === "score")
    filtered = [...filtered].sort((a, b) => b.score - a.score);

  // ─── RENDER ─────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* ── TOP NAV ── */}
      <nav
        style={{
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          padding: "0 2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 60,
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: 36,
              height: 36,
              background: "linear-gradient(135deg,#f59e0b,#d97706)",
              borderRadius: 9,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.1rem",
            }}
          >
            🛣️
          </div>
          <div>
            <div
              style={{
                fontFamily: "Syne, sans-serif",
                fontWeight: 800,
                fontSize: "1.1rem",
                letterSpacing: "-0.02em",
              }}
            >
              InspectRAIL
            </div>
            <div
              style={{
                fontFamily: "DM Mono, monospace",
                fontSize: "0.6rem",
                color: "var(--muted)",
                letterSpacing: "0.1em",
              }}
            >
              DASHBOARD
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {lastUpdated && (
            <span
              style={{
                fontFamily: "DM Mono, monospace",
                fontSize: "0.68rem",
                color: "var(--muted)",
              }}
            >
              Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
            </span>
          )}
          <button
            onClick={fetchReports}
            style={{
              background: "var(--surface2)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              padding: "0.4rem 1rem",
              borderRadius: 8,
              fontFamily: "DM Mono, monospace",
              fontSize: "0.72rem",
              cursor: "pointer",
            }}
          >
            ↻ Refresh
          </button>
          {urgent > 0 && (
            <div
              className="pulse-urgent"
              style={{
                background: "#450a0a",
                border: "1px solid #dc2626",
                color: "#f87171",
                padding: "0.35rem 0.8rem",
                borderRadius: 8,
                fontFamily: "DM Mono, monospace",
                fontSize: "0.72rem",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              🚨 {urgent} URGENT
            </div>
          )}
        </div>
      </nav>

      <main style={{ padding: "2rem", maxWidth: 1400, margin: "0 auto" }}>
        {/* ── STAT CARDS ── */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(6,1fr)",
            gap: "1rem",
            marginBottom: "2rem",
          }}
        >
          <StatCard num={total} label="Total Reports" color="var(--accent)" />
          <StatCard num={urgent} label="Urgent" color="#dc2626" />
          <StatCard num={high} label="High" color="#f97316" />
          <StatCard num={medium} label="Medium" color="#eab308" />
          <StatCard num={lowNorm} label="Low / Normal" color="#22c55e" />
          <StatCard num={withGPS} label="With GPS" color="#06b6d4" />
        </div>

        {/* ── TAB BAR ── */}
        <div
          style={{
            display: "flex",
            gap: "0.35rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: "0.3rem",
            marginBottom: "2rem",
            width: "fit-content",
          }}
        >
          {[
            { id: "reports", label: "📋  Reports" },
            { id: "map", label: "🗺️  Map View" },
            { id: "charts", label: "📊  Analytics" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background:
                  activeTab === tab.id ? "var(--accent)" : "transparent",
                color: activeTab === tab.id ? "#0a0a0a" : "var(--muted)",
                border: "none",
                borderRadius: 8,
                padding: "0.45rem 1.2rem",
                fontFamily: "DM Mono, monospace",
                fontSize: "0.78rem",
                fontWeight: activeTab === tab.id ? 700 : 500,
                cursor: "pointer",
                letterSpacing: "0.04em",
                transition: "all 0.2s",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && (
          <div
            style={{
              textAlign: "center",
              padding: "4rem",
              color: "var(--muted)",
              fontFamily: "DM Mono, monospace",
              fontSize: "0.85rem",
            }}
          >
            Loading reports...
          </div>
        )}

        {!loading && reports.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "5rem 2rem",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 16,
            }}
          >
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>📋</div>
            <h3
              style={{ fontFamily: "Syne, sans-serif", marginBottom: "0.5rem" }}
            >
              No reports yet
            </h3>
            <p
              style={{
                fontFamily: "DM Mono, monospace",
                fontSize: "0.78rem",
                color: "var(--muted)",
              }}
            >
              Submit a road inspection from the InspectRAIL app to see reports
              here
            </p>
          </div>
        )}

        {/* ══════════════════════════════════════════ */}
        {/* TAB: REPORTS                               */}
        {/* ══════════════════════════════════════════ */}
        {!loading && activeTab === "reports" && reports.length > 0 && (
          <>
            {/* Filter bar */}
            <div
              style={{
                display: "flex",
                gap: "0.75rem",
                marginBottom: "1.5rem",
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="🔍  Search by location, damage type..."
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  padding: "0.5rem 1rem",
                  borderRadius: 9,
                  fontFamily: "DM Mono, monospace",
                  fontSize: "0.78rem",
                  width: 280,
                  outline: "none",
                }}
              />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  padding: "0.5rem 1rem",
                  borderRadius: 9,
                  fontFamily: "DM Mono, monospace",
                  fontSize: "0.78rem",
                  cursor: "pointer",
                }}
              >
                {["All", "URGENT", "HIGH", "MEDIUM", "LOW", "NORMAL"].map(
                  (u) => (
                    <option key={u}>{u}</option>
                  ),
                )}
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  padding: "0.5rem 1rem",
                  borderRadius: 9,
                  fontFamily: "DM Mono, monospace",
                  fontSize: "0.78rem",
                  cursor: "pointer",
                }}
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="urgency">Highest Urgency</option>
                <option value="score">Highest Score</option>
              </select>
              <span
                style={{
                  fontFamily: "DM Mono, monospace",
                  fontSize: "0.72rem",
                  color: "var(--muted)",
                  marginLeft: "auto",
                }}
              >
                {filtered.length} report{filtered.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Report list */}
            <div
              style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
            >
              {filtered.map((r, i) => (
                <div
                  key={r.id}
                  className="fade-in"
                  style={{ animationDelay: `${i * 0.04}s` }}
                >
                  <div
                    onClick={() =>
                      setSelected(selected?.id === r.id ? null : r)
                    }
                    style={{
                      background: "var(--surface)",
                      border: `1px solid ${selected?.id === r.id ? "var(--accent)" : URGENCY_COLORS[r.urgency] + "33"}`,
                      borderRadius: 14,
                      padding: "1.25rem",
                      cursor: "pointer",
                      transition: "all 0.2s",
                      borderLeft: `4px solid ${URGENCY_COLORS[r.urgency]}`,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "1rem",
                        flexWrap: "wrap",
                      }}
                    >
                      {/* Thumbnail */}
                      {r.image_url && (
                        <img
                          src={r.image_url}
                          alt="road"
                          style={{
                            width: 80,
                            height: 60,
                            objectFit: "cover",
                            borderRadius: 8,
                            flexShrink: 0,
                          }}
                        />
                      )}
                      {/* Info */}
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.75rem",
                            marginBottom: "0.4rem",
                            flexWrap: "wrap",
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "Syne, sans-serif",
                              fontWeight: 700,
                              fontSize: "0.95rem",
                            }}
                          >
                            Report #{r.id}
                          </span>
                          <UrgencyBadge u={r.urgency} />
                          {(r.detected || []).map((d) => (
                            <DamageBadge key={d} name={d} />
                          ))}
                        </div>
                        <div
                          style={{
                            fontFamily: "DM Mono, monospace",
                            fontSize: "0.7rem",
                            color: "var(--muted)",
                            display: "flex",
                            gap: "1.5rem",
                            flexWrap: "wrap",
                          }}
                        >
                          <span>
                            🕐{" "}
                            {format(
                              new Date(r.created_at),
                              "MMM d, yyyy HH:mm",
                            )}
                          </span>
                          {r.location_str &&
                            r.location_str !== "Not provided" && (
                              <span>📍 {r.location_str}</span>
                            )}
                          <span>
                            ⚡ {r.num_det} detection{r.num_det !== 1 ? "s" : ""}
                          </span>
                          <span>Score: {(r.score * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      <div
                        style={{
                          fontFamily: "DM Mono, monospace",
                          fontSize: "0.7rem",
                          color: "var(--muted)",
                        }}
                      >
                        {selected?.id === r.id ? "▲ collapse" : "▼ expand"}
                      </div>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {selected?.id === r.id && (
                    <div
                      style={{
                        background: "var(--surface2)",
                        border: "1px solid var(--border)",
                        borderTop: "none",
                        borderRadius: "0 0 14px 14px",
                        padding: "1.5rem",
                      }}
                    >
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: "1.5rem",
                          marginBottom: "1.5rem",
                        }}
                      >
                        <div>
                          <p
                            style={{
                              fontFamily: "DM Mono, monospace",
                              fontSize: "0.7rem",
                              color: "var(--muted)",
                              marginBottom: "0.5rem",
                            }}
                          >
                            ORIGINAL IMAGE
                          </p>
                          {r.image_url ? (
                            <img
                              src={r.image_url}
                              alt="original"
                              style={{ width: "100%", borderRadius: 10 }}
                            />
                          ) : (
                            <div
                              style={{
                                background: "var(--surface)",
                                borderRadius: 10,
                                height: 180,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "var(--muted)",
                                fontSize: "0.78rem",
                              }}
                            >
                              No image
                            </div>
                          )}
                        </div>
                        <div>
                          <p
                            style={{
                              fontFamily: "DM Mono, monospace",
                              fontSize: "0.7rem",
                              color: "var(--muted)",
                              marginBottom: "0.5rem",
                            }}
                          >
                            ANNOTATED RESULT
                          </p>
                          {r.annot_url ? (
                            <img
                              src={r.annot_url}
                              alt="annotated"
                              style={{ width: "100%", borderRadius: 10 }}
                            />
                          ) : (
                            <div
                              style={{
                                background: "var(--surface)",
                                borderRadius: 10,
                                height: 180,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "var(--muted)",
                                fontSize: "0.78rem",
                              }}
                            >
                              No image
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Metrics */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(4,1fr)",
                          gap: "1rem",
                        }}
                      >
                        {[
                          {
                            label: "Urgency",
                            val: <UrgencyBadge u={r.urgency} />,
                          },
                          { label: "Detections", val: r.num_det },
                          {
                            label: "Urgency Score",
                            val: `${(r.score * 100).toFixed(1)}%`,
                          },
                          {
                            label: "Anomaly Score",
                            val: r.anomaly?.toFixed(5),
                          },
                        ].map((m) => (
                          <div
                            key={m.label}
                            style={{
                              background: "var(--surface)",
                              border: "1px solid var(--border)",
                              borderRadius: 10,
                              padding: "1rem",
                            }}
                          >
                            <div
                              style={{
                                fontFamily: "DM Mono, monospace",
                                fontSize: "0.65rem",
                                color: "var(--muted)",
                                textTransform: "uppercase",
                                letterSpacing: "0.1em",
                                marginBottom: "0.4rem",
                              }}
                            >
                              {m.label}
                            </div>
                            <div
                              style={{
                                fontFamily: "Syne, sans-serif",
                                fontSize: "1.1rem",
                                fontWeight: 700,
                              }}
                            >
                              {m.val}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* GPS */}
                      {r.latitude && r.longitude && (
                        <div
                          style={{
                            marginTop: "1rem",
                            background: "var(--surface)",
                            border: "1px solid var(--border)",
                            borderRadius: 10,
                            padding: "1rem",
                            display: "flex",
                            gap: "2rem",
                          }}
                        >
                          <div>
                            <div
                              style={{
                                fontFamily: "DM Mono, monospace",
                                fontSize: "0.65rem",
                                color: "var(--muted)",
                                textTransform: "uppercase",
                                letterSpacing: "0.1em",
                              }}
                            >
                              GPS Coordinates
                            </div>
                            <div
                              style={{
                                fontFamily: "DM Mono, monospace",
                                fontSize: "0.9rem",
                                color: "var(--accent)",
                                marginTop: "0.3rem",
                              }}
                            >
                              {r.latitude.toFixed(6)}, {r.longitude.toFixed(6)}
                            </div>
                          </div>
                          <a
                            href={`https://www.google.com/maps?q=${r.latitude},${r.longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              marginLeft: "auto",
                              alignSelf: "center",
                              background: "var(--surface2)",
                              border: "1px solid var(--border)",
                              color: "var(--accent)",
                              padding: "0.4rem 0.9rem",
                              borderRadius: 8,
                              fontFamily: "DM Mono, monospace",
                              fontSize: "0.72rem",
                              textDecoration: "none",
                            }}
                          >
                            📍 Open in Maps
                          </a>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {/* ══════════════════════════════════════════ */}
        {/* TAB: MAP                                   */}
        {/* ══════════════════════════════════════════ */}
        {!loading && activeTab === "map" && (
          <>
            <SectionHeader>GPS Report Map</SectionHeader>
            {withGPS === 0 ? (
              <div
                style={{
                  textAlign: "center",
                  padding: "4rem",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 14,
                }}
              >
                <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>
                  🗺️
                </div>
                <p
                  style={{
                    fontFamily: "DM Mono, monospace",
                    fontSize: "0.82rem",
                    color: "var(--muted)",
                  }}
                >
                  No GPS data yet — submit reports with coordinates to see them
                  on the map
                </p>
              </div>
            ) : (
              <div
                style={{
                  height: 560,
                  borderRadius: 14,
                  overflow: "hidden",
                  border: "1px solid var(--border)",
                }}
              >
                <MapComponent
                  reports={reports.filter((r) => r.latitude && r.longitude)}
                />
              </div>
            )}
          </>
        )}

        {/* ══════════════════════════════════════════ */}
        {/* TAB: CHARTS                                */}
        {/* ══════════════════════════════════════════ */}
        {!loading && activeTab === "charts" && reports.length > 0 && (
          <>
            <SectionHeader>Analytics</SectionHeader>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1.5rem",
              }}
            >
              {/* Urgency distribution pie */}
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 14,
                  padding: "1.5rem",
                }}
              >
                <h3
                  style={{
                    fontFamily: "Syne, sans-serif",
                    fontSize: "0.95rem",
                    fontWeight: 700,
                    marginBottom: "1.25rem",
                  }}
                >
                  Urgency Distribution
                </h3>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={urgencyDist}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                    >
                      {urgencyDist.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={customTooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Damage class bar chart */}
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 14,
                  padding: "1.5rem",
                }}
              >
                <h3
                  style={{
                    fontFamily: "Syne, sans-serif",
                    fontSize: "0.95rem",
                    fontWeight: 700,
                    marginBottom: "1.25rem",
                  }}
                >
                  Damage Type Frequency
                </h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={classData} margin={{ left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
                    <XAxis
                      dataKey="name"
                      tick={{
                        fill: "#64748b",
                        fontSize: 11,
                        fontFamily: "DM Mono, monospace",
                      }}
                    />
                    <YAxis
                      tick={{
                        fill: "#64748b",
                        fontSize: 11,
                        fontFamily: "DM Mono, monospace",
                      }}
                    />
                    <Tooltip contentStyle={customTooltipStyle} />
                    <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Timeline */}
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 14,
                  padding: "1.5rem",
                  gridColumn: "1 / -1",
                }}
              >
                <h3
                  style={{
                    fontFamily: "Syne, sans-serif",
                    fontSize: "0.95rem",
                    fontWeight: 700,
                    marginBottom: "1.25rem",
                  }}
                >
                  Reports Over Time
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={timelineData} margin={{ left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
                    <XAxis
                      dataKey="date"
                      tick={{
                        fill: "#64748b",
                        fontSize: 11,
                        fontFamily: "DM Mono, monospace",
                      }}
                    />
                    <YAxis
                      tick={{
                        fill: "#64748b",
                        fontSize: 11,
                        fontFamily: "DM Mono, monospace",
                      }}
                      allowDecimals={false}
                    />
                    <Tooltip contentStyle={customTooltipStyle} />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={{ fill: "#f59e0b", r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer
        style={{
          textAlign: "center",
          padding: "2rem",
          fontFamily: "DM Mono, monospace",
          fontSize: "0.68rem",
          color: "var(--muted)",
          borderTop: "1px solid var(--border)",
          marginTop: "3rem",
        }}
      >
        InspectRAIL — Road Analysis & Inspection Logic · Powered by YOLOv8 +
        ConvAE · RDD2022
      </footer>
    </div>
  );
}
