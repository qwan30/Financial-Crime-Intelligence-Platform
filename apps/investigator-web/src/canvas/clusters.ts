import type { TraceEdgeResponse, TraceGraphResponse } from "../api";
import type { Projection, ViewState } from "./model";

export type FundingCluster = {
  id: string;
  targetId: string;
  memberNodeIds: string[];
  memberEdgeIds: string[];
  amountVnd: bigint;
  firstMs: number;
  lastMs: number;
};

export type ClusterBundle = {
  id: string;
  source: string;
  target: string;
  memberEdgeIds: string[];
  currency: string | null;
  amountVnd: bigint | null;
  firstMs: number;
  lastMs: number;
};

export type ClusterProjection = {
  clusters: FundingCluster[];
  ownerByNodeId: Map<string, string>;
  bundles: ClusterBundle[];
};

export function fundingClusters(
  trace: TraceGraphResponse,
  cutoffMs: number | null
): FundingCluster[] {
  const seedNode = trace.nodes.find((n) => n.isSeed);
  const seedId = seedNode ? seedNode.nodeId : null;

  // 1. Filter eligible VND edges
  const eligibleEdges: Array<{ edge: TraceEdgeResponse; timeMs: number }> = [];
  for (const e of trace.edges) {
    if (e.currency !== "VND") continue;
    if (e.flowAmount <= 0 || e.flowAmount >= 50_000_000) continue;
    if (e.source === e.target) continue;
    if (e.source === seedId) continue; // seed cannot be a cluster member
    if (!e.timestamp) continue;

    const ms = Date.parse(e.timestamp);
    if (!Number.isFinite(ms)) continue;
    if (cutoffMs !== null && ms > cutoffMs) continue;

    eligibleEdges.push({ edge: e, timeMs: ms });
  }

  // 2. Group by target
  const edgesByTarget = new Map<
    string,
    Array<{ edge: TraceEdgeResponse; timeMs: number }>
  >();
  for (const item of eligibleEdges) {
    let list = edgesByTarget.get(item.edge.target);
    if (!list) {
      list = [];
      edgesByTarget.set(item.edge.target, list);
    }
    list.push(item);
  }

  // Sort each target's edges by (timestamp, edgeId)
  for (const list of edgesByTarget.values()) {
    list.sort(
      (a, b) => a.timeMs - b.timeMs || a.edge.edgeId.localeCompare(b.edge.edgeId)
    );
  }

  // 3. Slide 1-hour window (3,600,000 ms)
  type Candidate = {
    targetId: string;
    firstMs: number;
    lastMs: number;
    sources: string[];
    edges: Array<{ edge: TraceEdgeResponse; timeMs: number }>;
  };

  const candidates: Candidate[] = [];

  for (const [targetId, list] of edgesByTarget.entries()) {
    for (let i = 0; i < list.length; i++) {
      const startMs = list[i].timeMs;
      const windowEndMs = startMs + 3_600_000;
      const windowEdges: Array<{ edge: TraceEdgeResponse; timeMs: number }> = [];
      const distinctSources = new Set<string>();

      for (let j = i; j < list.length; j++) {
        if (list[j].timeMs <= windowEndMs) {
          windowEdges.push(list[j]);
          distinctSources.add(list[j].edge.source);
        } else {
          break;
        }
      }

      if (distinctSources.size >= 5) {
        const sortedSources = Array.from(distinctSources).sort((a, b) => a.localeCompare(b));
        candidates.push({
          targetId,
          firstMs: windowEdges[0].timeMs,
          lastMs: windowEdges[windowEdges.length - 1].timeMs,
          sources: sortedSources,
          edges: windowEdges,
        });
      }
    }
  }

  // 4. Sort candidates deterministically: targetId, firstMs, sources
  candidates.sort(
    (a, b) =>
      a.targetId.localeCompare(b.targetId) ||
      a.firstMs - b.firstMs ||
      a.sources.join("|").localeCompare(b.sources.join("|"))
  );

  // 5. Greedy non-overlapping assignment
  const assignedSources = new Set<string>();
  const acceptedClusters: FundingCluster[] = [];

  for (const cand of candidates) {
    const availableSources = cand.sources.filter((s) => !assignedSources.has(s));
    if (availableSources.length >= 5) {
      const availSet = new Set(availableSources);
      for (const s of availableSources) {
        assignedSources.add(s);
      }

      const memberEdges = cand.edges.filter((item) =>
        availSet.has(item.edge.source)
      );
      const memberEdgeIds = Array.from(
        new Set(memberEdges.map((m) => m.edge.edgeId))
      ).sort((a, b) => a.localeCompare(b));

      let totalVnd = 0n;
      let minMs = Number.MAX_SAFE_INTEGER;
      let maxMs = 0;

      for (const m of memberEdges) {
        totalVnd += BigInt(Math.round(m.edge.flowAmount));
        if (m.timeMs < minMs) minMs = m.timeMs;
        if (m.timeMs > maxMs) maxMs = m.timeMs;
      }

      const clusterId = `cluster:${encodeURIComponent(
        cand.targetId
      )}:${availableSources.map(encodeURIComponent).join("|")}`;

      acceptedClusters.push({
        id: clusterId,
        targetId: cand.targetId,
        memberNodeIds: availableSources.sort((a, b) => a.localeCompare(b)),
        memberEdgeIds,
        amountVnd: totalVnd,
        firstMs: minMs,
        lastMs: maxMs,
      });
    }
  }

  return acceptedClusters;
}

export function clusterProjection(
  trace: TraceGraphResponse,
  view: ViewState,
  projection: Projection,
  clusters: readonly FundingCluster[]
): ClusterProjection {
  const ownerByNodeId = new Map<string, string>();

  // Map unexpanded cluster members to their cluster ID
  for (const cluster of clusters) {
    if (!view.expandedClusterIds.has(cluster.id)) {
      for (const memberId of cluster.memberNodeIds) {
        ownerByNodeId.set(memberId, cluster.id);
      }
    }
  }

  // Create bundles for visible real edges touching collapsed members
  type BundleBuilder = {
    source: string;
    target: string;
    memberEdgeIds: string[];
    currency: string | null;
    amountVnd: bigint | null;
    firstMs: number;
    lastMs: number;
  };

  const vndBundles = new Map<string, BundleBuilder>();
  const singleBundles: ClusterBundle[] = [];

  for (const edge of trace.edges) {
    if (!projection.visibleEdgeIds.has(edge.edgeId)) continue;

    const mappedSource = ownerByNodeId.get(edge.source) ?? edge.source;
    const mappedTarget = ownerByNodeId.get(edge.target) ?? edge.target;

    // If neither endpoint is collapsed, no bundle
    if (mappedSource === edge.source && mappedTarget === edge.target) {
      continue;
    }

    // If internal to the same cluster, skip bundle (listed in inspector)
    if (mappedSource === mappedTarget) {
      continue;
    }

    const eventMs = edge.timestamp ? Date.parse(edge.timestamp) : 0;
    const validTime = Number.isFinite(eventMs) ? eventMs : 0;

    if (edge.currency === "VND") {
      const bundleKey = `${mappedSource}->${mappedTarget}`;
      let b = vndBundles.get(bundleKey);
      if (!b) {
        b = {
          source: mappedSource,
          target: mappedTarget,
          memberEdgeIds: [],
          currency: "VND",
          amountVnd: 0n,
          firstMs: validTime,
          lastMs: validTime,
        };
        vndBundles.set(bundleKey, b);
      }
      b.memberEdgeIds.push(edge.edgeId);
      b.amountVnd = (b.amountVnd ?? 0n) + BigInt(Math.round(edge.flowAmount));
      if (validTime > 0) {
        if (b.firstMs === 0 || validTime < b.firstMs) b.firstMs = validTime;
        if (validTime > b.lastMs) b.lastMs = validTime;
      }
    } else {
      // Non-VND single member bundle
      singleBundles.push({
        id: `bundle:${encodeURIComponent(mappedSource)}:${encodeURIComponent(
          mappedTarget
        )}:${encodeURIComponent(edge.edgeId)}`,
        source: mappedSource,
        target: mappedTarget,
        memberEdgeIds: [edge.edgeId],
        currency: edge.currency,
        amountVnd: null,
        firstMs: validTime,
        lastMs: validTime,
      });
    }
  }

  const bundles: ClusterBundle[] = [];
  for (const b of vndBundles.values()) {
    b.memberEdgeIds.sort((a, b) => a.localeCompare(b));
    bundles.push({
      id: `bundle:${encodeURIComponent(b.source)}:${encodeURIComponent(
        b.target
      )}`,
      source: b.source,
      target: b.target,
      memberEdgeIds: b.memberEdgeIds,
      currency: b.currency,
      amountVnd: b.amountVnd,
      firstMs: b.firstMs,
      lastMs: b.lastMs,
    });
  }

  bundles.push(...singleBundles);
  bundles.sort((a, b) => a.id.localeCompare(b.id));

  return {
    clusters: Array.from(clusters),
    ownerByNodeId,
    bundles,
  };
}
