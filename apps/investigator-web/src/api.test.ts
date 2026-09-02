import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchCase,
  fetchWorkbenchData,
  FeedbackRequest,
  submitFeedback,
  WorkbenchData,
} from "./api";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchWorkbenchData", () => {
    it("returns WorkbenchEnvelope on success", async () => {
      const mockWorkbenchData: WorkbenchData = {
        case: {
          caseId: "case_101",
          seedEntity: "entity_seed",
          evidenceIds: ["ev-1", "ev-2"],
          traceEdgeIds: ["edge-1"],
          createdAt: "2026-09-02T10:00:00Z",
          snapshotHash: "a".repeat(64),
        },
        evidence: [
          {
            evidenceId: "ev-1",
            category: "OBSERVED",
            sourceReference: "ref-1",
            polarity: "SUPPORTING",
            snapshotTime: "2026-09-02T10:00:00Z",
            generationMethodVersion: "v1",
            payloadSummary: "Wire transfer observed",
            integrityHash: "b".repeat(64),
            confidence: 0.95,
          },
        ],
        trace: {
          nodes: [
            {
              nodeId: "n1",
              entityType: "ACCOUNT",
              riskScore: 0.85,
              isSeed: true,
              isContext: false,
            },
          ],
          edges: [
            {
              edgeId: "edge-1",
              source: "n1",
              target: "n2",
              flowAmount: 100000,
              relationshipType: "WIRE",
              identityConfidence: 0.9,
            },
          ],
          isTruncated: false,
          totalHops: 1,
        },
        hypothesis: {
          hypothesisId: "hyp-1",
          caseId: "case_101",
          status: "HYPOTHESIS_GENERATED",
          summary: "Layering activity detected",
          claims: [
            {
              claimText: "Entity moved funds to offshore account",
              citedEvidenceIds: ["ev-1"],
            },
          ],
          generatedAt: "2026-09-02T10:05:00Z",
          modelVersion: "deepseek-r1",
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        json: async () => ({
          success: true,
          data: mockWorkbenchData,
          error: null,
        }),
      } as unknown as Response);

      const res = await fetchWorkbenchData("case_101");
      expect(res.success).toBe(true);
      if (res.success) {
        expect(res.data.case.caseId).toBe("case_101");
        expect(res.data.hypothesis.status).toBe("HYPOTHESIS_GENERATED");
        expect(res.data.evidence).toHaveLength(1);
      }
    });

    it("handles error envelope correctly", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        json: async () => ({
          success: false,
          data: null,
          error: {
            code: "CASE_NOT_FOUND",
            message: "Case case_999 not found",
          },
        }),
      } as unknown as Response);

      const res = await fetchWorkbenchData("case_999");
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.error.code).toBe("CASE_NOT_FOUND");
        expect(res.error.message).toContain("not found");
      }
    });

    it("catches network fetch failure and returns FETCH_ERROR", async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error("Connection refused"));

      const res = await fetchWorkbenchData("case_err");
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.error.code).toBe("FETCH_ERROR");
        expect(res.error.message).toBe("Connection refused");
      }
    });
  });

  describe("fetchCase", () => {
    it("returns CaseEnvelope on success", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        json: async () => ({
          success: true,
          data: {
            caseId: "case_001",
            seedEntity: "entity_seed",
            evidenceIds: ["ev-1"],
            traceEdgeIds: ["e-1"],
            createdAt: "2026-09-02T12:00:00Z",
            snapshotHash: "c".repeat(64),
          },
          error: null,
        }),
      } as unknown as Response);

      const res = await fetchCase("case_001");
      expect(res.success).toBe(true);
      if (res.success) {
        expect(res.data.caseId).toBe("case_001");
        expect(res.data.seedEntity).toBe("entity_seed");
      }
    });

    it("returns error envelope on network error", async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error("DNS lookup failed"));

      const res = await fetchCase("case_001");
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.error.code).toBe("FETCH_ERROR");
      }
    });
  });

  describe("submitFeedback", () => {
    it("submits feedback and returns FeedbackEnvelope", async () => {
      const feedbackReq: FeedbackRequest = {
        eventId: "fb-123",
        analystId: "analyst_alice",
        disposition: "CONFIRMED_SUSPICIOUS",
        reason: "Rapid movement of funds across high risk entities",
        createdAt: "2026-09-02T12:30:00Z",
        snapshotHash: "d".repeat(64),
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        json: async () => ({
          success: true,
          data: { status: "recorded", eventId: "fb-123" },
          error: null,
        }),
      } as unknown as Response);

      const res = await submitFeedback("case_001", feedbackReq);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/cases/case_001/feedback",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(feedbackReq),
        })
      );
      expect(res.success).toBe(true);
    });

    it("returns error envelope when submitFeedback fails", async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error("Timeout"));

      const feedbackReq: FeedbackRequest = {
        eventId: "fb-123",
        analystId: "analyst_alice",
        disposition: "FALSE_POSITIVE",
        reason: "Legitimate payroll activity",
        createdAt: "2026-09-02T12:30:00Z",
        snapshotHash: "d".repeat(64),
      };

      const res = await submitFeedback("case_001", feedbackReq);
      expect(res.success).toBe(false);
      if (!res.success) {
        expect(res.error.code).toBe("SUBMIT_FEEDBACK_ERROR");
        expect(res.error.message).toBe("Timeout");
      }
    });
  });
});
