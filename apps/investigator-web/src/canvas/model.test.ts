import { describe, expect, it } from "vitest";
import type { TraceEdgeResponse, TraceGraphResponse } from "../api";
import {
  edgeWidth,
  focusedElements,
  formatTransaction,
  formatVndMillions,
  initialView,
  projectGraph,
} from "./model";

describe("canvas model", () => {
  it("reveals amount-hidden funding without revealing future money or changing facts", () => {
    const makeEdge = (
      edgeId: string,
      source: string,
      target: string,
      flowAmount: number,
      clock: string
    ): TraceEdgeResponse => ({
      edgeId,
      source,
      target,
      flowAmount,
      timestamp: `2026-09-08T${clock}:00+07:00`,
      currency: "VND",
      relationshipType: "NAPAS_247",
      identityConfidence: 0.98,
    });
    const trace: TraceGraphResponse = {
      nodes: ["hub", "mule1", "mule2", "mule3", "shell"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: nodeId === "hub",
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
      edges: [
        makeEdge("TXN-2026-8801", "mule1", "hub", 10_000_000, "08:30"),
        makeEdge("TXN-2026-8802", "mule2", "hub", 25_000_000, "08:40"),
        makeEdge("TXN-2026-8803", "mule3", "hub", 45_000_000, "08:55"),
        makeEdge("TXN-2026-8804", "hub", "shell", 140_000_000, "09:12"),
      ],
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { hub: 0, mule1: 1, mule2: 1, mule3: 1, shell: 1 },
      timeMin: "2026-09-08T08:30:00+07:00",
      timeMax: "2026-09-08T09:12:00+07:00",
      unknownTimeEdgeCount: 0,
    };
    const view = {
      ...initialView(trace),
      cutoffMs: Date.parse("2026-09-08T08:55:00+07:00"),
      amountThresholdVnd: 50_000_000,
    };
    const original = JSON.stringify(trace);
    const projection = projectGraph(trace, view);
    expect(projection.amountHiddenByNode.get("hub")).toEqual({
      edgeIds: ["TXN-2026-8801", "TXN-2026-8802", "TXN-2026-8803"],
      amountVnd: 80_000_000n,
    });
    const revealed = projectGraph(trace, {
      ...view,
      viewOverrideEdgeIds: new Set(["TXN-2026-8801", "TXN-2026-8804"]),
    });
    expect(revealed.visibleEdgeIds.has("TXN-2026-8801")).toBe(true);
    expect(revealed.visibleEdgeIds.has("TXN-2026-8804")).toBe(false);
    expect(JSON.stringify(trace)).toBe(original);
  });

  it("handles equality-at-cutoff and future edges", () => {
    const edge: TraceEdgeResponse = {
      edgeId: "e1",
      source: "a",
      target: "b",
      flowAmount: 50_000_000,
      currency: "VND",
      timestamp: "2026-09-08T10:00:00+07:00",
      relationshipType: "NAPAS_247",
      identityConfidence: 0.9,
    };
    const trace: TraceGraphResponse = {
      nodes: [
        {
          nodeId: "a",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: true,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
        {
          nodeId: "b",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: false,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
      ],
      edges: [edge],
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { a: 0, b: 1 },
      timeMin: "2026-09-08T10:00:00+07:00",
      timeMax: "2026-09-08T10:00:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const targetMs = Date.parse("2026-09-08T10:00:00+07:00");
    // At exactly cutoff -> visible
    const projExact = projectGraph(trace, {
      ...initialView(trace),
      cutoffMs: targetMs,
      amountThresholdVnd: 0,
    });
    expect(projExact.visibleEdgeIds.has("e1")).toBe(true);
    expect(projExact.futureEdgeIds).toEqual([]);

    // 1ms before cutoff -> future, not visible
    const projBefore = projectGraph(trace, {
      ...initialView(trace),
      cutoffMs: targetMs - 1,
      amountThresholdVnd: 0,
    });
    expect(projBefore.visibleEdgeIds.has("e1")).toBe(false);
    expect(projBefore.futureEdgeIds).toEqual(["e1"]);
  });

  it("handles missing or invalid timestamps without throwing", () => {
    const edgeNoTime: TraceEdgeResponse = {
      edgeId: "e_null",
      source: "a",
      target: "b",
      flowAmount: 10_000_000,
      currency: "VND",
      timestamp: null,
      relationshipType: "NAPAS_247",
      identityConfidence: 0.9,
    };
    const edgeInvalidTime: TraceEdgeResponse = {
      edgeId: "e_invalid",
      source: "a",
      target: "b",
      flowAmount: 10_000_000,
      currency: "VND",
      timestamp: "not-a-date",
      relationshipType: "NAPAS_247",
      identityConfidence: 0.9,
    };
    const trace: TraceGraphResponse = {
      nodes: [
        {
          nodeId: "a",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: true,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
        {
          nodeId: "b",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: false,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
      ],
      edges: [edgeNoTime, edgeInvalidTime],
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { a: 0, b: 1 },
      timeMin: null,
      timeMax: null,
      unknownTimeEdgeCount: 2,
    };

    const proj = projectGraph(trace, {
      ...initialView(trace),
      cutoffMs: Date.now(),
    });
    expect(proj.visibleEdgeIds.size).toBe(0);
    expect(proj.unknownTimeEdgeIds).toEqual(["e_null", "e_invalid"]);
  });

  it("calculates exact VND edge widths at 0, 40M, and 100M boundaries", () => {
    const base: TraceEdgeResponse = {
      edgeId: "e",
      source: "a",
      target: "b",
      flowAmount: 0,
      currency: "VND",
      timestamp: null,
      relationshipType: "X",
      identityConfidence: 1,
    };
    expect(edgeWidth({ ...base, flowAmount: 0 })).toBe(1.8);
    expect(edgeWidth({ ...base, flowAmount: 39_999_999 })).toBe(1.8);
    expect(edgeWidth({ ...base, flowAmount: 40_000_000 })).toBe(3.0);
    expect(edgeWidth({ ...base, flowAmount: 99_999_999 })).toBe(3.0);
    expect(edgeWidth({ ...base, flowAmount: 100_000_000 })).toBe(4.5);
    expect(edgeWidth({ ...base, flowAmount: 500_000_000 })).toBe(4.5);
    // Non-VND uses neutral 1.8
    expect(edgeWidth({ ...base, currency: "USD", flowAmount: 500_000_000 })).toBe(1.8);
    expect(edgeWidth({ ...base, currency: null, flowAmount: 500_000_000 })).toBe(1.8);
  });

  it("formats VND millions with exact bigints and preserves micro-transfers", () => {
    expect(formatVndMillions(48_500_000n)).toBe("48.5 tr");
    expect(formatVndMillions(10_000_000n)).toBe("10.0 tr");
    expect(formatVndMillions(1n)).toBe("0.000001 tr");
    expect(formatVndMillions(0n)).toBe("0.0 tr");
    expect(formatVndMillions(140_000_000n)).toBe("140.0 tr");
    expect(formatVndMillions(1_500_000n)).toBe("1.5 tr");
    // Aggregate beyond JS safe integer total
    expect(formatVndMillions(10_000_000_000_000_000n)).toBe("10000000000.0 tr");
  });

  it("formats transactions with Asia/Ho_Chi_Minh time or explicit warnings", () => {
    const vndEdge: TraceEdgeResponse = {
      edgeId: "e1",
      source: "a",
      target: "b",
      flowAmount: 48_500_000,
      currency: "VND",
      timestamp: "2026-09-08T08:30:00+07:00",
      relationshipType: "NAPAS_247",
      identityConfidence: 0.98,
    };
    expect(formatTransaction(vndEdge)).toBe("48.5 tr (08:30)");

    const usdEdge: TraceEdgeResponse = {
      edgeId: "e2",
      source: "a",
      target: "b",
      flowAmount: 2500,
      currency: "USD",
      timestamp: "2026-09-08T08:30:00+07:00",
      relationshipType: "SWIFT",
      identityConfidence: 0.98,
    };
    expect(formatTransaction(usdEdge)).toBe("2500 USD (08:30)");

    const noCurEdge: TraceEdgeResponse = {
      edgeId: "e3",
      source: "a",
      target: "b",
      flowAmount: 5000,
      currency: null,
      timestamp: null,
      relationshipType: "UNKNOWN",
      identityConfidence: 0.5,
    };
    expect(formatTransaction(noCurEdge)).toBe("5000 · Chưa rõ tiền tệ");
  });

  it("counts self-loop hidden flow once on the node", () => {
    const loopEdge: TraceEdgeResponse = {
      edgeId: "loop1",
      source: "a",
      target: "a",
      flowAmount: 5_000_000,
      currency: "VND",
      timestamp: "2026-09-08T08:30:00+07:00",
      relationshipType: "SELF",
      identityConfidence: 1.0,
    };
    const trace: TraceGraphResponse = {
      nodes: [
        {
          nodeId: "a",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: true,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
      ],
      edges: [loopEdge],
      isTruncated: false,
      totalHops: 0,
      hopByNodeId: { a: 0 },
      timeMin: "2026-09-08T08:30:00+07:00",
      timeMax: "2026-09-08T08:30:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const proj = projectGraph(trace, {
      ...initialView(trace),
      amountThresholdVnd: 10_000_000,
      cutoffMs: Date.parse("2026-09-08T08:30:00+07:00"),
    });

    expect(proj.amountHiddenByNode.get("a")).toEqual({
      edgeIds: ["loop1"],
      amountVnd: 5_000_000n,
    });
  });

  it("enforces manual-hide precedence over view override", () => {
    const edge: TraceEdgeResponse = {
      edgeId: "e1",
      source: "a",
      target: "b",
      flowAmount: 5_000_000,
      currency: "VND",
      timestamp: "2026-09-08T08:30:00+07:00",
      relationshipType: "TRANSFER",
      identityConfidence: 0.9,
    };
    const trace: TraceGraphResponse = {
      nodes: [
        {
          nodeId: "a",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: true,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
        {
          nodeId: "b",
          entityType: "ACCOUNT",
          riskScore: null,
          isSeed: false,
          isContext: false,
          accountHolderName: null,
          bankShortName: null,
          accountLast4: null,
          badge: null,
        },
      ],
      edges: [edge],
      isTruncated: false,
      totalHops: 1,
      hopByNodeId: { a: 0, b: 1 },
      timeMin: "2026-09-08T08:30:00+07:00",
      timeMax: "2026-09-08T08:30:00+07:00",
      unknownTimeEdgeCount: 0,
    };

    const proj = projectGraph(trace, {
      ...initialView(trace),
      cutoffMs: Date.parse("2026-09-08T08:30:00+07:00"),
      amountThresholdVnd: 10_000_000,
      viewOverrideEdgeIds: new Set(["e1"]),
      manuallyHiddenEdgeIds: new Set(["e1"]),
    });
    // Manually hidden wins over view override!
    expect(proj.visibleEdgeIds.has("e1")).toBe(false);
  });

  it("computes focused elements linkage path to seed deterministically", () => {
    const trace: TraceGraphResponse = {
      nodes: ["seed", "mid", "target", "other"].map((nodeId) => ({
        nodeId,
        entityType: "ACCOUNT",
        riskScore: null,
        isSeed: nodeId === "seed",
        isContext: false,
        accountHolderName: null,
        bankShortName: null,
        accountLast4: null,
        badge: null,
      })),
      edges: [
        {
          edgeId: "e_s_m",
          source: "seed",
          target: "mid",
          flowAmount: 100,
          currency: "VND",
          timestamp: null,
          relationshipType: "T",
          identityConfidence: 1,
        },
        {
          edgeId: "e_m_t",
          source: "mid",
          target: "target",
          flowAmount: 100,
          currency: "VND",
          timestamp: null,
          relationshipType: "T",
          identityConfidence: 1,
        },
        {
          edgeId: "e_other",
          source: "other",
          target: "other",
          flowAmount: 100,
          currency: "VND",
          timestamp: null,
          relationshipType: "T",
          identityConfidence: 1,
        },
      ],
      isTruncated: false,
      totalHops: 2,
      hopByNodeId: { seed: 0, mid: 1, target: 2, other: 3 },
      timeMin: null,
      timeMax: null,
      unknownTimeEdgeCount: 3,
    };

    const visibleEdgeIds = new Set(["e_s_m", "e_m_t"]);
    const focused = focusedElements(trace, visibleEdgeIds, "target");

    expect(Array.from(focused.nodeIds).sort()).toEqual(["mid", "seed", "target"]);
    expect(Array.from(focused.edgeIds).sort()).toEqual(["e_m_t", "e_s_m"]);

    // Disconnected node
    const focusedOther = focusedElements(trace, visibleEdgeIds, "other");
    expect(Array.from(focusedOther.nodeIds)).toEqual(["other"]);
    expect(Array.from(focusedOther.edgeIds)).toEqual([]);
  });
});
