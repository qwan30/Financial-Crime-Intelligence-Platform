import React, { useId, useMemo, useState } from "react";
import type {
  CaseResponse,
  Disposition,
  EvidenceResponse,
  FeedbackEnvelope,
  FeedbackRequest,
  HypothesisResponse,
  PinnedEvidenceResponse,
  TraceEdgeResponse,
  TraceGraphResponse,
  TraceNodeResponse,
  TypologyTag,
} from "../api";
import type { ClusterProjection } from "./ForensicCanvas";
import { formatTransaction, formatVndMillions, Projection, Selection, ViewState } from "./model";

export type InspectorDrawerProps = {
  currentCase: CaseResponse;
  evidence: EvidenceResponse[];
  pins: PinnedEvidenceResponse[];
  trace: TraceGraphResponse;
  view: ViewState;
  projection: Projection;
  clusters: ClusterProjection;
  selectedEvidenceId: string | null;
  onSelectEvidence: (evidenceId: string | null) => void;
  onSelection: (selection: Selection) => void;
  // Pinning
  analystId: string;
  onAnalystIdChange: (id: string) => void;
  isMutating: boolean;
  pinningAvailable: boolean;
  onTogglePin: (
    edgeId: string,
    isPinned: boolean,
    typologyTag: TypologyTag | null
  ) => Promise<void>;
  // Cluster toggle
  onToggleCluster: (clusterId: string) => void;
  // View reveal
  onRevealBranch: (edgeIds: string[]) => void;
  // Copilot
  hypothesis: HypothesisResponse;
  isRefreshingHypothesis: boolean;
  hypothesisSnapshotHash: string | null;
  // Feedback
  onSubmitFeedback?: (feedback: FeedbackRequest) => Promise<FeedbackEnvelope | void>;
  // Movement for accessible card position
  onMoveNode?: (dx: number, dy: number) => void;
};

export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({
  currentCase,
  evidence,
  pins,
  trace,
  view,
  projection,
  clusters,
  selectedEvidenceId,
  onSelectEvidence,
  onSelection,
  analystId,
  onAnalystIdChange,
  isMutating,
  pinningAvailable,
  onTogglePin,
  onToggleCluster,
  onRevealBranch,
  hypothesis,
  isRefreshingHypothesis,
  hypothesisSnapshotHash,
  onSubmitFeedback,
  onMoveNode,
}) => {
  const analystInputId = useId();
  const dispositionSelectId = useId();
  const rationaleTextareaId = useId();

  // Feedback form state
  const [disposition, setDisposition] = useState<Disposition>("CONFIRMED_SUSPICIOUS");
  const [rationale, setRationale] = useState("");
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  // Active selected edge typology tag state
  const [selectedEdgeTag, setSelectedEdgeTag] = useState<TypologyTag | null>(null);

  // Selected item lookup
  const selectedNode: TraceNodeResponse | undefined = useMemo(() => {
    if (view.selection?.kind === "node") {
      return trace.nodes.find((n) => n.nodeId === view.selection?.id);
    }
    return undefined;
  }, [view.selection, trace.nodes]);

  const selectedEdge: TraceEdgeResponse | undefined = useMemo(() => {
    if (view.selection?.kind === "edge") {
      const e = trace.edges.find((item) => item.edgeId === view.selection?.id);
      if (e) return e;
      const p = pins.find((item) => item.edgeId === view.selection?.id);
      if (p) return p.transaction;
    }
    return undefined;
  }, [view.selection, trace.edges, pins]);

  const selectedCluster = useMemo(() => {
    if (view.selection?.kind === "cluster") {
      return clusters.clusters.find((c) => c.id === view.selection?.id);
    }
    return undefined;
  }, [view.selection, clusters.clusters]);

  const isSelectedEdgePinned = useMemo(() => {
    if (!selectedEdge) return false;
    return pins.some((p) => p.edgeId === selectedEdge.edgeId);
  }, [selectedEdge, pins]);

  const currentPinOfSelectedEdge = useMemo(() => {
    if (!selectedEdge) return undefined;
    return pins.find((p) => p.edgeId === selectedEdge.edgeId);
  }, [selectedEdge, pins]);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analystId.trim()) {
      setFeedbackError("Vui lòng nhập Mã điều tra viên (Analyst ID)");
      return;
    }
    if (!rationale.trim()) {
      setFeedbackError("Vui lòng nhập Lý do đánh giá");
      return;
    }

    setIsSubmittingFeedback(true);
    setFeedbackError(null);

    const payload: FeedbackRequest = {
      eventId: `fb-${Date.now()}`,
      analystId: analystId.trim(),
      disposition,
      reason: rationale.trim(),
      createdAt: new Date().toISOString(),
      modelVersion: hypothesis.modelVersion ?? null,
      snapshotHash: currentCase.snapshotHash,
    };

    try {
      if (onSubmitFeedback) {
        const res = await onSubmitFeedback(payload);
        if (res && !res.success) {
          setFeedbackError(res.error.message || "Gửi phản hồi thất bại");
          return;
        }
      }
      setFeedbackSuccess(true);
      setRationale("");
      setTimeout(() => setFeedbackSuccess(false), 4000);
    } catch (err: unknown) {
      setFeedbackError(err instanceof Error ? err.message : "Gửi phản hồi thất bại");
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <aside
      className="inspector-drawer"
      data-testid="inspector-drawer"
      style={{
        width: "100%",
        height: "100%",
        overflowY: "auto",
        background: "#0c1322",
        borderLeft: "1px solid #1e293b",
        color: "#f8fafc",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontSize: "13px",
        boxSizing: "border-box",
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
        gap: "24px",
      }}
    >
      {/* 1. Case Header Info */}
      <section style={{ borderBottom: "1px solid #1e293b", paddingBottom: "14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
            Vụ án: {currentCase.caseId}
          </h2>
          <span
            data-testid="seed-entity"
            style={{
              fontSize: "11px",
              background: "rgba(56, 189, 248, 0.15)",
              color: "#38bdf8",
              padding: "2px 8px",
              borderRadius: "4px",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              fontFamily: "monospace",
            }}
          >
            Mục tiêu: {currentCase.seedEntity}
          </span>
        </div>
        <div style={{ marginTop: "6px", fontSize: "11px", color: "#64748b", fontFamily: "monospace", wordBreak: "break-all" }}>
          Hash: <span data-testid="snapshot-hash">{currentCase.snapshotHash}</span>
        </div>
      </section>

      {/* 2. Selection Detail Section */}
      <section style={{ borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
        <h3 style={{ margin: "0 0 10px 0", fontSize: "14px", fontWeight: 600, color: "#94a3b8" }}>
          Chi tiết mục đã chọn
        </h3>

        {selectedNode && (
          <div data-testid="node-detail" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ fontSize: "15px", fontWeight: 700, color: "#38bdf8" }}>
              {selectedNode.accountHolderName ?? selectedNode.nodeId}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "12px", color: "#cbd5e1" }}>
              <div><strong>Ngân hàng:</strong> {selectedNode.bankShortName ?? "Chưa có dữ liệu"}</div>
              <div><strong>Số tài khoản:</strong> •••• {selectedNode.accountLast4 ?? "----"}</div>
              <div><strong>Điểm rủi ro:</strong> {selectedNode.riskScore !== null ? selectedNode.riskScore.toFixed(2) : "Chưa có dữ liệu"}</div>
              <div><strong>Khoảng cách:</strong> {trace.hopByNodeId[selectedNode.nodeId] ?? 1} hop</div>
              <div><strong>Huy hiệu:</strong> {selectedNode.badge ?? (selectedNode.isSeed ? "SEED_HUB" : "Chưa có")}</div>
              <div><strong>Loại:</strong> {selectedNode.entityType}</div>
            </div>

            {/* Hidden flows info if present */}
            {projection.amountHiddenByNode.has(selectedNode.nodeId) && (
              <div style={{ marginTop: "6px", background: "rgba(30, 41, 59, 0.6)", borderRadius: "6px", padding: "8px 10px" }}>
                <div style={{ color: "#f59e0b", fontWeight: 600, fontSize: "12px", marginBottom: "4px" }}>
                  Có {projection.amountHiddenByNode.get(selectedNode.nodeId)?.edgeIds.length} giao dịch bị ẩn (Tổng:{" "}
                  {formatVndMillions(projection.amountHiddenByNode.get(selectedNode.nodeId)!.amountVnd)})
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const edgeIds = projection.amountHiddenByNode.get(selectedNode.nodeId)?.edgeIds ?? [];
                    onRevealBranch(edgeIds);
                  }}
                  style={{
                    background: "#2563eb",
                    border: "none",
                    color: "#ffffff",
                    borderRadius: "4px",
                    padding: "4px 10px",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Ghim hiển thị nhánh này
                </button>
              </div>
            )}

            {/* Directional movement buttons for accessible node repositioning */}
            {onMoveNode && (
              <div style={{ display: "flex", gap: "4px", marginTop: "6px", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "#64748b" }}>Di chuyển (10px):</span>
                <button type="button" onClick={() => onMoveNode(0, -10)} style={{ padding: "2px 6px", fontSize: "11px" }}>▲</button>
                <button type="button" onClick={() => onMoveNode(0, 10)} style={{ padding: "2px 6px", fontSize: "11px" }}>▼</button>
                <button type="button" onClick={() => onMoveNode(-10, 0)} style={{ padding: "2px 6px", fontSize: "11px" }}>◀</button>
                <button type="button" onClick={() => onMoveNode(10, 0)} style={{ padding: "2px 6px", fontSize: "11px" }}>▶</button>
              </div>
            )}
          </div>
        )}

        {selectedEdge && (
          <div data-testid="edge-detail" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "monospace", fontWeight: 700, color: isSelectedEdgePinned ? "#c084fc" : "#38bdf8" }}>
                {selectedEdge.edgeId}
              </span>
              {isSelectedEdgePinned && (
                <span style={{ fontSize: "11px", background: "rgba(192, 132, 252, 0.2)", color: "#c084fc", padding: "2px 6px", borderRadius: "4px", fontWeight: 600 }}>
                  GHIM SAR
                </span>
              )}
            </div>
            <div style={{ fontSize: "12px", color: "#cbd5e1" }}>
              <div><strong>Từ:</strong> {selectedEdge.source} → <strong>Đến:</strong> {selectedEdge.target}</div>
              <div><strong>Số tiền:</strong> {formatTransaction(selectedEdge)} ({selectedEdge.flowAmount.toLocaleString()} {selectedEdge.currency ?? "VND"})</div>
              <div><strong>Quan hệ:</strong> {selectedEdge.relationshipType} ({((selectedEdge.identityConfidence ?? 1) * 100).toFixed(0)}%)</div>
              <div><strong>Thời gian:</strong> {selectedEdge.timestamp ? new Date(selectedEdge.timestamp).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }) : "Chưa có dữ liệu"}</div>
            </div>

            {/* Typology Tag Selector */}
            <div style={{ marginTop: "4px" }}>
              <label style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginBottom: "2px" }}>
                Gán nhãn hành vi điều tra:
              </label>
              <select
                value={selectedEdgeTag ?? currentPinOfSelectedEdge?.typologyTag ?? ""}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedEdgeTag(val ? (val as TypologyTag) : null);
                }}
                disabled={isMutating}
                style={{ width: "100%", background: "#1e293b", color: "#f8fafc", border: "1px solid #334155", borderRadius: "4px", padding: "4px 8px", fontSize: "12px" }}
              >
                <option value="">-- Không phân loại --</option>
                <option value="SEED_HUB">SEED / HUB (Điểm tập trung)</option>
                <option value="SMURFING">SMURFING (Nạp tiền nhỏ lẻ)</option>
                <option value="SHELL_CORP">SHELL CORP (Công ty bình phong)</option>
                <option value="LAYERING">LAYERING (Phân tầng rửa tiền)</option>
                <option value="CASHOUT">CASHOUT (Rút tiền mặt)</option>
                <option value="CRYPTO_OTC">CRYPTO OTC (Tiền mã hóa)</option>
                <option value="BENIGN">BENIGN (Hợp pháp / Thông thường)</option>
              </select>
            </div>

            {/* Pin / Unpin Button */}
            <div style={{ marginTop: "6px" }}>
              <button
                type="button"
                data-testid="pin-toggle-btn"
                disabled={isMutating || !pinningAvailable || !analystId.trim()}
                aria-pressed={isSelectedEdgePinned}
                onClick={async () => {
                  const tag = selectedEdgeTag ?? currentPinOfSelectedEdge?.typologyTag ?? null;
                  await onTogglePin(selectedEdge.edgeId, !isSelectedEdgePinned, tag);
                }}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  border: isSelectedEdgePinned ? "1px solid #c084fc" : "none",
                  background: isSelectedEdgePinned ? "transparent" : "#c084fc",
                  color: isSelectedEdgePinned ? "#c084fc" : "#000000",
                  fontWeight: 600,
                  cursor: isMutating || !pinningAvailable || !analystId.trim() ? "not-allowed" : "pointer",
                  opacity: isMutating || !pinningAvailable || !analystId.trim() ? 0.5 : 1,
                  fontSize: "12px",
                }}
              >
                {isMutating
                  ? "Đang lưu..."
                  : isSelectedEdgePinned
                  ? "Bỏ ghim khỏi Hồ Sơ SAR"
                  : "Ghim Giao Dịch Này vào Hồ Sơ SAR"}
              </button>
              {!analystId.trim() && (
                <div style={{ fontSize: "11px", color: "#f59e0b", marginTop: "4px" }}>
                  * Nhập Mã điều tra viên bên dưới để kích hoạt ghim SAR
                </div>
              )}
              {!pinningAvailable && (
                <div style={{ fontSize: "11px", color: "#f43f5e", marginTop: "4px" }}>
                  * Lưu trữ SAR không khả dụng (PostgreSQL chưa cấu hình)
                </div>
              )}
            </div>
          </div>
        )}

        {selectedCluster && (
          <div data-testid="cluster-detail" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ fontWeight: 700, color: "#f59e0b" }}>
              Cụm {selectedCluster.memberNodeIds.length} Con la Nạp tiền • Tổng: {formatVndMillions(selectedCluster.amountVnd)}
            </div>
            <div style={{ fontSize: "11px", color: "#94a3b8" }}>
              Nhóm hành vi cùng mẫu; không phải kết luận tội phạm
            </div>
            <button
              type="button"
              onClick={() => onToggleCluster(selectedCluster.id)}
              style={{
                background: "#1e293b",
                border: "1px solid #475569",
                color: "#f8fafc",
                borderRadius: "4px",
                padding: "6px 12px",
                cursor: "pointer",
                fontSize: "12px",
                marginTop: "4px",
              }}
            >
              {view.expandedClusterIds.has(selectedCluster.id) ? "Thu gọn cụm" : "Mở rộng cụm"}
            </button>
            <div style={{ marginTop: "4px" }}>
              <strong style={{ fontSize: "11px", color: "#94a3b8" }}>Tài khoản thành viên:</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                {selectedCluster.memberNodeIds.map((mid) => (
                  <button
                    key={mid}
                    type="button"
                    onClick={() => {
                      onSelection({ kind: "node", id: mid });
                    }}
                    style={{ background: "#1e293b", border: "1px solid #334155", color: "#cbd5e1", borderRadius: "3px", padding: "2px 6px", fontSize: "11px", cursor: "pointer" }}
                  >
                    {mid}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {!selectedNode && !selectedEdge && !selectedCluster && (
          <div style={{ color: "#64748b", fontStyle: "italic", fontSize: "12px" }}>
            Chọn một nút hoặc giao dịch trên đồ thị để xem chi tiết.
          </div>
        )}
      </section>

      {/* 3. Pinned SAR Dossier Section */}
      <section style={{ borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
        <h3 style={{ margin: "0 0 10px 0", fontSize: "14px", fontWeight: 600, color: "#c084fc" }}>
          Chứng cứ đã ghim ({pins.length})
        </h3>
        {pins.length === 0 ? (
          <div style={{ color: "#64748b", fontSize: "12px" }}>
            Chưa có giao dịch nào được ghim vào hồ sơ SAR.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {pins.map((p) => (
              <div
                key={p.edgeId}
                onClick={() => onSelection({ kind: "edge", id: p.edgeId })}
                style={{
                  background: view.selection?.kind === "edge" && view.selection.id === p.edgeId ? "rgba(192, 132, 252, 0.2)" : "rgba(30, 41, 59, 0.5)",
                  border: "1px solid rgba(192, 132, 252, 0.4)",
                  borderRadius: "6px",
                  padding: "8px 10px",
                  cursor: "pointer",
                  transition: "background 0.15s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontWeight: 600, color: "#f8fafc" }}>{p.edgeId}</span>
                  <span style={{ fontSize: "10px", background: "#c084fc", color: "#000000", fontWeight: 700, padding: "1px 4px", borderRadius: "2px" }}>
                    GHIM SAR
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "#cbd5e1", marginTop: "2px" }}>
                  {p.transaction.source} → {p.transaction.target}: {formatVndMillions(BigInt(Math.round(p.transaction.flowAmount)))}
                </div>
                <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px", display: "flex", justifyContent: "space-between" }}>
                  <span>ĐTV: {p.analystId}</span>
                  {p.typologyTag && <span style={{ color: "#c084fc" }}>{p.typologyTag}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 4. Case Evidence Timeline Section */}
      <section style={{ borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
        <h3 style={{ margin: "0 0 10px 0", fontSize: "14px", fontWeight: 600, color: "#38bdf8" }}>
          Dòng thời gian chứng cứ ({evidence.length})
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {evidence.map((item) => {
            const isSelected = selectedEvidenceId === item.evidenceId;
            const isSupporting = item.polarity === "SUPPORTING";
            return (
              <div
                key={item.evidenceId}
                data-testid={`evidence-item-${item.evidenceId}`}
                onClick={() => onSelectEvidence(item.evidenceId)}
                style={{
                  background: isSelected ? "rgba(56, 189, 248, 0.2)" : "rgba(30, 41, 59, 0.4)",
                  border: isSelected ? "1px solid #38bdf8" : "1px solid #334155",
                  borderRadius: "6px",
                  padding: "8px 10px",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#94a3b8" }}>
                    {item.evidenceId}
                  </span>
                  <span
                    data-testid={`polarity-badge-${item.evidenceId}`}
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "1px 6px",
                      borderRadius: "4px",
                      background: isSupporting ? "rgba(16, 185, 129, 0.2)" : "rgba(14, 165, 233, 0.2)",
                      color: isSupporting ? "#10b981" : "#0ea5e9",
                      border: `1px solid ${isSupporting ? "#10b981" : "#0ea5e9"}`,
                    }}
                  >
                    {item.polarity}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "#f8fafc", marginTop: "4px" }}>
                  {item.payloadSummary}
                </div>
                <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px", display: "flex", justifyContent: "space-between" }}>
                  <span>Tham chiếu: {item.sourceReference}</span>
                  {item.confidence !== null && item.confidence !== undefined && (
                    <span>Độ tin cậy: {(item.confidence * 100).toFixed(0)}%</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 5. AI Hypothesis Copilot Section */}
      <section style={{ borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "#a855f7" }}>
            Giả thuyết điều tra (AI Copilot)
          </h3>
          <span
            data-testid={`status-badge-${hypothesis.status}`}
            style={{
              fontSize: "10px",
              fontWeight: 600,
              padding: "2px 6px",
              borderRadius: "4px",
              background: hypothesis.status === "HYPOTHESIS_GENERATED" ? "rgba(168, 85, 247, 0.2)" : "rgba(100, 116, 139, 0.2)",
              color: hypothesis.status === "HYPOTHESIS_GENERATED" ? "#c084fc" : "#94a3b8",
            }}
          >
            {isRefreshingHypothesis ? "Đang cập nhật..." : hypothesis.status}
          </span>
        </div>

        {hypothesisSnapshotHash && hypothesisSnapshotHash !== currentCase.snapshotHash && (
          <div style={{ fontSize: "11px", color: "#f59e0b", marginBottom: "6px" }}>
            * Giả thuyết cho snapshot trước; đang đồng bộ snapshot mới
          </div>
        )}

        <div style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: 1.5, background: "rgba(15, 23, 42, 0.6)", padding: "8px 10px", borderRadius: "6px" }}>
          {hypothesis.summary}
        </div>

        {hypothesis.claims && hypothesis.claims.length > 0 && (
          <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
            <strong style={{ fontSize: "11px", color: "#94a3b8" }}>Nhận định trọng yếu:</strong>
            {hypothesis.claims.map((claim, idx) => (
              <div key={idx} style={{ fontSize: "12px", color: "#f8fafc", background: "rgba(30, 41, 59, 0.4)", padding: "6px 8px", borderRadius: "4px" }}>
                <div>{claim.claimText}</div>
                {claim.citedEvidenceIds && claim.citedEvidenceIds.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                    {claim.citedEvidenceIds.map((cid) => (
                      <button
                        key={cid}
                        type="button"
                        onClick={() => onSelectEvidence(cid)}
                        style={{
                          background: "rgba(56, 189, 248, 0.15)",
                          color: "#38bdf8",
                          border: "1px solid rgba(56, 189, 248, 0.3)",
                          borderRadius: "3px",
                          padding: "1px 4px",
                          fontSize: "10px",
                          fontFamily: "monospace",
                          cursor: "pointer",
                        }}
                      >
                        [{cid}]
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 6. Analyst Feedback Section */}
      <section style={{ borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
        <h3 style={{ margin: "0 0 10px 0", fontSize: "14px", fontWeight: 600, color: "#f8fafc" }}>
          Phản hồi của điều tra viên
        </h3>
        <form onSubmit={handleFeedbackSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div>
            <label htmlFor={analystInputId} style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "2px" }}>
              Mã điều tra viên (Analyst ID) *:
            </label>
            <input
              id={analystInputId}
              type="text"
              placeholder="VD: analyst_01"
              value={analystId}
              onChange={(e) => onAnalystIdChange(e.target.value)}
              disabled={isMutating || isSubmittingFeedback}
              style={{
                width: "100%",
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "6px 8px",
                color: "#f8fafc",
                fontSize: "12px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label htmlFor={dispositionSelectId} style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "2px" }}>
              Kết luận xử lý (Disposition):
            </label>
            <select
              id={dispositionSelectId}
              value={disposition}
              onChange={(e) => setDisposition(e.target.value as Disposition)}
              disabled={isMutating || isSubmittingFeedback}
              style={{
                width: "100%",
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "6px 8px",
                color: "#f8fafc",
                fontSize: "12px",
                boxSizing: "border-box",
              }}
            >
              <option value="CONFIRMED_SUSPICIOUS">CONFIRMED_SUSPICIOUS (Xác nhận đáng ngờ)</option>
              <option value="FALSE_POSITIVE">FALSE_POSITIVE (Cảnh báo giả)</option>
              <option value="ESCALATE">ESCALATE (Báo cáo cấp cao hơn)</option>
              <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT_EVIDENCE (Chưa đủ chứng cứ)</option>
            </select>
          </div>

          <div>
            <label htmlFor={rationaleTextareaId} style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "2px" }}>
              Lý do đánh giá (Rationale) *:
            </label>
            <textarea
              id={rationaleTextareaId}
              rows={3}
              placeholder="Nhập nhận định điều tra chuyên môn..."
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              disabled={isMutating || isSubmittingFeedback}
              style={{
                width: "100%",
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "6px 8px",
                color: "#f8fafc",
                fontSize: "12px",
                boxSizing: "border-box",
              }}
            />
          </div>

          {feedbackError && (
            <div style={{ color: "#f43f5e", fontSize: "11px" }}>{feedbackError}</div>
          )}
          {feedbackSuccess && (
            <div style={{ color: "#10b981", fontSize: "11px" }}>Đã lưu phản hồi thành công!</div>
          )}

          <button
            type="submit"
            disabled={isMutating || isSubmittingFeedback || !analystId.trim()}
            style={{
              background: "#2563eb",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              padding: "8px 14px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: isMutating || isSubmittingFeedback || !analystId.trim() ? "not-allowed" : "pointer",
              opacity: isMutating || isSubmittingFeedback || !analystId.trim() ? 0.6 : 1,
            }}
          >
            {isSubmittingFeedback ? "Đang gửi..." : "Gửi đánh giá vụ án"}
          </button>
        </form>
      </section>

      {/* 7. Accessible Details Section */}
      <details style={{ fontSize: "11px", color: "#94a3b8", cursor: "pointer" }}>
        <summary><strong>Danh sách thực thể và giao dịch</strong></summary>
        <div style={{ marginTop: "6px", display: "flex", flexDirection: "column", gap: "4px" }}>
          <div><strong>Nút ({trace.nodes.length}):</strong></div>
          {trace.nodes.map((n) => (
            <div
              key={n.nodeId}
              onClick={() => onSelection({ kind: "node", id: n.nodeId })}
              style={{ cursor: "pointer", color: "#38bdf8" }}
            >
              • {n.accountHolderName ?? n.nodeId} ({n.entityType})
            </div>
          ))}
          <div style={{ marginTop: "6px" }}><strong>Giao dịch ({trace.edges.length}):</strong></div>
          {trace.edges.map((e) => (
            <div
              key={e.edgeId}
              onClick={() => onSelection({ kind: "edge", id: e.edgeId })}
              style={{ cursor: "pointer", color: "#c084fc" }}
            >
              • {e.edgeId}: {e.source} → {e.target}
            </div>
          ))}
        </div>
      </details>
    </aside>
  );
};
