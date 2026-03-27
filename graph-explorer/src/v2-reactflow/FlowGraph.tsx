import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Link } from "react-router-dom";

import { fetchTopics, fetchParties, fetchNeighborhood } from "../api/graphApi";
import type { GraphNode, TopicInfo, PartyInfo } from "../types";
import { PARTY_COLORS } from "../types";
import NodeDetail from "./NodeDetail";
import FilterPanel from "./FilterPanel";

/* ── colour helpers ────────────────────────────────────────────── */

const TYPE_COLORS: Record<string, string> = {
  Topic: "#3B82F6",
  Party: "#FF6600",
  Argument: "#10B981",
  Source: "#6B7280",
  Politician: "#8B5CF6",
};

const EDGE_STYLES: Record<string, { stroke: string; strokeDasharray?: string }> = {
  ABOUT: { stroke: "#3B82F6" },
  MADE_BY: { stroke: "#FF8C00" },
  SUPPORTS: { stroke: "#22C55E", strokeDasharray: "5 3" },
  REBUTS: { stroke: "#EF4444" },
  CONTRADICTS: { stroke: "#EF4444", strokeDasharray: "8 4" },
  SOURCED_FROM: { stroke: "#6B7280", strokeDasharray: "3 3" },
  HAS_ARGUMENTS: { stroke: "#475569", strokeDasharray: "2 4" },
};

/* ── layout helpers ────────────────────────────────────────────── */

function circleLayout(cx: number, cy: number, count: number, radius: number) {
  return Array.from({ length: count }, (_, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });
}

/* ── component ─────────────────────────────────────────────────── */

export default function FlowGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  // Filters
  const [hiddenTopics, setHiddenTopics] = useState<Set<string>>(new Set());
  const [hiddenParties, setHiddenParties] = useState<Set<string>>(new Set());
  const [hiddenRelTypes, setHiddenRelTypes] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");

  // Topics & parties for filter panel
  const [allTopics, setAllTopics] = useState<TopicInfo[]>([]);
  const [allParties, setAllParties] = useState<PartyInfo[]>([]);

  // Track all graph nodes by id
  const graphNodes = useRef<Map<string, GraphNode>>(new Map());

  /* ── initial load ──────────────────────────────────────────── */

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [topics, parties] = await Promise.all([fetchTopics(), fetchParties()]);
        setAllTopics(topics);
        setAllParties(parties);

        const topicPositions = circleLayout(0, 0, topics.length, 400);
        const partyPositions = circleLayout(0, 0, parties.length, 200);

        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        topics.forEach((t, i) => {
          const id = `topic::${t.name}`;
          const size = Math.max(60, Math.min(140, 60 + t.argument_count * 2));
          graphNodes.current.set(id, {
            id,
            type: "Topic",
            label: t.name,
            properties: { name_en: t.name_en, category: t.category, argument_count: t.argument_count },
          });
          newNodes.push({
            id,
            position: topicPositions[i],
            data: { label: t.name, nodeType: "Topic", count: t.argument_count, name_en: t.name_en },
            style: {
              background: TYPE_COLORS.Topic,
              color: "#fff",
              border: "2px solid #60A5FA",
              borderRadius: "12px",
              padding: "12px 16px",
              fontSize: "13px",
              fontWeight: 600,
              width: size,
              textAlign: "center" as const,
              cursor: "pointer",
            },
          });
        });

        parties.forEach((p, i) => {
          const id = `party::${p.shortname}`;
          const color = PARTY_COLORS[p.shortname] || "#888";
          graphNodes.current.set(id, {
            id,
            type: "Party",
            label: p.shortname,
            properties: { name: p.name, ideology: p.ideology, argument_count: p.argument_count },
          });
          newNodes.push({
            id,
            position: partyPositions[i],
            data: { label: p.shortname, nodeType: "Party", count: p.argument_count, name: p.name },
            style: {
              background: color,
              color: p.shortname === "JOBBIK" ? "#fff" : "#000",
              border: `2px solid ${color}`,
              borderRadius: "50%",
              width: 70,
              height: 70,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "11px",
              fontWeight: 700,
              cursor: "pointer",
            },
          });
        });

        setNodes(newNodes);
        setEdges(newEdges);
      } catch (e) {
        console.error("Failed to load overview:", e);
      }
      setLoading(false);
    })();
  }, []);

  /* ── expand node ───────────────────────────────────────────── */

  const expandNode = useCallback(
    async (nodeId: string) => {
      if (expanded.has(nodeId)) return;
      setLoading(true);

      const gn = graphNodes.current.get(nodeId);
      if (!gn) {
        setLoading(false);
        return;
      }

      try {
        const data = await fetchNeighborhood(gn.type, gn.label, 1, 30);

        // Find parent position
        const parentNode = nodes.find((n) => n.id === nodeId);
        const px = parentNode?.position.x ?? 0;
        const py = parentNode?.position.y ?? 0;

        // Filter out nodes we already have
        const newGraphNodes = data.nodes.filter((n) => !graphNodes.current.has(n.id));
        const positions = circleLayout(px, py, newGraphNodes.length, 250);

        const newFlowNodes: Node[] = newGraphNodes.map((n, i) => {
          graphNodes.current.set(n.id, n);
          const isArg = n.type === "Argument";
          const sentiment = (n.properties?.sentiment as string) || "neutral";
          const sentimentColor =
            sentiment === "for" ? "#22C55E" : sentiment === "against" ? "#EF4444" : "#6B7280";

          return {
            id: n.id,
            position: positions[i],
            data: {
              label: n.label,
              nodeType: n.type,
              ...n.properties,
            },
            style: isArg
              ? {
                  background: "#1E293B",
                  color: "#E2E8F0",
                  border: `2px solid ${sentimentColor}`,
                  borderLeft: `5px solid ${sentimentColor}`,
                  borderRadius: "8px",
                  padding: "8px 10px",
                  fontSize: "11px",
                  width: 220,
                  cursor: "pointer",
                  lineHeight: "1.3",
                }
              : {
                  background: TYPE_COLORS[n.type] || "#475569",
                  color: "#fff",
                  border: `2px solid ${TYPE_COLORS[n.type] || "#475569"}`,
                  borderRadius: n.type === "Party" ? "50%" : "8px",
                  padding: "8px 12px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                },
          };
        });

        const newFlowEdges: Edge[] = data.edges
          .filter(
            (e) =>
              graphNodes.current.has(e.source) && graphNodes.current.has(e.target)
          )
          .map((e, i) => ({
            id: `e-${e.source}-${e.target}-${e.type}-${i}`,
            source: e.source,
            target: e.target,
            label: e.type === "REBUTS" || e.type === "SUPPORTS" || e.type === "CONTRADICTS" ? e.type : undefined,
            style: EDGE_STYLES[e.type] || { stroke: "#475569" },
            markerEnd:
              e.type === "REBUTS" || e.type === "SUPPORTS" || e.type === "CONTRADICTS"
                ? { type: MarkerType.ArrowClosed, color: EDGE_STYLES[e.type]?.stroke || "#475569" }
                : undefined,
            animated: e.type === "REBUTS",
          }));

        setNodes((prev) => [...prev, ...newFlowNodes]);
        setEdges((prev) => {
          const existingIds = new Set(prev.map((e) => e.id));
          const unique = newFlowEdges.filter((e) => !existingIds.has(e.id));
          return [...prev, ...unique];
        });
        setExpanded((prev) => new Set(prev).add(nodeId));
      } catch (e) {
        console.error("Failed to expand node:", e);
      }
      setLoading(false);
    },
    [expanded, nodes, setNodes, setEdges]
  );

  /* ── click handler ─────────────────────────────────────────── */

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      const gn = graphNodes.current.get(node.id);
      setSelected(gn ?? null);
      expandNode(node.id);
    },
    [expandNode]
  );

  /* ── keyboard shortcuts ────────────────────────────────────── */

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  /* ── filtered nodes/edges ──────────────────────────────────── */

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const data = n.data as Record<string, unknown>;
      if (data.nodeType === "Topic" && hiddenTopics.has(n.id.replace("topic::", ""))) return false;
      if (data.nodeType === "Party" && hiddenParties.has(n.id.replace("party::", ""))) return false;
      if (searchQuery) {
        const label = String(data.label || "").toLowerCase();
        if (!label.includes(searchQuery.toLowerCase())) return false;
      }
      return true;
    });
  }, [nodes, hiddenTopics, hiddenParties, searchQuery]);

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return edges.filter((e) => {
      if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
      const label = (e.label as string) || e.style?.stroke || "";
      // Check hidden relationship types
      for (const rel of hiddenRelTypes) {
        if (e.id.includes(rel)) return false;
      }
      return true;
    });
  }, [edges, visibleNodeIds, hiddenRelTypes]);

  /* ── render ────────────────────────────────────────────────── */

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0F172A", position: "relative" }}>
      <Link
        to="/"
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          zIndex: 20,
          color: "#94A3B8",
          textDecoration: "none",
          fontSize: 13,
        }}
      >
        &larr; Home
      </Link>

      {loading && (
        <div
          style={{
            position: "absolute",
            top: 12,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 20,
            background: "#1E40AF",
            color: "#fff",
            padding: "6px 16px",
            borderRadius: 8,
            fontSize: 13,
          }}
        >
          Loading...
        </div>
      )}

      <FilterPanel
        topics={allTopics}
        parties={allParties}
        hiddenTopics={hiddenTopics}
        hiddenParties={hiddenParties}
        hiddenRelTypes={hiddenRelTypes}
        searchQuery={searchQuery}
        onToggleTopic={(name) =>
          setHiddenTopics((prev) => {
            const next = new Set(prev);
            next.has(name) ? next.delete(name) : next.add(name);
            return next;
          })
        }
        onToggleParty={(name) =>
          setHiddenParties((prev) => {
            const next = new Set(prev);
            next.has(name) ? next.delete(name) : next.add(name);
            return next;
          })
        }
        onToggleRelType={(rel) =>
          setHiddenRelTypes((prev) => {
            const next = new Set(prev);
            next.has(rel) ? next.delete(rel) : next.add(rel);
            return next;
          })
        }
        onSearch={setSearchQuery}
        onReset={() => {
          setHiddenTopics(new Set());
          setHiddenParties(new Set());
          setHiddenRelTypes(new Set());
          setSearchQuery("");
        }}
      />

      <ReactFlow
        nodes={filteredNodes}
        edges={filteredEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        minZoom={0.1}
        maxZoom={3}
        style={{ background: "#0F172A" }}
      >
        <Background variant={BackgroundVariant.Dots} color="#1E293B" gap={20} />
        <Controls
          style={{ background: "#1E293B", borderColor: "#334155", borderRadius: 8 }}
        />
        <MiniMap
          style={{ background: "#1E293B", borderColor: "#334155" }}
          nodeColor={(n) => {
            const data = n.data as Record<string, unknown>;
            const t = data.nodeType as string;
            if (t === "Party") return PARTY_COLORS[n.id.replace("party::", "")] || "#888";
            return TYPE_COLORS[t] || "#475569";
          }}
        />
      </ReactFlow>

      {selected && (
        <NodeDetail node={selected} onClose={() => setSelected(null)} onExpand={expandNode} />
      )}
    </div>
  );
}
