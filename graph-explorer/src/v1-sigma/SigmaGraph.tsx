import { useEffect, useRef, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";

import { fetchTopics, fetchParties, fetchArguments } from "../api/graphApi";
import type { TopicInfo, PartyInfo, ArgumentSummary } from "../types";
import { PARTY_COLORS } from "../types";

/* ============================================================================
   Constants
   ============================================================================ */

const TOPIC_COLOR = "#38bdf8";
const ARGUMENT_COLOR = "#a78bfa";
const DEFAULT_PARTY_COLOR = "#64748b";

/* ============================================================================
   Component
   ============================================================================ */

export default function SigmaGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [parties, setParties] = useState<PartyInfo[]>([]);
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    label: string;
    type: string;
    detail: string;
  } | null>(null);

  /* ---------- Build initial graph from topics + parties ---------- */

  const buildGraph = useCallback(
    (topicData: TopicInfo[], partyData: PartyInfo[]) => {
      const graph = new Graph();

      // Add topic nodes
      for (const t of topicData) {
        const size = Math.max(8, Math.min(30, 8 + t.argument_count * 0.3));
        graph.addNode(`topic:${t.name}`, {
          label: t.name,
          size,
          color: TOPIC_COLOR,
          x: Math.random() * 100,
          y: Math.random() * 100,
          nodeType: "Topic",
          argumentCount: t.argument_count,
          nameEn: t.name_en,
          category: t.category,
        });
      }

      // Add party nodes
      for (const p of partyData) {
        const color = PARTY_COLORS[p.shortname] ?? DEFAULT_PARTY_COLOR;
        const size = Math.max(12, Math.min(35, 12 + p.argument_count * 0.15));
        graph.addNode(`party:${p.shortname}`, {
          label: p.shortname,
          size,
          color,
          x: Math.random() * 100,
          y: Math.random() * 100,
          nodeType: "Party",
          argumentCount: p.argument_count,
          fullName: p.name,
          ideology: p.ideology,
        });
      }

      // Add edges between every party and every topic
      // Weight by shared argument potential (topic_args * party_args / total)
      const totalArgs = topicData.reduce((s, t) => s + t.argument_count, 0) || 1;
      for (const t of topicData) {
        for (const p of partyData) {
          if (t.argument_count > 0 && p.argument_count > 0) {
            const weight =
              (t.argument_count * p.argument_count) / totalArgs;
            if (weight > 0.5) {
              graph.addEdge(`topic:${t.name}`, `party:${p.shortname}`, {
                size: Math.max(0.5, Math.min(3, weight * 0.1)),
                color: "#334155",
              });
            }
          }
        }
      }

      // Run ForceAtlas2 layout
      forceAtlas2.assign(graph, {
        iterations: 100,
        settings: {
          gravity: 1,
          scalingRatio: 10,
          barnesHutOptimize: true,
          slowDown: 5,
        },
      });

      return graph;
    },
    []
  );

  /* ---------- Expand node: fetch arguments and add to graph ---------- */

  const expandNode = useCallback(
    async (nodeId: string) => {
      const graph = graphRef.current;
      if (!graph) return;

      const [nodeType, nodeName] = nodeId.split(":");
      if (!nodeType || !nodeName) return;

      // Fetch arguments for this node
      let args: ArgumentSummary[];
      try {
        if (nodeType === "topic") {
          args = await fetchArguments({ topic: nodeName, limit: 15 });
        } else if (nodeType === "party") {
          args = await fetchArguments({ party: nodeName, limit: 15 });
        } else {
          return;
        }
      } catch {
        console.warn("Could not fetch arguments for", nodeId);
        return;
      }

      // Add argument nodes around the expanded node
      const parentAttrs = graph.getNodeAttributes(nodeId);
      const px = parentAttrs.x as number;
      const py = parentAttrs.y as number;

      for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        const argId = `arg:${nodeId}:${i}`;
        if (graph.hasNode(argId)) continue;

        const angle = (2 * Math.PI * i) / args.length;
        const radius = 15 + Math.random() * 5;

        const label =
          (arg.summary ?? arg.text).slice(0, 60) +
          ((arg.summary ?? arg.text).length > 60 ? "..." : "");

        graph.addNode(argId, {
          label,
          size: 5,
          color: ARGUMENT_COLOR,
          x: px + Math.cos(angle) * radius,
          y: py + Math.sin(angle) * radius,
          nodeType: "Argument",
          fullText: arg.text,
          party: arg.party,
          sentiment: arg.sentiment,
          strength: arg.strength,
        });

        graph.addEdge(nodeId, argId, {
          size: 0.5,
          color: "#475569",
        });

        // Link argument to its party if present
        if (arg.party) {
          const partyNode = `party:${arg.party}`;
          if (graph.hasNode(partyNode) && !graph.hasEdge(argId, partyNode)) {
            graph.addEdge(argId, partyNode, {
              size: 0.5,
              color: PARTY_COLORS[arg.party] ?? "#475569",
            });
          }
        }
      }

      // Re-run a short layout pass
      forceAtlas2.assign(graph, {
        iterations: 50,
        settings: {
          gravity: 1,
          scalingRatio: 10,
          barnesHutOptimize: true,
          slowDown: 10,
        },
      });

      sigmaRef.current?.refresh();
    },
    []
  );

  /* ---------- Initialize ---------- */

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const [topicData, partyData] = await Promise.all([
          fetchTopics(),
          fetchParties(),
        ]);

        if (cancelled) return;

        setTopics(topicData);
        setParties(partyData);

        const graph = buildGraph(topicData, partyData);
        graphRef.current = graph;

        if (!containerRef.current) return;

        const sigma = new Sigma(graph, containerRef.current, {
          renderEdgeLabels: false,
          enableEdgeEvents: false,
          defaultEdgeType: "line",
          labelColor: { color: "#e2e8f0" },
          labelSize: 12,
          labelRenderedSizeThreshold: 6,
        });

        sigmaRef.current = sigma;

        // --- Interactions ---

        // Single click: highlight neighbors
        sigma.on("clickNode", ({ node }) => {
          setHighlightedNode((prev) => (prev === node ? null : node));
        });

        // Double click: expand node (fetch arguments)
        sigma.on("doubleClickNode", ({ node, event }) => {
          event.original.preventDefault();
          expandNode(node);
        });

        // Hover: show tooltip
        sigma.on("enterNode", ({ node }) => {
          const attrs = graph.getNodeAttributes(node);
          const pos = sigma.graphToViewport({
            x: attrs.x as number,
            y: attrs.y as number,
          });

          let detail = "";
          if (attrs.nodeType === "Topic") {
            detail = `${attrs.argumentCount} arguments`;
            if (attrs.nameEn) detail += ` | ${attrs.nameEn}`;
          } else if (attrs.nodeType === "Party") {
            detail = `${attrs.argumentCount} arguments`;
            if (attrs.ideology) detail += ` | ${attrs.ideology}`;
          } else if (attrs.nodeType === "Argument") {
            detail = (attrs.fullText as string)?.slice(0, 120) ?? "";
            if (attrs.party) detail += ` [${attrs.party}]`;
          }

          setTooltip({
            x: pos.x + 15,
            y: pos.y - 10,
            label: attrs.label as string,
            type: attrs.nodeType as string,
            detail,
          });
        });

        sigma.on("leaveNode", () => {
          setTooltip(null);
        });

        // Click background to reset highlight
        sigma.on("clickStage", () => {
          setHighlightedNode(null);
        });

        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      sigmaRef.current?.kill();
      sigmaRef.current = null;
    };
  }, [buildGraph, expandNode]);

  /* ---------- Highlight reducer ---------- */

  useEffect(() => {
    const sigma = sigmaRef.current;
    const graph = graphRef.current;
    if (!sigma || !graph) return;

    if (highlightedNode) {
      const neighbors = new Set(graph.neighbors(highlightedNode));
      neighbors.add(highlightedNode);

      sigma.setSetting("nodeReducer", (node, data) => {
        if (neighbors.has(node)) return data;
        return { ...data, color: "#1e293b", label: "" };
      });

      sigma.setSetting("edgeReducer", (edge, data) => {
        const [source, target] = graph.extremities(edge);
        if (neighbors.has(source) && neighbors.has(target)) return data;
        return { ...data, color: "#0f172a", hidden: true };
      });
    } else {
      sigma.setSetting("nodeReducer", null);
      sigma.setSetting("edgeReducer", null);
    }

    sigma.refresh();
  }, [highlightedNode]);

  /* ---------- Search filtering ---------- */

  const searchResults = searchQuery.trim()
    ? [
        ...topics
          .filter((t) =>
            t.name.toLowerCase().includes(searchQuery.toLowerCase())
          )
          .map((t) => ({ id: `topic:${t.name}`, label: t.name, type: "topic" as const })),
        ...parties
          .filter((p) =>
            p.shortname.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (p.name ?? "").toLowerCase().includes(searchQuery.toLowerCase())
          )
          .map((p) => ({
            id: `party:${p.shortname}`,
            label: p.shortname,
            type: "party" as const,
          })),
      ].slice(0, 10)
    : [];

  const focusNode = (nodeId: string) => {
    const sigma = sigmaRef.current;
    const graph = graphRef.current;
    if (!sigma || !graph || !graph.hasNode(nodeId)) return;

    const attrs = graph.getNodeAttributes(nodeId);
    const camera = sigma.getCamera();
    camera.animate(
      { x: attrs.x as number, y: attrs.y as number, ratio: 0.3 },
      { duration: 400 }
    );
    setHighlightedNode(nodeId);
    setSearchQuery("");
  };

  /* ---------- Render ---------- */

  if (error) {
    return (
      <div className="graph-container">
        <div className="error-banner">Failed to load: {error}</div>
        <div ref={containerRef} className="sigma-container" />
      </div>
    );
  }

  return (
    <div className="graph-container">
      {loading && (
        <div className="loading-overlay">
          <div className="spinner" />
          Loading graph data...
        </div>
      )}

      <Link to="/" className="back-link">
        Home
      </Link>

      {/* Sigma canvas — must always be in DOM for ref */}
      <div ref={containerRef} className="sigma-container" />

      {/* Search */}
      <div className="panel search-panel">
        <input
          type="text"
          placeholder="Search topics or parties..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchResults.length > 0 && (
          <div className="search-results">
            {searchResults.map((r) => (
              <button key={r.id} onClick={() => focusNode(r.id)}>
                <span className={`type-badge ${r.type}`}>{r.type}</span>
                {r.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="panel legend-panel">
        <h3>Legend</h3>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: TOPIC_COLOR }} />
          Topics (sized by arguments)
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: ARGUMENT_COLOR }} />
          Arguments (double-click to expand)
        </div>
        <hr style={{ borderColor: "#334155", margin: "0.5rem 0" }} />
        <h3>Parties</h3>
        {parties.map((p) => (
          <div key={p.shortname} className="legend-item">
            <span
              className="legend-dot"
              style={{
                background: PARTY_COLORS[p.shortname] ?? DEFAULT_PARTY_COLOR,
              }}
            />
            {p.shortname}
            {p.name ? ` - ${p.name}` : ""}
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="panel stats-panel">
        <h3>Graph</h3>
        <div className="stat-row">
          <span>Topics</span>
          <span className="value">{topics.length}</span>
        </div>
        <div className="stat-row">
          <span>Parties</span>
          <span className="value">{parties.length}</span>
        </div>
        <div className="stat-row">
          <span>Nodes</span>
          <span className="value">
            {graphRef.current?.order ?? 0}
          </span>
        </div>
        <div className="stat-row">
          <span>Edges</span>
          <span className="value">
            {graphRef.current?.size ?? 0}
          </span>
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="node-tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="node-type">{tooltip.type}</div>
          <h4>{tooltip.label}</h4>
          {tooltip.detail && <div className="node-detail">{tooltip.detail}</div>}
        </div>
      )}
    </div>
  );
}
