import type { GraphNode } from "../types";
import { PARTY_COLORS } from "../types";

interface Props {
  node: GraphNode;
  onClose: () => void;
  onExpand: (nodeId: string) => void;
}

export default function NodeDetail({ node, onClose, onExpand }: Props) {
  const sentiment = node.properties?.sentiment as string | undefined;
  const sentimentColor =
    sentiment === "for" ? "#22C55E" : sentiment === "against" ? "#EF4444" : "#6B7280";
  const strength = node.properties?.strength as number | undefined;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        right: 0,
        width: 360,
        height: "100vh",
        background: "#1E293B",
        borderLeft: "1px solid #334155",
        zIndex: 30,
        overflow: "auto",
        padding: "20px",
        color: "#E2E8F0",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 16 }}>
        <span
          style={{
            background: node.type === "Party"
              ? PARTY_COLORS[node.label] || "#475569"
              : node.type === "Topic"
                ? "#3B82F6"
                : "#10B981",
            color: "#fff",
            padding: "3px 10px",
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
          }}
        >
          {node.type}
        </span>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#94A3B8",
            fontSize: 20,
            cursor: "pointer",
            padding: "0 4px",
          }}
        >
          ✕
        </button>
      </div>

      {/* Title */}
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, lineHeight: 1.3 }}>
        {node.label}
      </h2>

      {/* Properties */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {node.type === "Argument" && (
          <>
            {node.properties?.argument_type && (
              <div>
                <Label>Type</Label>
                <Value>{String(node.properties.argument_type)}</Value>
              </div>
            )}
            {sentiment && (
              <div>
                <Label>Sentiment</Label>
                <span style={{ color: sentimentColor, fontWeight: 600, fontSize: 14 }}>
                  {sentiment === "for" ? "🟢 For" : sentiment === "against" ? "🔴 Against" : "⚪ Neutral"}
                </span>
              </div>
            )}
            {strength && (
              <div>
                <Label>Strength</Label>
                <Value>{"★".repeat(strength)}{"☆".repeat(5 - strength)}</Value>
              </div>
            )}
            {node.properties?.party && (
              <div>
                <Label>Party</Label>
                <span
                  style={{
                    background: PARTY_COLORS[String(node.properties.party)] || "#475569",
                    color: "#fff",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  {String(node.properties.party)}
                </span>
              </div>
            )}
            {node.properties?.speaker && (
              <div>
                <Label>Speaker</Label>
                <Value>{String(node.properties.speaker)}</Value>
              </div>
            )}
          </>
        )}

        {node.type === "Topic" && (
          <>
            {node.properties?.name_en && (
              <div>
                <Label>English</Label>
                <Value>{String(node.properties.name_en)}</Value>
              </div>
            )}
            {node.properties?.category && (
              <div>
                <Label>Category</Label>
                <Value>{String(node.properties.category)}</Value>
              </div>
            )}
            {node.properties?.argument_count != null && (
              <div>
                <Label>Arguments</Label>
                <Value>{String(node.properties.argument_count)}</Value>
              </div>
            )}
          </>
        )}

        {node.type === "Party" && (
          <>
            {node.properties?.name && (
              <div>
                <Label>Full Name</Label>
                <Value>{String(node.properties.name)}</Value>
              </div>
            )}
            {node.properties?.ideology && (
              <div>
                <Label>Ideology</Label>
                <Value>{String(node.properties.ideology)}</Value>
              </div>
            )}
            {node.properties?.argument_count != null && (
              <div>
                <Label>Arguments</Label>
                <Value>{String(node.properties.argument_count)}</Value>
              </div>
            )}
          </>
        )}
      </div>

      {/* Expand button */}
      <button
        onClick={() => onExpand(node.id)}
        style={{
          marginTop: 20,
          width: "100%",
          padding: "10px",
          background: "#3B82F6",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Expand Neighbors
      </button>

      {/* Keyboard hint */}
      <p style={{ marginTop: 16, color: "#64748B", fontSize: 11, textAlign: "center" }}>
        Press <kbd style={{ background: "#334155", padding: "2px 6px", borderRadius: 3 }}>Esc</kbd> to close
      </p>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span style={{ fontSize: 11, color: "#94A3B8", textTransform: "uppercase", letterSpacing: 0.5 }}>
      {children}
    </span>
  );
}

function Value({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 14, marginTop: 2 }}>{children}</div>;
}
