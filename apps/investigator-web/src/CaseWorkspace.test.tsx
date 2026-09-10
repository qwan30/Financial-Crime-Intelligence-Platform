import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkbenchData } from "./api";
import { CaseWorkspace } from "./CaseWorkspace";

vi.mock("cytoscape", () => {
  const cyMock = {
    on: vi.fn(),
    nodes: vi.fn().mockReturnValue([]),
    edges: vi.fn().mockReturnValue([]),
    getElementById: vi.fn().mockReturnValue({
      inside: () => false,
      length: 0,
      renderedPosition: () => ({ x: 0, y: 0 }),
      position: () => ({ x: 0, y: 0 }),
      data: vi.fn(),
    }),
    batch: vi.fn((fn: () => void) => fn()),
    add: vi.fn(),
    remove: vi.fn(),
    resize: vi.fn(),
    destroy: vi.fn(),
    fit: vi.fn(),
    layout: vi.fn().mockReturnValue({ run: vi.fn() }),
  };
  return {
    default: vi.fn(() => cyMock),
  };
});

describe("CaseWorkspace", () => {
  const mockWorkbenchData: WorkbenchData = {
    case: {
      caseId: "case_alpha",
      seedEntity: "entity_target_123",
      evidenceIds: ["ev-sup-1", "ev-mit-1"],
      traceEdgeIds: ["edge-1", "edge-2"],
      createdAt: "2026-09-01T12:00:00Z",
      snapshotHash:
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    evidence: [
      {
        evidenceId: "ev-sup-1",
        category: "TRANSACTION",
        sourceReference: "napas:msg:1001",
        polarity: "SUPPORTING",
        snapshotTime: "2026-09-01T14:30:00Z",
        generationMethodVersion: "1.0.0",
        payloadSummary: "High velocity transfers to offshore jurisdiction",
        integrityHash:
          "1111111111111111111111111111111111111111111111111111111111111111",
        confidence: 0.95,
      },
      {
        evidenceId: "ev-mit-1",
        category: "KYC",
        sourceReference: "core_banking:cif:99",
        polarity: "MITIGATING",
        snapshotTime: "2026-09-01T14:35:00Z",
        generationMethodVersion: "1.0.0",
        payloadSummary: "KYC documentation recently re-verified by compliance",
        integrityHash:
          "2222222222222222222222222222222222222222222222222222222222222222",
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
          accountHolderName: "Cong ty ABC",
          bankShortName: "Vietcombank",
          accountLast4: "1234",
          badge: "SEED_HUB",
        },
        {
          nodeId: "node_context",
          entityType: "INDIVIDUAL",
          riskScore: 0.25,
          isSeed: false,
          isContext: true,
          accountHolderName: "Nguyen Van B",
          bankShortName: "BIDV",
          accountLast4: "5678",
          badge: "BENIGN",
        },
        {
          nodeId: "node_intermediary",
          entityType: "ACCOUNT",
          riskScore: 0.55,
          isSeed: false,
          isContext: false,
          accountHolderName: "Tran Thi C",
          bankShortName: "Techcombank",
          accountLast4: "9012",
          badge: "LAYERING",
        },
      ],
      edges: [
        {
          edgeId: "edge-1",
          source: "node_seed",
          target: "node_intermediary",
          flowAmount: 150000000,
          currency: "VND",
          timestamp: "2026-09-01T14:00:00+07:00",
          relationshipType: "SWIFT_TRANSFER",
          identityConfidence: 0.95,
        },
        {
          edgeId: "edge-2",
          source: "node_intermediary",
          target: "node_context",
          flowAmount: 25000000,
          currency: "VND",
          timestamp: "2026-09-01T14:30:00+07:00",
          relationshipType: "PAYROLL",
          identityConfidence: 0.65,
        },
      ],
      isTruncated: false,
      totalHops: 2,
      hopByNodeId: { node_seed: 0, node_intermediary: 1, node_context: 2 },
      timeMin: "2026-09-01T14:00:00+07:00",
      timeMax: "2026-09-01T14:30:00+07:00",
      unknownTimeEdgeCount: 0,
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
            "Rapid transfer of 150M to intermediary account within 24 hours of alert.",
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
    pins: [],
    pinningAvailable: true,
    hypothesisSnapshotHash: null,
  };

  it("renders header with Case ID, Seed Entity, and Snapshot Hash", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    expect(screen.getByText("Vụ án: case_alpha")).toBeInTheDocument();
    expect(screen.getByTestId("seed-entity")).toHaveTextContent(
      "Mục tiêu: entity_target_123"
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

  it("renders Cytoscape graph container", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    const graphContainer = screen.getByTestId("trace-graph-container");
    expect(graphContainer).toBeInTheDocument();
  });

  it("renders AI Hypothesis Panel with status, summary, and claims", () => {
    render(<CaseWorkspace workbenchData={mockWorkbenchData} />);

    expect(
      screen.getByTestId("status-badge-HYPOTHESIS_GENERATED")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Entity entity_target_123 exhibits layering characteristics/
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Rapid transfer of 150M to intermediary account within 24 hours of alert/
      )
    ).toBeInTheDocument();
  });

  it("supports clicking citations to trigger evidence selection", async () => {
    const user = userEvent.setup();
    const onSelectEvidence = vi.fn();

    render(
      <CaseWorkspace
        workbenchData={mockWorkbenchData}
        onSelectEvidence={onSelectEvidence}
      />
    );

    const citationBtn = screen.getByText("[ev-sup-1]");
    expect(citationBtn).toBeInTheDocument();

    await user.click(citationBtn);

    expect(onSelectEvidence).toHaveBeenCalledWith("ev-sup-1");
  });

  it("handles analyst feedback form submission with required analyst ID", async () => {
    const user = userEvent.setup();
    const onSubmitFeedback = vi.fn().mockResolvedValue({ success: true, data: {} });

    render(
      <CaseWorkspace
        workbenchData={mockWorkbenchData}
        onSubmitFeedback={onSubmitFeedback}
      />
    );

    // Enter Analyst ID
    const analystInput = screen.getByLabelText(/Mã điều tra viên/);
    await user.type(analystInput, "analyst_senior_42");

    // Select disposition
    const dispositionSelect = screen.getByLabelText(/Kết luận xử lý/);
    await user.selectOptions(dispositionSelect, "ESCALATE");

    // Rationale
    const reasonTextarea = screen.getByLabelText(/Lý do đánh giá/);
    await user.type(
      reasonTextarea,
      "Escalating to Senior Compliance due to overseas wire velocity."
    );

    // Submit
    const submitBtn = screen.getByRole("button", {
      name: "Gửi đánh giá vụ án",
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
      expect(screen.getByText("Đã lưu phản hồi thành công!")).toBeInTheDocument();
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

    const analystInput = screen.getByLabelText(/Mã điều tra viên/);
    await user.type(analystInput, "analyst_01");

    const reasonTextarea = screen.getByLabelText(/Lý do đánh giá/);
    await user.type(reasonTextarea, "Some justification");

    const submitBtn = screen.getByRole("button", {
      name: "Gửi đánh giá vụ án",
    });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Snapshot hash mismatch")).toBeInTheDocument();
    });
  });

  it("renders pinned evidence in the dossier when pins are present", () => {
    const withPinsData: WorkbenchData = {
      ...mockWorkbenchData,
      pins: [
        {
          edgeId: "edge-1",
          evidenceId: "ev:txn:edge-1",
          analystId: "analyst_01",
          typologyTag: "SHELL_CORP",
          updatedAt: "2026-09-08T10:00:00Z",
          transaction: mockWorkbenchData.trace.edges[0],
        },
      ],
    };

    render(<CaseWorkspace workbenchData={withPinsData} />);
    expect(screen.getByText("Chứng cứ đã ghim (1)")).toBeInTheDocument();
    expect(screen.getByText("GHIM SAR")).toBeInTheDocument();
    expect(screen.getByText("ĐTV: analyst_01")).toBeInTheDocument();
    expect(screen.getByText("SHELL_CORP")).toBeInTheDocument();
  });
});
