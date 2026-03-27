import type { TopicInfo, PartyInfo, GraphStats, ArgumentSummary } from "../types";

const BASE = "/v2/graph";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

/** Fetch all topics with argument counts. */
export function fetchTopics(): Promise<TopicInfo[]> {
  return fetchJson<TopicInfo[]>(`${BASE}/topics`);
}

/** Fetch all parties with argument counts. */
export function fetchParties(): Promise<PartyInfo[]> {
  return fetchJson<PartyInfo[]>(`${BASE}/parties`);
}

/** Fetch graph-wide statistics. */
export function fetchStats(): Promise<GraphStats> {
  return fetchJson<GraphStats>(`${BASE}/stats`);
}

/** Fetch arguments, optionally filtered by topic and/or party. */
export function fetchArguments(params?: {
  topic?: string;
  party?: string;
  limit?: number;
}): Promise<ArgumentSummary[]> {
  const qs = new URLSearchParams();
  if (params?.topic) qs.set("topic", params.topic);
  if (params?.party) qs.set("party", params.party);
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return fetchJson<ArgumentSummary[]>(`${BASE}/arguments${suffix}`);
}

/** Compare all parties on a given topic. */
export function fetchCompare(topic: string): Promise<Record<string, string[]>> {
  return fetchJson<Record<string, string[]>>(
    `${BASE}/compare/${encodeURIComponent(topic)}`
  );
}

/** Fetch graph overview (all topics + parties with connections). */
export function fetchOverview(): Promise<import("../types").GraphData> {
  return fetchJson<import("../types").GraphData>(`${BASE}/overview`);
}

/** Fetch neighborhood around a node. */
export function fetchNeighborhood(
  nodeType: string,
  nodeName: string,
  depth: number = 1,
  limit: number = 50,
): Promise<import("../types").GraphData> {
  const qs = new URLSearchParams({
    node_type: nodeType,
    node_name: nodeName,
    depth: String(depth),
    limit: String(limit),
  });
  return fetchJson<import("../types").GraphData>(`${BASE}/neighborhood?${qs}`);
}
