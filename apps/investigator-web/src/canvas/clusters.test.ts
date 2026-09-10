import { describe, expect, it } from "vitest";
import type { TraceEdgeResponse, TraceGraphResponse } from "../api";
import { clusterProjection, fundingClusters } from "./clusters";
import { initialView, projectGraph } from "./model";

describe("canvas clusters", () => {
  const makeEdge = (
    edgeId: string,
    source: string,
    target: string,
    flowAmount: number,
    minute: number,
    currency = "VND"
  ): TraceEdgeResponse => {
    const mm = minute.toString().padStart(2, "0");
    return {
      edgeId,
      source,
      target,
      flowAmount,
      currency,
      timestamp: `2026-09-08T08:${mm}:00+07:00`,
      relationshipType: "NAPAS_247",
      identityConfidence: 0.98,
    };
  };

  it("detects smurfing clusters with >= 5 distinct sources within 1 hour", () => {
    const nodes = [
      {
        nodeId: "hub",
        entityType: "ACCOUNT",
        riskScore: 0.88,
        isSeed: true,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      },
      ...["m1", "m2", "m3", "m4", "m5"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: 0.7,
        isSeed: false,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
    ];

    // 5 transfers to hub between 08:10 and 08:50 (within 1 hour, < 50M)
    const edges = [
      makeEdge("e1", "m1", "hub", 10_000_000, 10),
      makeEdge("e2", "m2", "hub", 25_000_000, 20),
      makeEdge("e3", "m3", "hub", 45_000_000, 30),
      makeEdge("e4", "m4", "hub", 20_000_000, 40),
      makeEdge("e5", "m5", "hub", 30_000_000, 50),
    ];

    const trace: TraceGraphResponse = {
      nodes,
      edges,
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { hub: 0, m1: 1, m2: 1, m3: 1, m4: 1, m5: 1 },
      timeMin: "2026-09-08T08:10:00+07:00",
      timeMax: "2026-09-08T08:50:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const clusters = fundingClusters(trace, null);
    expect(clusters.length).toBe(1);
    expect(clusters[0].targetId).toBe("hub");
    expect(clusters[0].memberNodeIds.sort()).toEqual(["m1", "m2", "m3", "m4", "m5"]);
    expect(clusters[0].amountVnd).toBe(130_000_000n);
  });

  it("does not qualify with 4 sources or repeated source from same account", () => {
    const nodes = [
      {
        nodeId: "hub",
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: true,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      },
      ...["m1", "m2", "m3", "m4"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: false,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
    ];

    // 5 transfers but only 4 distinct sources (m1 transferred twice)
    const edges = [
      makeEdge("e1", "m1", "hub", 10_000_000, 10),
      makeEdge("e1b", "m1", "hub", 10_000_000, 15),
      makeEdge("e2", "m2", "hub", 25_000_000, 20),
      makeEdge("e3", "m3", "hub", 45_000_000, 30),
      makeEdge("e4", "m4", "hub", 20_000_000, 40),
    ];

    const trace: TraceGraphResponse = {
      nodes,
      edges,
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { hub: 0, m1: 1, m2: 1, m3: 1, m4: 1 },
      timeMin: "2026-09-08T08:10:00+07:00",
      timeMax: "2026-09-08T08:40:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const clusters = fundingClusters(trace, null);
    expect(clusters.length).toBe(0);
  });

  it("enforces strict < 50M flowAmount rule", () => {
    const nodes = [
      {
        nodeId: "hub",
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: true,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      },
      ...["m1", "m2", "m3", "m4", "m5"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: false,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
    ];

    // m5 has 50_000_000 -> not strictly < 50_000_000!
    const edges = [
      makeEdge("e1", "m1", "hub", 10_000_000, 10),
      makeEdge("e2", "m2", "hub", 25_000_000, 20),
      makeEdge("e3", "m3", "hub", 45_000_000, 30),
      makeEdge("e4", "m4", "hub", 20_000_000, 40),
      makeEdge("e5", "m5", "hub", 50_000_000, 50),
    ];

    const trace: TraceGraphResponse = {
      nodes,
      edges,
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { hub: 0, m1: 1, m2: 1, m3: 1, m4: 1, m5: 1 },
      timeMin: "2026-09-08T08:10:00+07:00",
      timeMax: "2026-09-08T08:50:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const clusters = fundingClusters(trace, null);
    expect(clusters.length).toBe(0);
  });

  it("never includes the seed node as a cluster member", () => {
    const nodes = [
      {
        nodeId: "hub",
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: true,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      },
      ...["m1", "m2", "m3", "m4", "target"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: false,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
    ];

    // hub (seed) transfers to target along with m1..m4
    const edges = [
      makeEdge("e1", "m1", "target", 10_000_000, 10),
      makeEdge("e2", "m2", "target", 25_000_000, 20),
      makeEdge("e3", "m3", "target", 45_000_000, 30),
      makeEdge("e4", "m4", "target", 20_000_000, 40),
      makeEdge("e5", "hub", "target", 15_000_000, 50), // seed!
    ];

    const trace: TraceGraphResponse = {
      nodes,
      edges,
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { hub: 0, target: 1, m1: 1, m2: 1, m3: 1, m4: 1 },
      timeMin: "2026-09-08T08:10:00+07:00",
      timeMax: "2026-09-08T08:50:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const clusters = fundingClusters(trace, null);
    // hub is seed, cannot be member -> only 4 non-seed members -> does not qualify
    expect(clusters.length).toBe(0);
  });

  it("projects collapsed cluster bundles and preserves source trace immutability", () => {
    const nodes = [
      {
        nodeId: "hub",
        entityType: "ACCOUNT",
        riskScore: 0.88,
        isSeed: true,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      },
      ...["m1", "m2", "m3", "m4", "m5"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: 0.7,
        isSeed: false,
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
    ];

    const edges = [
      makeEdge("e1", "m1", "hub", 10_000_000, 10),
      makeEdge("e2", "m2", "hub", 25_000_000, 20),
      makeEdge("e3", "m3", "hub", 45_000_000, 30),
      makeEdge("e4", "m4", "hub", 20_000_000, 40),
      makeEdge("e5", "m5", "hub", 30_000_000, 50),
    ];

    const trace: TraceGraphResponse = {
      nodes,
      edges,
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { hub: 0, m1: 1, m2: 1, m3: 1, m4: 1, m5: 1 },
      timeMin: "2026-09-08T08:10:00+07:00",
      timeMax: "2026-09-08T08:50:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const originalJson = JSON.stringify(trace);
    const view = initialView(trace);
    const proj = projectGraph(trace, view);
    const clusters = fundingClusters(trace, view.cutoffMs);

    // Collapsed projection
    const cp = clusterProjection(trace, view, proj, clusters);
    expect(cp.clusters.length).toBe(1);
    expect(cp.ownerByNodeId.get("m1")).toBe(clusters[0].id);
    expect(cp.ownerByNodeId.get("hub")).toBeUndefined(); // hub is target, not member
    expect(cp.bundles.length).toBe(1);
    expect(cp.bundles[0].memberEdgeIds.sort()).toEqual(["e1", "e2", "e3", "e4", "e5"]);
    expect(cp.bundles[0].amountVnd).toBe(130_000_000n);

    // Expanded projection
    const expandedView = {
      ...view,
      expandedClusterIds: new Set([clusters[0].id]),
    };
    const cpExpanded = clusterProjection(trace, expandedView, proj, clusters);
    expect(cpExpanded.ownerByNodeId.size).toBe(0);
    expect(cpExpanded.bundles.length).toBe(0); // no bundles when expanded

    expect(JSON.stringify(trace)).toBe(originalJson);
  });
});
