import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WorkbenchData } from "./api";
import { CaseWorkspace } from "./CaseWorkspace";

vi.mock("cytoscape", () => ({
  default: () => ({
    destroy: () => undefined,
    on: () => undefined,
  }),
}));

describe("CaseWorkspace", () => {
  const mockWorkbenchData: WorkbenchData = {
    case: {
      caseId: "case_alpha",
      seedEntity: "entity_target_123",
      evidenceIds: ["ev-sup-1", "ev-mit-1"],
      traceEdgeIds: ["edge-1", "edge-2"],
      createdAt: "2026-09-02T08:00:00Z",
      snapshotHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    evidence: [
      {
        evidenceId: "ev-sup-1",
        category: "OBSERVED",
        sourceReference: "txn-wire-999",
        polarity: "SUPPORTING",
        snapshotTime: "2026-09-02T08:05:00Z",
        generationMethodVersion: "v1.0.0",
        payloadSummary: "High velocity transfers to offshore jurisdiction",
        integrityHash: "1111111111111111111111111111111111111111111111111111111111111111",
        confidence: 0.98,
      },
      {
        evidenceId: "ev-mit-1",
        category: "RULE",
        sourceReference: "kyc-profile-verified",
        polarity: "MITIGATING",
        snapshotTime: "2026-09-02T07:30:00Z",
        generationMethodVersion: "v1.0.0",
        payloadSummary: "KYC documentation recently re-verified by compliance",
        integrityHash: "2222222222222222222222222222222222222222222222222222222222222222",
        confidence: 0.85,
      },
    ],
    trace: {
      nodes: [
        {
          nodeId: "node_seed",
          entityType: "COMPANY",
          riskScore: 0.85,
          isSeed: true,
          isContext: false,
        },
        {
          nodeId: "node_context",
          entityType: "INDIVIDUAL",
          riskScore: 0.25,
          isSeed: false,
          isContext: true,
        },
        {
          nodeId: "node_intermediary",
          entityType: "ACCOUNT",
          riskScore: 0.55,
          isSeed: false,
          isContext: false,
        },
      ],
      edges: [
        {
          edgeId: "edge-1",
          source: "node_seed",
          target: "node_intermediary",
          flowAmount: 150000,
          relationshipType: "SWIFT_TRANSFER",
          identityConfidence: 0.95,
        },
        {
          edgeId: "edge-2",
          source: "node_intermediary",
          target: "node_context",
          flowAmount: 25000,
          relationshipType: "PAYROLL",
          identityConfidence: 0.65,
        },
      ],
      isTruncated: false,
      totalHops: 2,
    },
    hypothesis: {
      hypothesisId: "hyp-001",
      caseId: "case_alpha",
      status: "HYPOTHESIS_GENERATED",
      summary:
        "Entity entity_target_123 exhibits layering characteristics through intermediary accounts.",
      claims: [
        {
          claimText:
            "Rapid transfer of $150,000 to intermediary account within 24 hours of alert.",
          citedEvidenceIds: ["ev-sup-1"],
        },
        {
          claimText:
            "Account has active KYC documentation mitigating identity theft suspicions.",
          citedEvidenceIds: ["ev-mit-1"],
        },
      ],
      generatedAt: "2026-09-02T08:15:00Z",
      modelVersion: "deepseek-r1-aml-v1",
    },
  };

  it("shows evidence and provider-off state with minimal caseData", () => {
    render(
      <CaseWorkspace
        caseData={{ caseId: "c1", evidenceIds: ["ev-1"], traceEdgeIds: ["e1"] }}
        aiStatus="AI_UNAVAILABLE"
      />
    );
    expect(screen.getByText("Case c1")).toBeInTheDocument();
    expect(
      screen.getByText("AI unavailable — investigation tools remain active")
    ).toBeInTheDocument();
    expect(screen.getByTestId("status-badge-AI_UNAVAILABLE")).toBeInTheDocument();
  });

  it("renders header with Seed Entity and Snapshot Hash", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    expect(screen.getByText("Case case_alpha")).toBeInTheDocument();
    expect(screen.getByTestId("seed-entity")).toHaveTextContent(
      "Seed Entity: entity_target_123"
    );
    expect(screen.getByTestId("snapshot-hash")).toHaveTextContent(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
  });

  it("renders Evidence Timeline with Supporting vs Mitigating badges", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    const supBadge = screen.getByTestId("polarity-badge-ev-sup-1");
    expect(supBadge).toHaveTextContent("SUPPORTING");

    const mitBadge = screen.getByTestId("polarity-badge-ev-mit-1");
    expect(mitBadge).toHaveTextContent("MITIGATING");

    expect(
      screen.getByText("High velocity transfers to offshore jurisdiction")
    ).toBeInTheDocument();
    expect(
      screen.getByText("KYC documentation recently re-verified by compliance")
    ).toBeInTheDocument();
  });

  it("renders Cytoscape graph container with trace information", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    const graphContainer = screen.getByTestId("trace-graph-container");
    expect(graphContainer).toBeInTheDocument();
    expect(screen.getByText(/2 bounded edges/)).toBeInTheDocument();
    expect(screen.getByText(/High Risk/)).toBeInTheDocument();
  });

  it("renders AI Hypothesis Panel with HYPOTHESIS_GENERATED status, summary, and claims", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    expect(
      screen.getByTestId("status-badge-HYPOTHESIS_GENERATED")
    ).toBeInTheDocument();
    expect(screen.getByTestId("hypothesis-summary")).toHaveTextContent(
      "Entity entity_target_123 exhibits layering characteristics"
    );
    expect(
      screen.getByText(
        "Rapid transfer of $150,000 to intermediary account within 24 hours of alert."
      )
    ).toBeInTheDocument();
  });

  it("supports clicking citations to highlight cited evidence", async () => {
    const user = userEvent.setup();
    const onSelectEvidence = vi.fn();

    render(
      <CaseWorkspace
        workbenchData={mockWorkbenchData}
        onSelectEvidence={onSelectEvidence}
      />
    );

    const citationBtn = screen.getByTestId("citation-ev-sup-1");
    expect(citationBtn).toBeInTheDocument();

    await user.click(citationBtn);

    expect(onSelectEvidence).toHaveBeenCalledWith("ev-sup-1");
    expect(screen.getByText("Selected: ev-sup-1")).toBeInTheDocument();
  });

  it("renders status badge and message for INSUFFICIENT_EVIDENCE", () => {
    render(
      <CaseWorkspace
        caseData={{ caseId: "case_sparse" }}
        aiStatus="INSUFFICIENT_EVIDENCE"
      />
    );

    expect(
      screen.getByTestId("status-badge-INSUFFICIENT_EVIDENCE")
    ).toBeInTheDocument();
    expect(screen.getByTestId("ai-insufficient-msg")).toHaveTextContent(
      "Insufficient evidence to construct a complete hypothesis"
    );
  });

  it("renders status badge and message for AI_INVALID_OUTPUT", () => {
    render(
      <CaseWorkspace
        caseData={{ caseId: "case_invalid" }}
        aiStatus="AI_INVALID_OUTPUT"
      />
    );

    expect(
      screen.getByTestId("status-badge-AI_INVALID_OUTPUT")
    ).toBeInTheDocument();
    expect(screen.getByTestId("ai-invalid-msg")).toHaveTextContent(
      "AI hypothesis output failed schema or citation verification"
    );
  });

  it("handles analyst feedback form submission", async () => {
    const user = userEvent.setup();
    const onSubmitFeedback = vi.fn().mockResolvedValue({ success: true, data: {} });

    render(
      <CaseWorkspace
        workbenchData={mockWorkbenchData}
        onSubmitFeedback={onSubmitFeedback}
      />
    );

    // Select disposition
    const dispositionSelect = screen.getByLabelText("Case Disposition");
    await user.selectOptions(dispositionSelect, "ESCALATE");

    // Analyst ID
    const analystInput = screen.getByLabelText("Analyst ID");
    await user.clear(analystInput);
    await user.type(analystInput, "analyst_senior_42");

    // Rationale
    const reasonTextarea = screen.getByLabelText("Adjudication Rationale");
    await user.type(
      reasonTextarea,
      "Escalating to Senior Compliance due to overseas wire velocity."
    );

    // Submit
    const submitBtn = screen.getByRole("button", {
      name: "Submit Disposition",
    });
    await user.click(submitBtn);

    expect(onSubmitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        analystId: "analyst_senior_42",
        disposition: "ESCALATE",
        reason: "Escalating to Senior Compliance due to overseas wire velocity.",
        snapshotHash:
          "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      })
    );

    await waitFor(() => {
      expect(screen.getByTestId("feedback-result")).toHaveTextContent(
        "Feedback submitted successfully"
      );
    });
  });

  it("handles analyst feedback submission error", async () => {
    const user = userEvent.setup();
    const onSubmitFeedback = vi.fn().mockResolvedValue({
      success: false,
      data: null,
      error: { code: "FEEDBACK_CONFLICT", message: "Snapshot hash mismatch" },
    });

    render(
      <CaseWorkspace
        workbenchData={mockWorkbenchData}
        onSubmitFeedback={onSubmitFeedback}
      />
    );

    const reasonTextarea = screen.getByLabelText("Adjudication Rationale");
    await user.type(reasonTextarea, "Some justification");

    const submitBtn = screen.getByRole("button", {
      name: "Submit Disposition",
    });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId("feedback-result")).toHaveTextContent(
        "Snapshot hash mismatch"
      );
    });
  });

  it("renders loading and error states", () => {
    const { rerender } = render(
      <CaseWorkspace
        caseData={{ caseId: "case_load" }}
        isLoading={true}
      />
    );
    expect(screen.getByText("Loading Case case_load...")).toBeInTheDocument();

    rerender(
      <CaseWorkspace
        caseData={{ caseId: "case_load" }}
        error="Failed to connect to API"
      />
    );
    expect(screen.getByText("Failed to connect to API")).toBeInTheDocument();
  });
});
