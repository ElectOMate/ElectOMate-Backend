import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchTopics, fetchParties, fetchStats, fetchArguments } from "../api/graphApi";
import type { TopicInfo, PartyInfo, GraphStats, ArgumentSummary } from "../types";
import { PARTY_COLORS } from "../types";

export default function DatabaseView() {
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [parties, setParties] = useState<PartyInfo[]>([]);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [args, setArgs] = useState<ArgumentSummary[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string>("");
  const [selectedParty, setSelectedParty] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"overview" | "arguments" | "topics" | "parties">("overview");

  useEffect(() => {
    Promise.all([fetchTopics(), fetchParties(), fetchStats()])
      .then(([t, p, s]) => { setTopics(t); setParties(p); setStats(s); })
      .catch(console.error);
  }, []);

  const loadArguments = async () => {
    setLoading(true);
    try {
      const params: { topic?: string; party?: string; limit?: number } = { limit: 100 };
      if (selectedTopic) params.topic = selectedTopic;
      if (selectedParty) params.party = selectedParty;
      const data = await fetchArguments(params);
      setArgs(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (tab === "arguments") loadArguments();
  }, [tab, selectedTopic, selectedParty]);

  return (
    <div style={{ background: "#0F172A", color: "#E2E8F0", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      {/* Header */}
      <div style={{ background: "#1E293B", borderBottom: "1px solid #334155", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16 }}>
        <Link to="/" style={{ color: "#94A3B8", textDecoration: "none", fontSize: 13 }}>← Home</Link>
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, flex: 1 }}>
          🗄️ Knowledge Graph Database View
        </h1>
        {stats && (
          <span style={{ color: "#64748B", fontSize: 12 }}>
            {stats.total_arguments} arguments · {stats.total_topics} topics · {stats.total_parties} parties · {stats.total_sources} sources
          </span>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #334155", background: "#1E293B" }}>
        {(["overview", "arguments", "topics", "parties"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "10px 24px", border: "none", cursor: "pointer",
              background: tab === t ? "#0F172A" : "transparent",
              color: tab === t ? "#3B82F6" : "#94A3B8",
              borderBottom: tab === t ? "2px solid #3B82F6" : "2px solid transparent",
              fontSize: 13, fontWeight: 600, textTransform: "uppercase",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div style={{ padding: 24 }}>
        {/* Overview Tab */}
        {tab === "overview" && stats && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
              {[
                { label: "Arguments", value: stats.total_arguments, color: "#10B981" },
                { label: "Topics", value: stats.total_topics, color: "#3B82F6" },
                { label: "Parties", value: stats.total_parties, color: "#FF6600" },
                { label: "Politicians", value: stats.total_politicians, color: "#8B5CF6" },
                { label: "Sources", value: stats.total_sources, color: "#F59E0B" },
                { label: "Relationships", value: stats.total_relationships, color: "#EF4444" },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ background: "#1E293B", borderRadius: 12, padding: 20, border: "1px solid #334155" }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color }}>{value}</div>
                  <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 4 }}>{label}</div>
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
              {/* Topics breakdown */}
              <div style={{ background: "#1E293B", borderRadius: 12, padding: 20, border: "1px solid #334155" }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Topics by Argument Count</h3>
                {topics.map((t) => (
                  <div key={t.name} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <div style={{ width: 120, fontSize: 12, color: "#CBD5E1" }}>{t.name}</div>
                    <div style={{ flex: 1, height: 16, background: "#0F172A", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{
                        width: `${Math.min(100, (t.argument_count / (topics[0]?.argument_count || 1)) * 100)}%`,
                        height: "100%", background: "#3B82F6", borderRadius: 4,
                      }} />
                    </div>
                    <div style={{ width: 40, fontSize: 11, color: "#94A3B8", textAlign: "right" }}>{t.argument_count}</div>
                  </div>
                ))}
              </div>

              {/* Parties breakdown */}
              <div style={{ background: "#1E293B", borderRadius: 12, padding: 20, border: "1px solid #334155" }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Parties by Argument Count</h3>
                {parties.map((p) => (
                  <div key={p.shortname} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <div style={{
                      width: 60, padding: "3px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, textAlign: "center",
                      background: PARTY_COLORS[p.shortname] || "#475569",
                      color: p.shortname === "MKKP" ? "#000" : "#fff",
                    }}>
                      {p.shortname}
                    </div>
                    <div style={{ flex: 1, height: 16, background: "#0F172A", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{
                        width: `${Math.min(100, (p.argument_count / (parties[0]?.argument_count || 1)) * 100)}%`,
                        height: "100%", background: PARTY_COLORS[p.shortname] || "#475569", borderRadius: 4,
                      }} />
                    </div>
                    <div style={{ width: 40, fontSize: 11, color: "#94A3B8", textAlign: "right" }}>{p.argument_count}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Arguments Tab */}
        {tab === "arguments" && (
          <div>
            <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
              <select
                value={selectedTopic}
                onChange={(e) => setSelectedTopic(e.target.value)}
                style={{ background: "#1E293B", color: "#E2E8F0", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}
              >
                <option value="">All Topics</option>
                {topics.map((t) => <option key={t.name} value={t.name}>{t.name} ({t.argument_count})</option>)}
              </select>
              <select
                value={selectedParty}
                onChange={(e) => setSelectedParty(e.target.value)}
                style={{ background: "#1E293B", color: "#E2E8F0", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}
              >
                <option value="">All Parties</option>
                {parties.map((p) => <option key={p.shortname} value={p.shortname}>{p.shortname} ({p.argument_count})</option>)}
              </select>
              <span style={{ color: "#64748B", fontSize: 12, alignSelf: "center" }}>
                {loading ? "Loading..." : `${args.length} arguments`}
              </span>
            </div>

            <div style={{ background: "#1E293B", borderRadius: 12, border: "1px solid #334155", overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #334155" }}>
                    <th style={thStyle}>Argument</th>
                    <th style={{ ...thStyle, width: 80 }}>Party</th>
                    <th style={{ ...thStyle, width: 80 }}>Type</th>
                    <th style={{ ...thStyle, width: 80 }}>Sentiment</th>
                    <th style={{ ...thStyle, width: 60 }}>Strength</th>
                    <th style={{ ...thStyle, width: 150 }}>Topics</th>
                  </tr>
                </thead>
                <tbody>
                  {args.map((a, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1E293B" }}>
                      <td style={tdStyle}>{a.text}</td>
                      <td style={tdStyle}>
                        {a.party && (
                          <span style={{
                            padding: "2px 6px", borderRadius: 4, fontSize: 10, fontWeight: 700,
                            background: PARTY_COLORS[a.party] || "#475569", color: "#fff",
                          }}>
                            {a.party}
                          </span>
                        )}
                      </td>
                      <td style={{ ...tdStyle, fontSize: 11 }}>{a.argument_type || "-"}</td>
                      <td style={tdStyle}>
                        <span style={{
                          color: a.sentiment === "for" ? "#22C55E" : a.sentiment === "against" ? "#EF4444" : "#94A3B8",
                          fontSize: 11,
                        }}>
                          {a.sentiment === "for" ? "🟢 For" : a.sentiment === "against" ? "🔴 Against" : "⚪ Neutral"}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        {a.strength ? "★".repeat(a.strength) + "☆".repeat(5 - a.strength) : "-"}
                      </td>
                      <td style={{ ...tdStyle, fontSize: 11 }}>{a.topics.join(", ") || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Topics Tab */}
        {tab === "topics" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
            {topics.map((t) => (
              <div key={t.name} style={{ background: "#1E293B", borderRadius: 12, padding: 20, border: "1px solid #334155" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{t.name}</h3>
                    <div style={{ fontSize: 12, color: "#94A3B8" }}>{t.name_en}</div>
                  </div>
                  <span style={{
                    background: "#3B82F6", color: "#fff", padding: "4px 10px", borderRadius: 20,
                    fontSize: 12, fontWeight: 700,
                  }}>
                    {t.argument_count}
                  </span>
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#64748B" }}>Category: {t.category}</div>
              </div>
            ))}
          </div>
        )}

        {/* Parties Tab */}
        {tab === "parties" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
            {parties.map((p) => (
              <div key={p.shortname} style={{ background: "#1E293B", borderRadius: 12, padding: 20, border: "1px solid #334155", borderLeft: `4px solid ${PARTY_COLORS[p.shortname] || "#475569"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{p.shortname}</h3>
                    <div style={{ fontSize: 12, color: "#94A3B8" }}>{p.name}</div>
                  </div>
                  <span style={{
                    background: PARTY_COLORS[p.shortname] || "#475569", color: "#fff",
                    padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 700,
                  }}>
                    {p.argument_count}
                  </span>
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#64748B" }}>Ideology: {p.ideology}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "10px 12px", fontSize: 11, color: "#64748B",
  textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 600,
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px", fontSize: 13, color: "#CBD5E1",
  verticalAlign: "top", lineHeight: 1.4,
};
