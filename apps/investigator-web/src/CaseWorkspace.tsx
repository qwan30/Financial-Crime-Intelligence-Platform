import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  expandGraph,
  FeedbackEnvelope,
  FeedbackRequest,
  fetchWorkbenchData,
  pinEvidence,
  refreshHypothesis,
  TypologyTag,
  WorkbenchData,
} from "./api";
import { CanvasActions, ForensicCanvas } from "./canvas/ForensicCanvas";
import { CanvasControls, PlaybackSpeed } from "./canvas/CanvasControls";
import { clusterProjection, fundingClusters } from "./canvas/clusters";
import { InspectorDrawer } from "./canvas/InspectorDrawer";
import { initialView, projectGraph, Selection, ViewState } from "./canvas/model";

export type CaseWorkspaceProps = {
  workbenchData: WorkbenchData;
  onSubmitFeedback?: (feedback: FeedbackRequest) => Promise<FeedbackEnvelope | void>;
  onSelectEvidence?: (evidenceId: string) => void;
};

export const CaseWorkspace: React.FC<CaseWorkspaceProps> = ({
  workbenchData,
  onSubmitFeedback,
  onSelectEvidence,
}) => {
  // Case State
  const [currentCase, setCurrentCase] = useState(workbenchData.case);
  const [evidence, setEvidence] = useState(workbenchData.evidence);
  const [pins, setPins] = useState(workbenchData.pins ?? []);
  const [trace, setTrace] = useState(workbenchData.trace);
  const [hypothesis, setHypothesis] = useState(workbenchData.hypothesis);
  const [hypothesisSnapshotHash, setHypothesisSnapshotHash] = useState<string | null>(
    workbenchData.hypothesisSnapshotHash ?? null
  );

  // View & UI State
  const [view, setView] = useState<ViewState>(() => initialView(workbenchData.trace));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);
  const [analystId, setAnalystId] = useState("");
  const [pendingPinEdgeId, setPendingPinEdgeId] = useState<string | null>(null);
  const [isMutating, setIsMutating] = useState(false);
  const [isExpanding, setIsExpanding] = useState(false);
  const [isRefreshingHypothesis, setIsRefreshingHypothesis] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const actionsRef = useRef<CanvasActions | null>(null);
  const refreshTimerRef = useRef<number | null>(null);

  // Time range
  const timeMin = useMemo(() => {
    return trace.timeMin ? Date.parse(trace.timeMin) : null;
  }, [trace.timeMin]);

  const timeMax = useMemo(() => {
    return trace.timeMax ? Date.parse(trace.timeMax) : null;
  }, [trace.timeMax]);

  // Derived graph projections
  const projection = useMemo(() => {
    return projectGraph(trace, view);
  }, [trace, view]);

  const clusters = useMemo(() => {
    return fundingClusters(trace, view.cutoffMs);
  }, [trace, view.cutoffMs]);

  const clusterProj = useMemo(() => {
    return clusterProjection(trace, view, projection, clusters);
  }, [trace, view, projection, clusters]);

  const pinnedEdgeIds = useMemo(() => {
    return new Set(pins.map((p) => p.edgeId));
  }, [pins]);

  // Monotonic Clock Playback
  useEffect(() => {
    if (!playing || timeMin === null || timeMax === null || timeMin >= timeMax) {
      return;
    }

    let animationFrameId: number;
    let lastTime = performance.now();

    const tick = (now: number) => {
      const rawDelta = now - lastTime;
      lastTime = now;
      const delta = Math.min(250, rawDelta);

      setView((prev) => {
        const currentCutoff = prev.cutoffMs ?? timeMin;
        const totalDurationMs = 30_000 / speed;
        const progress = (delta / totalDurationMs) * (timeMax - timeMin);
        const nextCutoff = currentCutoff + progress;

        if (nextCutoff >= timeMax) {
          setPlaying(false);
          return { ...prev, cutoffMs: timeMax };
        }
        return { ...prev, cutoffMs: nextCutoff };
      });

      animationFrameId = requestAnimationFrame(tick);
    };

    animationFrameId = requestAnimationFrame(tick);

    const handleVisibilityChange = () => {
      if (document.hidden) {
        setPlaying(false);
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelAnimationFrame(animationFrameId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [playing, speed, timeMin, timeMax]);

  // Debounced Hypothesis Refresh
  const scheduleHypothesisRefresh = useCallback(
    (caseId: string, snapshotHash: string) => {
      clearTimeout(refreshTimerRef.current ?? undefined);
      setIsRefreshingHypothesis(true);
      refreshTimerRef.current = window.setTimeout(async () => {
        try {
          const res = await refreshHypothesis(caseId, snapshotHash);
          if (res.success) {
            setHypothesis(res.data.hypothesis);
            setHypothesisSnapshotHash(res.data.snapshotHash);
          } else if (res.error.code === "SNAPSHOT_CONFLICT") {
            // Reconcile workbench on 409
            const freshWb = await fetchWorkbenchData(caseId);
            if (freshWb.success) {
              setCurrentCase(freshWb.data.case);
              setEvidence(freshWb.data.evidence);
              setPins(freshWb.data.pins);
              setHypothesis(freshWb.data.hypothesis);
              setHypothesisSnapshotHash(freshWb.data.hypothesisSnapshotHash);
            }
          }
        } finally {
          setIsRefreshingHypothesis(false);
        }
      }, 400);
    },
    []
  );

  // Optimistic Pinning with Rollback
  const handleTogglePin = useCallback(
    async (edgeId: string, isPinned: boolean, typologyTag: TypologyTag | null) => {
      if (!analystId.trim() || !workbenchData.pinningAvailable || isMutating) {
        return;
      }

      setIsMutating(true);
      setPendingPinEdgeId(edgeId);

      const oldPins = pins;
      const oldHash = currentCase.snapshotHash;

      // Optimistic update
      if (isPinned) {
        const edge = trace.edges.find((e) => e.edgeId === edgeId);
        if (edge) {
          const optPin = {
            edgeId,
            evidenceId: `pending-${edgeId}`,
            analystId: analystId.trim(),
            typologyTag,
            updatedAt: new Date().toISOString(),
            transaction: edge,
          };
          setPins((prev) => [...prev.filter((p) => p.edgeId !== edgeId), optPin]);
        }
      } else {
        setPins((prev) => prev.filter((p) => p.edgeId !== edgeId));
      }

      try {
        const res = await pinEvidence(
          currentCase.caseId,
          {
            edge_id: edgeId,
            analyst_id: analystId.trim(),
            is_pinned: isPinned,
            typology_tag: typologyTag,
          },
          oldHash
        );

        if (res.success) {
          setCurrentCase(res.data.case);
          setEvidence(res.data.evidence);
          setPins(res.data.pins);
          scheduleHypothesisRefresh(currentCase.caseId, res.data.new_snapshot_hash);
        } else {
          // Rollback on error
          setPins(oldPins);
          if (res.error.code === "SNAPSHOT_CONFLICT") {
            const freshWb = await fetchWorkbenchData(currentCase.caseId);
            if (freshWb.success) {
              setCurrentCase(freshWb.data.case);
              setEvidence(freshWb.data.evidence);
              setPins(freshWb.data.pins);
            }
          }
          alert(`Lỗi khi cập nhật ghim SAR: ${res.error.message}`);
        }
      } catch (err: unknown) {
        setPins(oldPins);
        const msg = err instanceof Error ? err.message : "Network error";
        alert(`Lỗi kết nối khi ghim SAR: ${msg}`);
      } finally {
        setIsMutating(false);
        setPendingPinEdgeId(null);
      }
    },
    [
      analystId,
      workbenchData.pinningAvailable,
      isMutating,
      pins,
      currentCase,
      trace.edges,
      scheduleHypothesisRefresh,
    ]
  );

  // Hop Expansion
  const handleExpandHop = useCallback(async () => {
    if (view.selection?.kind !== "node" || isExpanding) return;
    const nodeId = view.selection.id;
    const knownEdgeIds = trace.edges.map((e) => e.edgeId);

    setIsExpanding(true);
    try {
      const res = await expandGraph(currentCase.caseId, {
        nodeId,
        knownEdgeIds,
        snapshotHash: currentCase.snapshotHash,
      });

      if (res.success) {
        const newEdges = res.data.edges;
        const newNodes = res.data.nodes;

        // Check if new edges discovered
        if (newEdges.length <= knownEdgeIds.length) {
          alert("Không còn giao dịch trong phạm vi 3 hop");
        }

        setTrace((prev) => ({
          ...prev,
          nodes: newNodes,
          edges: newEdges,
          isTruncated: res.data.isTruncated,
          totalHops: res.data.totalHops,
          hopByNodeId: res.data.hopByNodeId ?? prev.hopByNodeId,
          timeMin: res.data.timeMin ?? prev.timeMin,
          timeMax: res.data.timeMax ?? prev.timeMax,
          unknownTimeEdgeCount: res.data.unknownTimeEdgeCount ?? prev.unknownTimeEdgeCount,
        }));
      } else {
        alert(`Mở rộng Hop thất bại: ${res.error.message}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error";
      alert(`Lỗi kết nối khi mở rộng Hop: ${msg}`);
    } finally {
      setIsExpanding(false);
    }
  }, [view.selection, isExpanding, trace.edges, currentCase]);

  // Reveal hidden branch
  const handleRevealBranch = useCallback((edgeIds: string[]) => {
    setView((prev) => {
      const nextOverride = new Set(prev.viewOverrideEdgeIds);
      for (const eid of edgeIds) {
        nextOverride.add(eid);
      }
      return { ...prev, viewOverrideEdgeIds: nextOverride };
    });
  }, []);

  // Restore hidden
  const handleRestoreHidden = useCallback(() => {
    setView((prev) => ({
      ...prev,
      manuallyHiddenEdgeIds: new Set(),
      viewOverrideEdgeIds: new Set(),
    }));
  }, []);

  // Play / Pause toggle
  const handlePlayToggle = useCallback(() => {
    if (!playing) {
      if (timeMax !== null && view.cutoffMs !== null && view.cutoffMs >= timeMax) {
        setView((prev) => ({ ...prev, cutoffMs: timeMin }));
      }
    }
    setPlaying((p) => !p);
  }, [playing, timeMax, timeMin, view.cutoffMs]);

  // Selection handler
  const handleSelection = useCallback((sel: Selection) => {
    setView((prev) => ({ ...prev, selection: sel }));
  }, []);

  // Focus handler
  const handleFocus = useCallback((nodeId: string | null) => {
    setView((prev) => ({ ...prev, focusedNodeId: nodeId }));
  }, []);

  // Hidden flow click from card
  const handleHiddenFlowClick = useCallback((nodeId: string) => {
    setView((prev) => ({
      ...prev,
      selection: { kind: "node", id: nodeId },
      focusedNodeId: nodeId,
    }));
  }, []);

  // Toggle cluster expansion
  const handleToggleCluster = useCallback((clusterId: string) => {
    setView((prev) => {
      const nextExpanded = new Set(prev.expandedClusterIds);
      if (nextExpanded.has(clusterId)) {
        nextExpanded.delete(clusterId);
      } else {
        nextExpanded.add(clusterId);
      }
      return { ...prev, expandedClusterIds: nextExpanded };
    });
  }, []);

  // Keyboard shortcut actions
  const handleTogglePinSelected = useCallback(() => {
    if (view.selection?.kind === "edge") {
      const edgeId = view.selection.id;
      const isPinned = pinnedEdgeIds.has(edgeId);
      handleTogglePin(edgeId, !isPinned, null);
    }
  }, [view.selection, pinnedEdgeIds, handleTogglePin]);

  const handleHideSelected = useCallback(() => {
    if (view.selection?.kind === "edge") {
      const edgeId = view.selection.id;
      setView((prev) => {
        const nextHidden = new Set(prev.manuallyHiddenEdgeIds);
        nextHidden.add(edgeId);
        return { ...prev, manuallyHiddenEdgeIds: nextHidden };
      });
    } else if (view.selection?.kind === "node") {
      const nodeId = view.selection.id;
      const incidentEdges = trace.edges.filter(
        (e) => e.source === nodeId || e.target === nodeId
      );
      setView((prev) => {
        const nextHidden = new Set(prev.manuallyHiddenEdgeIds);
        for (const e of incidentEdges) {
          nextHidden.add(e.edgeId);
        }
        return { ...prev, manuallyHiddenEdgeIds: nextHidden };
      });
    }
  }, [view.selection, trace.edges]);

  const handleClearSelection = useCallback(() => {
    setView((prev) => ({ ...prev, selection: null, focusedNodeId: null }));
  }, []);

  return (
    <div
      className="case-workspace-layout"
      data-testid="case-workspace"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 65fr) minmax(0, 35fr)",
        height: "100%",
        width: "100%",
        minHeight: 0,
        overflow: "hidden",
        background: "#07090e",
      }}
    >
      {/* 65% Left Canvas Area */}
      <div
        className="canvas-area-wrapper"
        data-testid="trace-graph-container"
        style={{
          position: "relative",
          height: "100%",
          width: "100%",
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        <ForensicCanvas
          caseId={currentCase.caseId}
          trace={trace}
          view={view}
          projection={projection}
          clusters={clusterProj}
          pinnedEdgeIds={pinnedEdgeIds}
          pendingPinEdgeId={pendingPinEdgeId}
          onSelection={handleSelection}
          onFocus={handleFocus}
          onHiddenFlow={handleHiddenFlowClick}
          onToggleCluster={handleToggleCluster}
          actionsRef={actionsRef}
        />

        <CanvasControls
          view={view}
          timeMin={timeMin}
          timeMax={timeMax}
          playing={playing}
          speed={speed}
          expanding={isExpanding}
          canExpand={view.selection?.kind === "node" && trace.edges.length < 100}
          hiddenCount={view.manuallyHiddenEdgeIds.size}
          totalLoadedEdges={trace.edges.length}
          isTruncated={trace.isTruncated}
          unknownTimeCount={trace.unknownTimeEdgeCount}
          onLayout={(layout) => {
            setView((prev) => ({ ...prev, layout }));
            actionsRef.current?.applyLayout(layout);
          }}
          onAmount={(amountVnd) => {
            setView((prev) => ({ ...prev, amountThresholdVnd: amountVnd }));
          }}
          onCutoff={(cutoffMs) => {
            setPlaying(false);
            setView((prev) => ({ ...prev, cutoffMs }));
          }}
          onPlay={handlePlayToggle}
          onSpeed={(s) => setSpeed(s)}
          onFit={() => actionsRef.current?.fit()}
          onExpand={handleExpandHop}
          onRestoreHidden={handleRestoreHidden}
          onTogglePinSelected={handleTogglePinSelected}
          onHideSelected={handleHideSelected}
          onClearSelection={handleClearSelection}
        />
      </div>

      {/* 35% Right Inspector Drawer */}
      <div
        className="inspector-area-wrapper"
        style={{
          height: "100%",
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        <InspectorDrawer
          currentCase={currentCase}
          evidence={evidence}
          pins={pins}
          trace={trace}
          view={view}
          projection={projection}
          clusters={clusterProj}
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={(eid) => {
            setSelectedEvidenceId(eid);
            if (eid && onSelectEvidence) onSelectEvidence(eid);
          }}
          onSelection={handleSelection}
          analystId={analystId}
          onAnalystIdChange={setAnalystId}
          isMutating={isMutating}
          pinningAvailable={workbenchData.pinningAvailable}
          onTogglePin={handleTogglePin}
          onToggleCluster={handleToggleCluster}
          onRevealBranch={handleRevealBranch}
          hypothesis={hypothesis}
          isRefreshingHypothesis={isRefreshingHypothesis}
          hypothesisSnapshotHash={hypothesisSnapshotHash}
          onSubmitFeedback={onSubmitFeedback}
          onMoveNode={(dx, dy) => actionsRef.current?.moveSelectedNode(dx, dy)}
        />
      </div>
    </div>
  );
};
