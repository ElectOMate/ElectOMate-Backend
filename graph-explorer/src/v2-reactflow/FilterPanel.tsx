import type { TopicInfo, PartyInfo } from "../types";
import { PARTY_COLORS } from "../types";
import { useState } from "react";

interface Props {
  topics: TopicInfo[];
  parties: PartyInfo[];
  hiddenTopics: Set<string>;
  hiddenParties: Set<string>;
  hiddenRelTypes: Set<string>;
  searchQuery: string;
  onToggleTopic: (name: string) => void;
  onToggleParty: (name: string) => void;
  onToggleRelType: (rel: string) => void;
  onSearch: (q: string) => void;
  onReset: () => void;
}

const REL_TYPES = [
  { key: "ABOUT", label: "About", color: "#3B82F6" },
  { key: "MADE_BY", label: "Made by", color: "#FF8C00" },
  { key: "SUPPORTS", label: "Supports", color: "#22C55E" },
  { key: "REBUTS", label: "Rebuts", color: "#EF4444" },
  { key: "CONTRADICTS", label: "Contradicts", color: "#EF4444" },
];

export default function FilterPanel({
  topics,
  parties,
  hiddenTopics,
  hiddenParties,
  hiddenRelTypes,
  searchQuery,
  onToggleTopic,
  onToggleParty,
  onToggleRelType,
  onSearch,
  onReset,
}: Props) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      style={{
        position: "absolute",
        top: 12,
        right: 12,
        zIndex: 20,
        background: "#1E293B",
        border: "1px solid #334155",
        borderRadius: 10,
        padding: collapsed ? "8px 12px" : "14px 16px",
        width: collapsed ? "auto" : 240,
        maxHeight: "90vh",
        overflow: "auto",
        fontSize: 12,
        color: "#CBD5E1",
      }}
    >
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <span style={{ fontWeight: 700, fontSize: 13 }}>Filters</span>
        <span style={{ color: "#64748B" }}>{collapsed ? "▸" : "▾"}</span>
      </div>

      {!collapsed && (
        <>
          {/* Search */}
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => onSearch(e.target.value)}
            style={{
              width: "100%",
              marginTop: 10,
              padding: "6px 10px",
              background: "#0F172A",
              border: "1px solid #334155",
              borderRadius: 6,
              color: "#E2E8F0",
              fontSize: 12,
              outline: "none",
            }}
          />

          {/* Topics */}
          <Section title="Topics">
            {topics.map((t) => (
              <Checkbox
                key={t.name}
                label={`${t.name} (${t.argument_count})`}
                checked={!hiddenTopics.has(t.name)}
                color="#3B82F6"
                onChange={() => onToggleTopic(t.name)}
              />
            ))}
          </Section>

          {/* Parties */}
          <Section title="Parties">
            {parties.map((p) => (
              <Checkbox
                key={p.shortname}
                label={`${p.shortname} (${p.argument_count})`}
                checked={!hiddenParties.has(p.shortname)}
                color={PARTY_COLORS[p.shortname] || "#888"}
                onChange={() => onToggleParty(p.shortname)}
              />
            ))}
          </Section>

          {/* Relationships */}
          <Section title="Relationships">
            {REL_TYPES.map((r) => (
              <Checkbox
                key={r.key}
                label={r.label}
                checked={!hiddenRelTypes.has(r.key)}
                color={r.color}
                onChange={() => onToggleRelType(r.key)}
              />
            ))}
          </Section>

          {/* Reset */}
          <button
            onClick={onReset}
            style={{
              marginTop: 10,
              width: "100%",
              padding: "6px",
              background: "#334155",
              color: "#CBD5E1",
              border: "none",
              borderRadius: 6,
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            Reset All
          </button>
        </>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 10, color: "#64748B", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>{children}</div>
    </div>
  );
}

function Checkbox({
  label,
  checked,
  color,
  onChange,
}: {
  label: string;
  checked: boolean;
  color: string;
  onChange: () => void;
}) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        cursor: "pointer",
        opacity: checked ? 1 : 0.4,
        fontSize: 11,
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 2,
          background: checked ? color : "transparent",
          border: `1.5px solid ${color}`,
          flexShrink: 0,
        }}
        onClick={(e) => {
          e.preventDefault();
          onChange();
        }}
      />
      <span onClick={onChange}>{label}</span>
    </label>
  );
}
