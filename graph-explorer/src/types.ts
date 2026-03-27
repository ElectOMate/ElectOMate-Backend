/** Shared types for the graph explorer. */

export interface GraphNode {
  id: string;
  type: "Topic" | "Party" | "Argument" | "Politician" | "Source";
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type:
    | "ABOUT"
    | "MADE_BY"
    | "SUPPORTS"
    | "REBUTS"
    | "CONTRADICTS"
    | "SOURCED_FROM";
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/** API response types matching backend Pydantic models */

export interface TopicInfo {
  name: string;
  name_en: string | null;
  category: string | null;
  argument_count: number;
}

export interface PartyInfo {
  shortname: string;
  name: string | null;
  ideology: string | null;
  argument_count: number;
}

export interface GraphStats {
  total_arguments: number;
  total_topics: number;
  total_parties: number;
  total_politicians: number;
  total_sources: number;
  total_relationships: number;
}

export interface ArgumentSummary {
  text: string;
  summary: string | null;
  argument_type: string | null;
  sentiment: string | null;
  strength: number | null;
  party: string | null;
  politician: string | null;
  topics: string[];
}

/** Party color mapping */
export const PARTY_COLORS: Record<string, string> = {
  FIDESZ: "#FF6600",
  TISZA: "#00B4D8",
  DK: "#0066CC",
  MI_HAZANK: "#006633",
  MKKP: "#FFD700",
  JOBBIK: "#1a1a1a",
  MSZP: "#CC0000",
};
