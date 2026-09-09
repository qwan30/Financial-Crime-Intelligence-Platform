import type { TraceEdgeResponse, TraceGraphResponse } from "../api";

export type LayoutName = "causal" | "cose" | "concentric";

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | { kind: "cluster"; id: string }
  | { kind: "bundle"; id: string }
  | null;

export type ViewState = {
  cutoffMs: number | null;
  amountThresholdVnd: number;
  viewOverrideEdgeIds: ReadonlySet<string>;
  manuallyHiddenEdgeIds: ReadonlySet<string>;
  expandedClusterIds: ReadonlySet<string>;
  selection: Selection;
  focusedNodeId: string | null;
  layout: LayoutName;
};

export type HiddenFlow = {
  edgeIds: string[];
  amountVnd: bigint;
};

export type Projection = {
  visibleEdgeIds: Set<string>;
  amountHiddenByNode: Map<string, HiddenFlow>;
  unknownTimeEdgeIds: string[];
  futureEdgeIds: string[];
};

export function initialView(trace: TraceGraphResponse): ViewState {
  return {
    cutoffMs: trace.timeMax ? Date.parse(trace.timeMax) : null,
    amountThresholdVnd: 0,
    viewOverrideEdgeIds: new Set<string>(),
    manuallyHiddenEdgeIds: new Set<string>(),
    expandedClusterIds: new Set<string>(),
    selection: null,
    focusedNodeId: null,
    layout: "causal",
  };
}

export function projectGraph(
  trace: TraceGraphResponse,
  view: ViewState
): Projection {
  const visibleEdgeIds = new Set<string>();
  const unknownTimeEdgeIds: string[] = [];
  const futureEdgeIds: string[] = [];
  const hiddenMap = new Map<string, { edgeIds: string[]; amountVnd: bigint }>();

  for (const edge of trace.edges) {
    const eventMs =
      edge.timestamp === null ? NaN : Date.parse(edge.timestamp);
    const hasValidTime = Number.isFinite(eventMs);

    if (!hasValidTime) {
      unknownTimeEdgeIds.push(edge.edgeId);
    } else if (view.cutoffMs !== null && eventMs > view.cutoffMs) {
      futureEdgeIds.push(edge.edgeId);
    }

    const temporal =
      hasValidTime && view.cutoffMs !== null && eventMs <= view.cutoffMs;
    const manuallyHidden = view.manuallyHiddenEdgeIds.has(edge.edgeId);
    const amountHidden =
      edge.currency === "VND" &&
      edge.flowAmount < view.amountThresholdVnd &&
      !view.viewOverrideEdgeIds.has(edge.edgeId);

    const visible = temporal && !manuallyHidden && !amountHidden;

    if (visible) {
      visibleEdgeIds.add(edge.edgeId);
    }

    if (temporal && !manuallyHidden && amountHidden) {
      const endpoints =
        edge.source === edge.target
          ? [edge.source]
          : [edge.source, edge.target];

      const flowBigInt = BigInt(Math.round(edge.flowAmount));
      for (const ep of endpoints) {
        let entry = hiddenMap.get(ep);
        if (!entry) {
          entry = { edgeIds: [], amountVnd: 0n };
          hiddenMap.set(ep, entry);
        }
        entry.edgeIds.push(edge.edgeId);
        entry.amountVnd += flowBigInt;
      }
    }
  }

  const amountHiddenByNode = new Map<string, HiddenFlow>();
  for (const [nodeId, entry] of hiddenMap.entries()) {
    const uniqueSorted = Array.from(new Set(entry.edgeIds)).sort();
    amountHiddenByNode.set(nodeId, {
      edgeIds: uniqueSorted,
      amountVnd: entry.amountVnd,
    });
  }

  return {
    visibleEdgeIds,
    amountHiddenByNode,
    unknownTimeEdgeIds,
    futureEdgeIds,
  };
}

export function formatVndMillions(amount: bigint): string {
  const sign = amount < 0n ? "-" : "";
  const abs = amount < 0n ? -amount : amount;
  const whole = abs / 1_000_000n;
  const rem = abs % 1_000_000n;

  let frac = rem.toString().padStart(6, "0");
  while (frac.length > 1 && frac.endsWith("0")) {
    frac = frac.slice(0, -1);
  }

  return `${sign}${whole.toString()}.${frac} tr`;
}

export function formatTransaction(edge: TraceEdgeResponse): string {
  let timeStr = "";
  if (edge.timestamp) {
    const d = new Date(edge.timestamp);
    if (!isNaN(d.getTime())) {
      timeStr = d.toLocaleTimeString("en-GB", {
        timeZone: "Asia/Ho_Chi_Minh",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }
  }

  if (edge.currency === "VND") {
    const formatted = formatVndMillions(BigInt(Math.round(edge.flowAmount)));
    return timeStr ? `${formatted} (${timeStr})` : formatted;
  }

  if (edge.currency === null || edge.currency === undefined) {
    return `${edge.flowAmount} · Chưa rõ tiền tệ`;
  }

  const base = `${edge.flowAmount} ${edge.currency}`;
  return timeStr ? `${base} (${timeStr})` : base;
}

export function edgeWidth(edge: TraceEdgeResponse): number {
  if (edge.currency === "VND") {
    if (edge.flowAmount >= 100_000_000) return 4.5;
    if (edge.flowAmount >= 40_000_000) return 3.0;
    return 1.8;
  }
  return 1.8;
}

export function focusedElements(
  trace: TraceGraphResponse,
  visibleEdgeIds: ReadonlySet<string>,
  nodeId: string | null
): { nodeIds: Set<string>; edgeIds: Set<string> } {
  if (nodeId === null) {
    return { nodeIds: new Set<string>(), edgeIds: new Set<string>() };
  }

  const nodeIds = new Set<string>([nodeId]);
  const edgeIds = new Set<string>();

  const visibleEdges = trace.edges.filter((e) => visibleEdgeIds.has(e.edgeId));

  // 1. Closed neighborhood
  for (const e of visibleEdges) {
    if (e.source === nodeId || e.target === nodeId) {
      edgeIds.add(e.edgeId);
      nodeIds.add(e.source);
      nodeIds.add(e.target);
    }
  }

  // 2. Shortest undirected linkage path to seed
  const seedNode = trace.nodes.find((n) => n.isSeed);
  const seedId = seedNode ? seedNode.nodeId : null;

  if (seedId && seedId !== nodeId) {
    // Build adjacency
    const adj = new Map<string, Array<{ neighbor: string; edgeId: string }>>();
    for (const e of visibleEdges) {
      if (!adj.has(e.source)) adj.set(e.source, []);
      if (!adj.has(e.target)) adj.set(e.target, []);
      adj.get(e.source)!.push({ neighbor: e.target, edgeId: e.edgeId });
      adj.get(e.target)!.push({ neighbor: e.source, edgeId: e.edgeId });
    }

    // Sort adjacency deterministically
    for (const list of adj.values()) {
      list.sort((a, b) =>
        a.neighbor.localeCompare(b.neighbor) || a.edgeId.localeCompare(b.edgeId)
      );
    }

    // BFS from nodeId to seedId
    const queue: string[] = [nodeId];
    const prev = new Map<string, { parent: string; edgeId: string }>();
    const visited = new Set<string>([nodeId]);

    let found = false;
    while (queue.length > 0) {
      const curr = queue.shift()!;
      if (curr === seedId) {
        found = true;
        break;
      }
      for (const edgeInfo of adj.get(curr) ?? []) {
        if (!visited.has(edgeInfo.neighbor)) {
          visited.add(edgeInfo.neighbor);
          prev.set(edgeInfo.neighbor, { parent: curr, edgeId: edgeInfo.edgeId });
          queue.push(edgeInfo.neighbor);
        }
      }
    }

    if (found) {
      let cur = seedId;
      while (cur !== nodeId) {
        const p = prev.get(cur)!;
        nodeIds.add(cur);
        edgeIds.add(p.edgeId);
        cur = p.parent;
      }
    }
  }

  return { nodeIds, edgeIds };
}
