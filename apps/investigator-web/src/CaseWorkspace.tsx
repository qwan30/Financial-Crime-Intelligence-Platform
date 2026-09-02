import cytoscape from "cytoscape";
import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  Disposition,
  EvidenceResponse,
  FeedbackEnvelope,
  FeedbackRequest,
  HypothesisResponse,
  submitFeedback as apiSubmitFeedback,
  TraceGraphResponse,
  WorkbenchData,
} from "./api";

export type CaseWorkspaceProps = {
  workbenchData?: WorkbenchData;
  caseData?: {
    caseId: string;
    evidenceIds?: string[];
    traceEdgeIds?: string[];
    seedEntity?: string;
    snapshotHash?: string;
    createdAt?: string;
  };
  evidenceList?: EvidenceResponse[];
  traceGraph?: TraceGraphResponse;
  aiStatus?: string;
  hypothesis?: HypothesisResponse;
  onSubmitFeedback?: (feedback: FeedbackRequest) => Promise<FeedbackEnvelope | void>;
  onSelectEvidence?: (evidenceId: string) => void;
  isLoading?: boolean;
  error?: string | null;
};

export function TraceGraph({
  trace,
  selectedEvidenceId,
  onNodeClick,
}: {
  trace: TraceGraphResponse;
  selectedEvidenceId?: string | null;
  onNodeClick?: (nodeId: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const elements: cytoscape.ElementDefinition[] = [];

    // Add nodes
    trace.nodes.forEach((node) => {
      let color = "#64748b"; // gray for context or low risk
      if (node.riskScore !== null && node.riskScore !== undefined) {
        if (node.riskScore >= 0.7) {
          color = "#ef4444"; // red
        } else if (node.riskScore >= 0.4) {
          color = "#f59e0b"; // amber
        } else {
          color = "#64748b"; // gray context
        }
      } else if (node.isContext) {
        color = "#94a3b8"; // lighter gray context
      }

      elements.push({
        data: {
          id: node.nodeId,
          label: `${node.nodeId}${
            node.riskScore !== null && node.riskScore !== undefined
              ? ` (${node.riskScore.toFixed(2)})`
              : ""
          }`,
          riskScore: node.riskScore ?? 0,
          isSeed: node.isSeed,
          isContext: node.isContext,
          entityType: node.entityType,
          color,
        },
      });
    });

    // Add edges
    trace.edges.forEach((edge) => {
      const isDashed = edge.identityConfidence < 0.8;
      let width = 2;
      if (edge.flowAmount >= 100000) {
        width = 5;
      } else if (edge.flowAmount >= 10000) {
        width = 3.5;
      } else if (edge.flowAmount >= 1000) {
        width = 2.5;
      } else {
        width = 1.5;
      }

      elements.push({
        data: {
          id: edge.edgeId,
          source: edge.source,
          target: edge.target,
          flowAmount: edge.flowAmount,
          relationshipType: edge.relationshipType,
          identityConfidence: edge.identityConfidence,
          lineStyle: isDashed ? "dashed" : "solid",
          width,
          label: `$${edge.flowAmount.toLocaleString()} (${edge.relationshipType})`,
        },
      });
    });

    try {
      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(color)",
              label: "data(label)",
              color: "#1e293b",
              "font-size": "11px",
              "text-valign": "bottom",
              "text-margin-y": 4,
              width: "36px",
              height: "36px",
            },
          },
          {
            selector: "node[?isSeed]",
            style: {
              "border-width": "3px",
              "border-color": "#0f172a",
              shape: "diamond",
              width: "44px",
              height: "44px",
            },
          },
          {
            selector: "edge",
            style: {
              width: "data(width)",
              "line-color": "#64748b",
              "target-arrow-color": "#64748b",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              label: "data(label)",
              "font-size": "9px",
              "text-rotation": "autorotate",
              color: "#334155",
            },
          },
          {
            selector: "edge[lineStyle = 'dashed']",
            style: {
              "line-style": "dashed",
            },
          },
          {
            selector: "edge[lineStyle = 'solid']",
            style: {
              "line-style": "solid",
            },
          },
        ],
        layout: {
          name: "breadthfirst",
          directed: true,
          padding: 16,
        },
      });

      if (onNodeClick && typeof cy.on === "function") {
        cy.on("tap", "node", (evt) => {
          const node = evt.target;
          onNodeClick(node.id());
        });
      }

      cyRef.current = cy;
      return () => {
        try {
          cy.destroy();
        } catch {
          // ignore mock error in jsdom tests
        }
      };
    } catch {
      // In non-DOM or mock environments where cytoscape is mocked
    }
  }, [trace, onNodeClick]);

  return (
    <div
      aria-label="Bounded transaction trace"
      ref={containerRef}
      style={{
        height: 340,
        width: "100%",
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        position: "relative",
      }}
      data-testid="trace-graph-container"
    >
      {selectedEvidenceId && (
        <div
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            background: "rgba(255,255,255,0.9)",
            padding: "4px 8px",
            fontSize: "12px",
            borderRadius: "4px",
            border: "1px solid #cbd5e1",
            zIndex: 10,
          }}
        >
          Selected: {selectedEvidenceId}
        </div>
      )}
    </div>
  );
}

export function CaseWorkspace({
  workbenchData,
  caseData,
  evidenceList,
  traceGraph,
  aiStatus,
  hypothesis,
  onSubmitFeedback,
  onSelectEvidence,
  isLoading,
  error,
}: CaseWorkspaceProps) {
  // Normalize data from workbenchData or fallback props
  const caseId =
    workbenchData?.case.caseId ?? caseData?.caseId ?? "unknown";
  const seedEntity =
    workbenchData?.case.seedEntity ?? caseData?.seedEntity ?? "N/A";
  const snapshotHash =
    workbenchData?.case.snapshotHash ??
    caseData?.snapshotHash ??
    "0000000000000000000000000000000000000000000000000000000000000000";
  const createdAt =
    workbenchData?.case.createdAt ?? caseData?.createdAt ?? new Date().toISOString();

  const evidence: EvidenceResponse[] = useMemo(() => {
    if (workbenchData?.evidence && workbenchData.evidence.length > 0) {
      return workbenchData.evidence;
    }
    if (evidenceList && evidenceList.length > 0) {
      return evidenceList;
    }
    if (caseData?.evidenceIds && caseData.evidenceIds.length > 0) {
      return caseData.evidenceIds.map((id, index) => ({
        evidenceId: id,
        category: "OBSERVED",
        sourceReference: `source-ref-${id}`,
        polarity: index % 2 === 0 ? "SUPPORTING" : "MITIGATING",
        snapshotTime: new Date(Date.now() - (index + 1) * 3600000).toISOString(),
        generationMethodVersion: "v1.0.0",
        payloadSummary: `Evidence payload for item ${id}`,
        integrityHash: "a".repeat(64),
        confidence: 0.9,
      }));
    }
    return [];
  }, [workbenchData?.evidence, evidenceList, caseData?.evidenceIds]);

  const trace: TraceGraphResponse = useMemo(() => {
    if (workbenchData?.trace) {
      return workbenchData.trace;
    }
    if (traceGraph) {
      return traceGraph;
    }
    const edgeIds = caseData?.traceEdgeIds ?? [];
    return {
      nodes: edgeIds.flatMap((_id, index) => [
        {
          nodeId: `n${index}`,
          entityType: "ACCOUNT",
          riskScore: index === 0 ? 0.85 : 0.35,
          isSeed: index === 0,
          isContext: index !== 0,
        },
        {
          nodeId: `n${index + 1}`,
          entityType: "ACCOUNT",
          riskScore: 0.45,
          isSeed: false,
          isContext: false,
        },
      ]),
      edges: edgeIds.map((id, index) => ({
        edgeId: id,
        source: `n${index}`,
        target: `n${index + 1}`,
        flowAmount: 25000,
        relationshipType: "WIRE_TRANSFER",
        identityConfidence: 0.85,
      })),
      isTruncated: false,
      totalHops: edgeIds.length,
    };
  }, [workbenchData?.trace, traceGraph, caseData?.traceEdgeIds]);

  const currentAiStatus =
    workbenchData?.hypothesis.status ??
    aiStatus ??
    hypothesis?.status ??
    "AI_UNAVAILABLE";

  const hypothesisSummary =
    workbenchData?.hypothesis.summary ?? hypothesis?.summary ?? "";

  const claims =
    workbenchData?.hypothesis.claims ?? hypothesis?.claims ?? [];

  // Local state
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(
    null
  );
  const [disposition, setDisposition] = useState<Disposition>(
    "CONFIRMED_SUSPICIOUS"
  );
  const [reason, setReason] = useState("");
  const [analystId, setAnalystId] = useState("analyst_lead");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const formId = useId();

  const handleCitationClick = (evidenceId: string) => {
    setSelectedEvidenceId(evidenceId);
    if (onSelectEvidence) {
      onSelectEvidence(evidenceId);
    }
    // Scroll to evidence element if present
    const el = document.getElementById(`evidence-${evidenceId}`);
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || !analystId.trim()) return;

    setIsSubmitting(true);
    setSubmissionResult(null);

    const feedbackPayload: FeedbackRequest = {
      eventId: `fb-${Date.now()}`,
      analystId: analystId.trim(),
      disposition,
      reason: reason.trim(),
      createdAt: new Date().toISOString(),
      snapshotHash,
      modelVersion: workbenchData?.hypothesis.modelVersion ?? "deepseek-r1-aml-v1",
    };

    try {
      if (onSubmitFeedback) {
        const res = await onSubmitFeedback(feedbackPayload);
        if (res && !res.success) {
          setSubmissionResult({
            success: false,
            message: res.error?.message ?? "Feedback submission failed",
          });
        } else {
          setSubmissionResult({
            success: true,
            message: "Feedback submitted successfully",
          });
          setReason("");
        }
      } else {
        const res = await apiSubmitFeedback(caseId, feedbackPayload);
        if (res.success) {
          setSubmissionResult({
            success: true,
            message: "Feedback submitted successfully",
          });
          setReason("");
        } else {
          setSubmissionResult({
            success: false,
            message: res.error.message,
          });
        }
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unexpected submission error";
      setSubmissionResult({
        success: false,
        message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Sort evidence by snapshot time
  const sortedEvidence = useMemo(() => {
    return [...evidence].sort(
      (a, b) =>
        new Date(b.snapshotTime).getTime() - new Date(a.snapshotTime).getTime()
    );
  }, [evidence]);

  if (isLoading) {
    return (
      <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
        <h1>Loading Case {caseId}...</h1>
        <p>Fetching workbench data from Case API.</p>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
        <h1 style={{ color: "#dc2626" }}>Error Loading Case</h1>
        <p>{error}</p>
      </main>
    );
  }

  return (
    <main
      style={{
        padding: "24px",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        maxWidth: "1400px",
        margin: "0 auto",
        color: "#0f172a",
      }}
    >
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid #e2e8f0",
          paddingBottom: "16px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h1 style={{ margin: "0 0 8px 0", fontSize: "28px" }}>
              Case {caseId}
            </h1>
            <div
              style={{
                display: "flex",
                gap: "16px",
                fontSize: "14px",
                color: "#475569",
                flexWrap: "wrap",
              }}
            >
              <span data-testid="seed-entity">
                <strong>Seed Entity:</strong> {seedEntity}
              </span>
              <span>
                <strong>Created:</strong>{" "}
                {new Date(createdAt).toLocaleString()}
              </span>
            </div>
          </div>
          <div
            style={{
              textAlign: "right",
              fontSize: "12px",
              color: "#64748b",
            }}
          >
            <div>
              <strong>Snapshot Hash:</strong>
            </div>
            <code
              data-testid="snapshot-hash"
              style={{
                background: "#f1f5f9",
                padding: "2px 6px",
                borderRadius: "4px",
                fontSize: "11px",
                fontFamily: "monospace",
                display: "inline-block",
                maxWidth: "300px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={snapshotHash}
            >
              {snapshotHash}
            </code>
          </div>
        </div>
      </header>

      {/* Main 2-Column Grid Layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))",
          gap: "24px",
        }}
      >
        {/* Left Column: Trace Graph and Evidence Timeline */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Trace Graph Section */}
          <section
            aria-labelledby="trace-heading"
            style={{
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              padding: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <h2
                id="trace-heading"
                style={{ margin: 0, fontSize: "18px", color: "#1e293b" }}
              >
                Transaction Trace Graph
              </h2>
              <span
                style={{
                  fontSize: "13px",
                  color: "#64748b",
                  background: "#f1f5f9",
                  padding: "2px 8px",
                  borderRadius: "12px",
                }}
              >
                {trace.edges.length} bounded edges ({trace.nodes.length} nodes)
              </span>
            </div>

            {/* Trace Graph Legend */}
            <div
              style={{
                display: "flex",
                gap: "12px",
                fontSize: "11px",
                color: "#64748b",
                marginBottom: "8px",
                flexWrap: "wrap",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    background: "#ef4444",
                    borderRadius: "50%",
                    display: "inline-block",
                  }}
                />{" "}
                High Risk (≥0.7)
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    background: "#f59e0b",
                    borderRadius: "50%",
                    display: "inline-block",
                  }}
                />{" "}
                Medium Risk (≥0.4)
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    background: "#64748b",
                    borderRadius: "50%",
                    display: "inline-block",
                  }}
                />{" "}
                Context Node
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span
                  style={{
                    width: 14,
                    height: 0,
                    borderTop: "2px dashed #64748b",
                    display: "inline-block",
                  }}
                />{" "}
                Low Identity Confidence
              </span>
            </div>

            <TraceGraph
              trace={trace}
              selectedEvidenceId={selectedEvidenceId}
              onNodeClick={(nodeId) => {
                const matched = evidence.find((e) =>
                  e.payloadSummary.includes(nodeId) ||
                  e.sourceReference.includes(nodeId)
                );
                if (matched) {
                  setSelectedEvidenceId(matched.evidenceId);
                }
              }}
            />
          </section>

          {/* Evidence Timeline Section */}
          <section
            aria-labelledby="evidence-heading"
            style={{
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              padding: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <h2
                id="evidence-heading"
                style={{ margin: 0, fontSize: "18px", color: "#1e293b" }}
              >
                Evidence Timeline
              </h2>
              <span style={{ fontSize: "13px", color: "#64748b" }}>
                {sortedEvidence.length} items
              </span>
            </div>

            {sortedEvidence.length === 0 ? (
              <p style={{ color: "#64748b", fontSize: "14px" }}>
                No evidence items recorded for this case.
              </p>
            ) : (
              <ul
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: 0,
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                {sortedEvidence.map((item) => {
                  const isSupporting = item.polarity === "SUPPORTING";
                  const isMitigating = item.polarity === "MITIGATING";
                  const isSelected = selectedEvidenceId === item.evidenceId;

                  return (
                    <li
                      key={item.evidenceId}
                      id={`evidence-${item.evidenceId}`}
                      data-testid={`evidence-item-${item.evidenceId}`}
                      onClick={() => setSelectedEvidenceId(item.evidenceId)}
                      style={{
                        padding: "12px",
                        borderRadius: "6px",
                        border: isSelected
                          ? "2px solid #2563eb"
                          : "1px solid #e2e8f0",
                        background: isSelected
                          ? "#eff6ff"
                          : "#ffffff",
                        transition: "all 0.15s ease-in-out",
                        cursor: "pointer",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: "6px",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            gap: "8px",
                            alignItems: "center",
                          }}
                        >
                          <strong style={{ fontSize: "14px" }}>
                            {item.evidenceId}
                          </strong>
                          {/* Polarity Badge */}
                          <span
                            data-testid={`polarity-badge-${item.evidenceId}`}
                            style={{
                              fontSize: "11px",
                              fontWeight: 600,
                              padding: "2px 6px",
                              borderRadius: "4px",
                              border: isSupporting
                                ? "1px solid #86efac"
                                : isMitigating
                                ? "1px solid #fde68a"
                                : "1px solid #cbd5e1",
                              background: isSupporting
                                ? "#dcfce7"
                                : isMitigating
                                ? "#fef3c7"
                                : "#f1f5f9",
                              color: isSupporting
                                ? "#166534"
                                : isMitigating
                                ? "#92400e"
                                : "#475569",
                            }}
                          >
                            {item.polarity}
                          </span>
                          {/* Category Badge */}
                          <span
                            style={{
                              fontSize: "11px",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              background: "#f1f5f9",
                              color: "#475569",
                            }}
                          >
                            {item.category}
                          </span>
                        </div>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                          {new Date(item.snapshotTime).toLocaleTimeString()}
                        </span>
                      </div>

                      <p
                        style={{
                          margin: "0 0 6px 0",
                          fontSize: "13px",
                          color: "#334155",
                        }}
                      >
                        {item.payloadSummary}
                      </p>

                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: "11px",
                          color: "#64748b",
                        }}
                      >
                        <span>Source: {item.sourceReference}</span>
                        {item.confidence !== null &&
                          item.confidence !== undefined && (
                            <span>
                              Confidence: {(item.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>

        {/* Right Column: AI Hypothesis & Analyst Feedback */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* AI Hypothesis Section */}
          <section
            aria-labelledby="hypothesis-heading"
            style={{
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              padding: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <h2
                id="hypothesis-heading"
                style={{ margin: 0, fontSize: "18px", color: "#1e293b" }}
              >
                AI Investigation Hypothesis
              </h2>

              {/* Status Badge */}
              <span
                data-testid={`status-badge-${currentAiStatus}`}
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  padding: "4px 8px",
                  borderRadius: "6px",
                  textTransform: "uppercase",
                  background:
                    currentAiStatus === "HYPOTHESIS_GENERATED"
                      ? "#dcfce7"
                      : currentAiStatus === "INSUFFICIENT_EVIDENCE"
                      ? "#fef3c7"
                      : currentAiStatus === "AI_INVALID_OUTPUT"
                      ? "#fee2e2"
                      : "#f1f5f9",
                  color:
                    currentAiStatus === "HYPOTHESIS_GENERATED"
                      ? "#166534"
                      : currentAiStatus === "INSUFFICIENT_EVIDENCE"
                      ? "#92400e"
                      : currentAiStatus === "AI_INVALID_OUTPUT"
                      ? "#991b1b"
                      : "#475569",
                  border:
                    currentAiStatus === "HYPOTHESIS_GENERATED"
                      ? "1px solid #86efac"
                      : currentAiStatus === "INSUFFICIENT_EVIDENCE"
                      ? "1px solid #fde68a"
                      : currentAiStatus === "AI_INVALID_OUTPUT"
                      ? "1px solid #fca5a5"
                      : "1px solid #cbd5e1",
                }}
              >
                {currentAiStatus}
              </span>
            </div>

            {/* AI Status Messaging */}
            {currentAiStatus === "AI_UNAVAILABLE" && (
              <div
                data-testid="ai-unavailable-msg"
                style={{
                  padding: "12px",
                  backgroundColor: "#f8fafc",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                  color: "#475569",
                  fontSize: "14px",
                  marginBottom: "12px",
                }}
              >
                AI unavailable — investigation tools remain active
              </div>
            )}

            {currentAiStatus === "INSUFFICIENT_EVIDENCE" && (
              <div
                data-testid="ai-insufficient-msg"
                style={{
                  padding: "12px",
                  backgroundColor: "#fffbeb",
                  borderRadius: "6px",
                  border: "1px solid #fef3c7",
                  color: "#92400e",
                  fontSize: "14px",
                  marginBottom: "12px",
                }}
              >
                Insufficient evidence to construct a complete hypothesis
              </div>
            )}

            {currentAiStatus === "AI_INVALID_OUTPUT" && (
              <div
                data-testid="ai-invalid-msg"
                style={{
                  padding: "12px",
                  backgroundColor: "#fef2f2",
                  borderRadius: "6px",
                  border: "1px solid #fee2e2",
                  color: "#991b1b",
                  fontSize: "14px",
                  marginBottom: "12px",
                }}
              >
                AI hypothesis output failed schema or citation verification
              </div>
            )}

            {/* Summary */}
            {hypothesisSummary && (
              <div style={{ marginBottom: "16px" }}>
                <h3
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    margin: "0 0 6px 0",
                    color: "#334155",
                  }}
                >
                  Executive Summary
                </h3>
                <p
                  data-testid="hypothesis-summary"
                  style={{
                    margin: 0,
                    fontSize: "14px",
                    lineHeight: "1.5",
                    color: "#1e293b",
                    background: "#f8fafc",
                    padding: "12px",
                    borderRadius: "6px",
                    border: "1px solid #e2e8f0",
                  }}
                >
                  {hypothesisSummary}
                </p>
              </div>
            )}

            {/* Material Claims with Citations */}
            {claims.length > 0 && (
              <div>
                <h3
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    margin: "0 0 8px 0",
                    color: "#334155",
                  }}
                >
                  Material Claims & Evidence Citations
                </h3>
                <ul
                  style={{
                    listStyle: "none",
                    padding: 0,
                    margin: 0,
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  {claims.map((claim, idx) => (
                    <li
                      key={idx}
                      data-testid={`material-claim-${idx}`}
                      style={{
                        padding: "10px",
                        borderRadius: "6px",
                        background: "#ffffff",
                        border: "1px solid #e2e8f0",
                      }}
                    >
                      <p
                        style={{
                          margin: "0 0 8px 0",
                          fontSize: "13px",
                          color: "#1e293b",
                          lineHeight: "1.4",
                        }}
                      >
                        {claim.claimText}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 600,
                            color: "#64748b",
                          }}
                        >
                          Citations:
                        </span>
                        {claim.citedEvidenceIds.map((eid) => (
                          <button
                            key={eid}
                            type="button"
                            data-testid={`citation-${eid}`}
                            onClick={() => handleCitationClick(eid)}
                            style={{
                              background:
                                selectedEvidenceId === eid
                                  ? "#2563eb"
                                  : "#eff6ff",
                              color:
                                selectedEvidenceId === eid
                                  ? "#ffffff"
                                  : "#1d4ed8",
                              border: "1px solid #bfdbfe",
                              borderRadius: "4px",
                              padding: "2px 6px",
                              fontSize: "11px",
                              fontFamily: "monospace",
                              cursor: "pointer",
                              transition: "all 0.1s ease",
                            }}
                          >
                            [{eid}]
                          </button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* Analyst Feedback Form */}
          <section
            aria-labelledby="feedback-heading"
            style={{
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              padding: "16px",
            }}
          >
            <h2
              id="feedback-heading"
              style={{ margin: "0 0 12px 0", fontSize: "18px", color: "#1e293b" }}
            >
              Analyst Adjudication & Feedback
            </h2>

            <form
              onSubmit={handleFeedbackSubmit}
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              {/* Disposition Selection */}
              <div>
                <label
                  htmlFor={`${formId}-disposition`}
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "4px",
                    color: "#334155",
                  }}
                >
                  Case Disposition:
                </label>
                <select
                  id={`${formId}-disposition`}
                  aria-label="Case Disposition"
                  value={disposition}
                  onChange={(e) =>
                    setDisposition(e.target.value as Disposition)
                  }
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "14px",
                    background: "#ffffff",
                  }}
                >
                  <option value="CONFIRMED_SUSPICIOUS">
                    CONFIRMED_SUSPICIOUS (Suspicious Activity Detected)
                  </option>
                  <option value="FALSE_POSITIVE">
                    FALSE_POSITIVE (Legitimate Activity)
                  </option>
                  <option value="ESCALATE">
                    ESCALATE (Escalate to Senior Compliance)
                  </option>
                  <option value="INSUFFICIENT_EVIDENCE">
                    INSUFFICIENT_EVIDENCE (Requires Additional Data)
                  </option>
                </select>
              </div>

              {/* Analyst ID */}
              <div>
                <label
                  htmlFor={`${formId}-analyst-id`}
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "4px",
                    color: "#334155",
                  }}
                >
                  Analyst ID:
                </label>
                <input
                  id={`${formId}-analyst-id`}
                  type="text"
                  aria-label="Analyst ID"
                  value={analystId}
                  onChange={(e) => setAnalystId(e.target.value)}
                  placeholder="e.g. analyst_01"
                  required
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "14px",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* Reason / Rationale */}
              <div>
                <label
                  htmlFor={`${formId}-reason`}
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "4px",
                    color: "#334155",
                  }}
                >
                  Adjudication Rationale:
                </label>
                <textarea
                  id={`${formId}-reason`}
                  aria-label="Adjudication Rationale"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Enter detailed rationale for the chosen disposition..."
                  rows={3}
                  required
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "14px",
                    boxSizing: "border-box",
                    fontFamily: "inherit",
                  }}
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting || !reason.trim() || !analystId.trim()}
                style={{
                  background: isSubmitting ? "#94a3b8" : "#2563eb",
                  color: "#ffffff",
                  padding: "10px 16px",
                  borderRadius: "6px",
                  border: "none",
                  fontWeight: 600,
                  fontSize: "14px",
                  cursor: isSubmitting ? "not-allowed" : "pointer",
                  transition: "background 0.15s ease",
                }}
              >
                {isSubmitting ? "Submitting..." : "Submit Disposition"}
              </button>

              {/* Feedback Result Notification */}
              {submissionResult && (
                <div
                  data-testid="feedback-result"
                  style={{
                    padding: "10px",
                    borderRadius: "6px",
                    fontSize: "13px",
                    background: submissionResult.success ? "#f0fdf4" : "#fef2f2",
                    color: submissionResult.success ? "#166534" : "#991b1b",
                    border: submissionResult.success
                      ? "1px solid #bbf7d0"
                      : "1px solid #fecaca",
                  }}
                >
                  {submissionResult.message}
                </div>
              )}
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}

export default CaseWorkspace;
