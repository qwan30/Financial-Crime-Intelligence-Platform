import cytoscape, { Core, EventObject } from "cytoscape";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TraceGraphResponse, TraceNodeResponse } from "../api";
import {
  EdgeAnnotationView,
  LeaderLines,
  measureCardSize,
  measureTextWidth,
  NodeCardAnnotation,
} from "./annotations";
import "./canvas.css";
import {
  causalPositions,
  EdgeAnnotation,
  LayoutItem,
  placeEdgeAnnotations,
  Point,
  PositionMap,
  readPositions,
  Rect,
  separateCards,
  writePositions,
} from "./geometry";
import {
  edgeWidth,
  focusedElements,
  formatTransaction,
  LayoutName,
  Projection,
  Selection,
  ViewState,
} from "./model";

export type ClusterProjection = {
  clusters: Array<{
    id: string;
    targetId: string;
    memberNodeIds: string[];
    memberEdgeIds: string[];
    amountVnd: bigint;
    firstMs: number;
    lastMs: number;
  }>;
  ownerByNodeId: Map<string, string>;
  bundles: Array<{
    id: string;
    source: string;
    target: string;
    memberEdgeIds: string[];
    currency: string | null;
    amountVnd: bigint | null;
    firstMs: number;
    lastMs: number;
  }>;
};

export type CanvasActions = {
  fit(): void;
  applyLayout(layout: LayoutName): void;
  moveSelectedNode(dx: number, dy: number): void;
};

export type ForensicCanvasProps = {
  caseId: string;
  trace: TraceGraphResponse;
  view: ViewState;
  projection: Projection;
  clusters: ClusterProjection;
  pinnedEdgeIds: ReadonlySet<string>;
  pendingPinEdgeId: string | null;
  onSelection: (selection: Selection) => void;
  onFocus: (nodeId: string | null) => void;
  onHiddenFlow: (nodeId: string) => void;
  onToggleCluster: (clusterId: string) => void;
  actionsRef: React.RefObject<CanvasActions | null>;
};

export const ForensicCanvas: React.FC<ForensicCanvasProps> = ({
  caseId,
  trace,
  view,
  projection,
  clusters: _clusters,
  pinnedEdgeIds,
  pendingPinEdgeId: _pendingPinEdgeId,
  onSelection,
  onFocus,
  onHiddenFlow,
  onToggleCluster: _onToggleCluster,
  actionsRef,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [cardSizes, setCardSizes] = useState<Map<string, { width: number; height: number }>>(
    new Map()
  );
  const [renderedNodes, setRenderedNodes] = useState<
    Array<{ node: TraceNodeResponse; center: Point; size: { width: number; height: number } }>
  >([]);
  const [renderedEdgeAnnotations, setRenderedEdgeAnnotations] = useState<
    Array<{ annotation: EdgeAnnotation; label: string; isPinned: boolean; edgeId: string }>
  >([]);

  // Stable callback refs
  const onSelectionRef = useRef(onSelection);
  onSelectionRef.current = onSelection;
  const onFocusRef = useRef(onFocus);
  onFocusRef.current = onFocus;

  // Compute card size for each node
  useEffect(() => {
    const map = new Map<string, { width: number; height: number }>();
    for (const node of trace.nodes) {
      const hasHidden = projection.amountHiddenByNode.has(node.nodeId);
      map.set(node.nodeId, measureCardSize(node, hasHidden));
    }
    setCardSizes(map);
  }, [trace.nodes, projection.amountHiddenByNode]);

  // Derive layout item column for causal layout
  const getLayoutItem = useCallback(
    (node: TraceNodeResponse): LayoutItem => {
      let column: 0 | 1 | 2 | 3 = 1;
      if (node.badge === "SMURFING") {
        column = 0;
      } else if (node.isSeed || node.badge === "SEED_HUB") {
        column = 1;
      } else if (node.badge === "SHELL_CORP" || node.badge === "LAYERING") {
        column = 2;
      } else if (node.badge === "CASHOUT" || node.badge === "CRYPTO_OTC") {
        column = 3;
      } else {
        // Untyped / context node
        const hop = trace.hopByNodeId[node.nodeId] ?? 1;
        // Direct inbound only to seed goes to col 0
        const isInboundOnly =
          trace.edges.some((e) => e.source === node.nodeId) &&
          !trace.edges.some((e) => e.target === node.nodeId);
        if (isInboundOnly && hop <= 1) {
          column = 0;
        } else {
          column = Math.min(3, hop + 1) as 0 | 1 | 2 | 3;
        }
      }
      return { id: node.nodeId, kind: "node", column };
    },
    [trace.edges, trace.hopByNodeId]
  );

  // Focused elements
  const focused = useMemo(() => {
    return focusedElements(trace, projection.visibleEdgeIds, view.focusedNodeId);
  }, [trace, projection.visibleEdgeIds, view.focusedNodeId]);

  // Update DOM annotations from Cytoscape rendered positions
  const updateAnnotations = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const nodesList: Array<{
      node: TraceNodeResponse;
      center: Point;
      size: { width: number; height: number };
    }> = [];
    const occupiedCardRects: Rect[] = [];

    for (const node of trace.nodes) {
      const cyNode = cy.getElementById(node.nodeId);
      if (cyNode && cyNode.inside()) {
        const renderedPos = cyNode.renderedPosition();
        const size = cardSizes.get(node.nodeId) ?? { width: 170, height: 52 };
        nodesList.push({
          node,
          center: { x: renderedPos.x, y: renderedPos.y },
          size,
        });
        occupiedCardRects.push({
          x: renderedPos.x,
          y: renderedPos.y,
          width: size.width,
          height: size.height,
        });
      }
    }
    setRenderedNodes(nodesList);

    // Candidates for visible edges
    const candidates: Array<{
      edgeId: string;
      anchor: Point;
      angleDegrees: number;
      textWidth: number;
      textHeight: number;
    }> = [];
    const edgeLabelMap = new Map<string, string>();

    for (const edge of trace.edges) {
      if (!projection.visibleEdgeIds.has(edge.edgeId)) continue;
      const cyEdge = cy.getElementById(edge.edgeId);
      if (!cyEdge || !cyEdge.inside()) continue;

      const srcNode = cy.getElementById(edge.source);
      const tgtNode = cy.getElementById(edge.target);
      if (!srcNode || !tgtNode) continue;

      const p1 = srcNode.renderedPosition();
      const p2 = tgtNode.renderedPosition();

      let anchor: Point;
      let angle = 0;

      if (edge.source === edge.target) {
        anchor = { x: p1.x, y: p1.y - 45 };
        angle = 0;
      } else {
        anchor = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        angle = (Math.atan2(dy, dx) * 180) / Math.PI;
        while (angle > 90) angle -= 180;
        while (angle < -90) angle += 180;
      }

      const label = formatTransaction(edge);
      edgeLabelMap.set(edge.edgeId, label);
      const textW = measureTextWidth(label, "500 12px sans-serif");
      candidates.push({
        edgeId: edge.edgeId,
        anchor,
        angleDegrees: angle,
        textWidth: textW,
        textHeight: 18,
      });
    }

    const placed = placeEdgeAnnotations(candidates, occupiedCardRects, 12);
    setRenderedEdgeAnnotations(
      placed.map((a) => ({
        annotation: a,
        label: edgeLabelMap.get(a.edgeId) ?? a.edgeId,
        isPinned: pinnedEdgeIds.has(a.edgeId),
        edgeId: a.edgeId,
      }))
    );
  }, [trace.nodes, trace.edges, cardSizes, projection.visibleEdgeIds, pinnedEdgeIds]);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      boxSelectionEnabled: false,
      autounselectify: true,
      style: [
        {
          selector: "node",
          style: {
            shape: "round-rectangle",
            "background-opacity": 0,
            "border-width": 0,
            width: "data(width)",
            height: "data(height)",
            label: "",
          },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "data(lineColor)",
            "line-color": "data(lineColor)",
            width: "data(width)",
            "line-style": "data(lineStyle)" as cytoscape.Css.LineStyle,
            opacity: "data(opacity)" as unknown as number,
            label: "",
          },
        },
      ],
    });

    cyRef.current = cy;

    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        onSelectionRef.current(null);
        onFocusRef.current(null);
      }
    });

    cy.on("tap", "node", (evt: EventObject) => {
      const nid = evt.target.id();
      onSelectionRef.current({ kind: "node", id: nid });
      onFocusRef.current(nid);
    });

    cy.on("tap", "edge", (evt: EventObject) => {
      const eid = evt.target.id();
      onSelectionRef.current({ kind: "edge", id: eid });
    });

    cy.on("pan zoom", () => {
      updateAnnotations();
    });

    cy.on("drag", "node", () => {
      updateAnnotations();
    });

    cy.on("dragfree", "node", (evt: EventObject) => {
      const node = evt.target;
      const currentPos = node.position();
      const posMap: PositionMap = {};
      cy.nodes().forEach((n) => {
        posMap[n.id()] = n.position();
      });
      posMap[node.id()] = currentPos;
      writePositions(localStorage, caseId, posMap);
      updateAnnotations();
    });

    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => {
        cy.resize();
        updateAnnotations();
      });
      ro.observe(containerRef.current);
    }

    return () => {
      if (ro) ro.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [caseId, updateAnnotations]);

  // Sync elements and styles into Cytoscape
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cardSizes.size === 0) return;

    cy.batch(() => {
      // 1. Sync nodes
      const existingNodeIds = new Set(cy.nodes().map((n) => n.id()));
      const targetNodeIds = new Set(trace.nodes.map((n) => n.nodeId));

      // Remove nodes not in trace
      for (const nid of existingNodeIds) {
        if (!targetNodeIds.has(nid)) {
          cy.remove(cy.getElementById(nid));
        }
      }

      // Add or update nodes
      for (const node of trace.nodes) {
        const size = cardSizes.get(node.nodeId) ?? { width: 170, height: 52 };
        let cyNode = cy.getElementById(node.nodeId);
        if (cyNode.length === 0) {
          cyNode = cy.add({
            group: "nodes",
            data: {
              id: node.nodeId,
              isSeed: node.isSeed,
              hop: trace.hopByNodeId[node.nodeId] ?? 1,
              width: size.width,
              height: size.height,
            },
          });
        } else {
          cyNode.data({
            width: size.width,
            height: size.height,
            isSeed: node.isSeed,
            hop: trace.hopByNodeId[node.nodeId] ?? 1,
          });
        }
      }

      // 2. Sync edges
      const existingEdgeIds = new Set(cy.edges().map((e) => e.id()));
      const targetEdgeIds = new Set(trace.edges.map((e) => e.edgeId));

      for (const eid of existingEdgeIds) {
        if (!targetEdgeIds.has(eid)) {
          cy.remove(cy.getElementById(eid));
        }
      }

      for (const edge of trace.edges) {
        const isVisible = projection.visibleEdgeIds.has(edge.edgeId);
        const isPinned = pinnedEdgeIds.has(edge.edgeId);
        const isDimmed = view.focusedNodeId !== null && !focused.edgeIds.has(edge.edgeId);

        const w = edgeWidth(edge);
        const lineStyle = edge.identityConfidence < 0.8 ? "dashed" : "solid";
        const lineColor = isPinned ? "#c084fc" : "#64748b";
        const opacity = !isVisible ? 0 : isDimmed ? 0.2 : 1.0;

        let cyEdge = cy.getElementById(edge.edgeId);
        if (cyEdge.length === 0) {
          cy.add({
            group: "edges",
            data: {
              id: edge.edgeId,
              source: edge.source,
              target: edge.target,
              width: w,
              lineStyle,
              lineColor,
              opacity,
            },
          });
        } else {
          cyEdge.data({
            width: w,
            lineStyle,
            lineColor,
            opacity,
          });
        }
      }
    });

    // 3. Apply positions if not yet placed
    const saved = readPositions(localStorage, caseId);
    let needsInitialPositions = false;
    cy.nodes().forEach((n) => {
      if (!saved[n.id()]) needsInitialPositions = true;
    });

    if (needsInitialPositions) {
      const items = trace.nodes.map((n) => getLayoutItem(n));
      const pos = causalPositions(items, cardSizes);
      cy.batch(() => {
        for (const [id, p] of Object.entries(pos)) {
          cy.getElementById(id).position(p);
        }
      });
      writePositions(localStorage, caseId, pos);
    } else {
      cy.batch(() => {
        for (const [id, p] of Object.entries(saved)) {
          cy.getElementById(id).position(p);
        }
      });
    }

    updateAnnotations();
  }, [
    trace,
    cardSizes,
    projection.visibleEdgeIds,
    pinnedEdgeIds,
    view.focusedNodeId,
    focused.edgeIds,
    caseId,
    getLayoutItem,
    updateAnnotations,
  ]);

  // Actions implementation
  const fit = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.fit(undefined, 40);
    updateAnnotations();
  }, [updateAnnotations]);

  const applyLayout = useCallback(
    (layoutName: LayoutName) => {
      const cy = cyRef.current;
      if (!cy) return;

      if (layoutName === "causal") {
        const items = trace.nodes.map((n) => getLayoutItem(n));
        const pos = causalPositions(items, cardSizes);
        cy.batch(() => {
          for (const [id, p] of Object.entries(pos)) {
            cy.getElementById(id).position(p);
          }
        });
        writePositions(localStorage, caseId, pos);
        updateAnnotations();
      } else if (layoutName === "cose") {
        const layout = cy.layout({
          name: "cose",
          nodeRepulsion: () => 900000,
          idealEdgeLength: () => 200,
          padding: 80,
          animate: false,
        } as cytoscape.LayoutOptions);
        layout.run();
        const curPositions: PositionMap = {};
        cy.nodes().forEach((n) => {
          curPositions[n.id()] = n.position();
        });
        const separated = separateCards(curPositions, cardSizes, new Set(), 12);
        cy.batch(() => {
          for (const [id, p] of Object.entries(separated)) {
            cy.getElementById(id).position(p);
          }
        });
        writePositions(localStorage, caseId, separated);
        updateAnnotations();
      } else if (layoutName === "concentric") {
        const seedNode = trace.nodes.find((n) => n.isSeed);
        const seedId = seedNode ? seedNode.nodeId : "";
        const layout = cy.layout({
          name: "concentric",
          concentric: (n: cytoscape.NodeSingular) =>
            n.data("isSeed") ? 3 : n.data("hop") === 1 ? 2 : 1,
          minNodeSpacing: 140,
          padding: 90,
          avoidOverlap: true,
          animate: false,
        } as cytoscape.LayoutOptions);
        layout.run();
        const curPositions: PositionMap = {};
        cy.nodes().forEach((n) => {
          curPositions[n.id()] = n.position();
        });
        const separated = separateCards(curPositions, cardSizes, new Set([seedId]), 12);
        cy.batch(() => {
          for (const [id, p] of Object.entries(separated)) {
            cy.getElementById(id).position(p);
          }
        });
        writePositions(localStorage, caseId, separated);
        updateAnnotations();
      }
    },
    [trace.nodes, cardSizes, caseId, getLayoutItem, updateAnnotations]
  );

  const moveSelectedNode = useCallback(
    (dx: number, dy: number) => {
      const cy = cyRef.current;
      if (!cy || view.selection?.kind !== "node") return;
      const nodeId = view.selection.id;
      const cyNode = cy.getElementById(nodeId);
      if (!cyNode || cyNode.length === 0) return;

      const p = cyNode.position();
      const newPos = { x: p.x + dx, y: p.y + dy };
      cyNode.position(newPos);

      const allPos: PositionMap = {};
      cy.nodes().forEach((n) => {
        allPos[n.id()] = n.position();
      });
      allPos[nodeId] = newPos;
      writePositions(localStorage, caseId, allPos);
      updateAnnotations();
    },
    [view.selection, caseId, updateAnnotations]
  );

  useEffect(() => {
    if (actionsRef) {
      actionsRef.current = {
        fit,
        applyLayout,
        moveSelectedNode,
      };
    }
  }, [actionsRef, fit, applyLayout, moveSelectedNode]);

  return (
    <div className="forensic-canvas-root" data-testid="forensic-canvas-root">
      <div className="forensic-canvas-cy" ref={containerRef} data-testid="cy-container" />
      <div className="forensic-canvas-annotations" data-testid="annotations-layer">
        <LeaderLines
          annotations={renderedEdgeAnnotations.map((r) => r.annotation)}
        />
        {renderedNodes.map(({ node, center, size }) => {
          const isSelected =
            view.selection?.kind === "node" && view.selection.id === node.nodeId;
          const isDimmed =
            view.focusedNodeId !== null && !focused.nodeIds.has(node.nodeId);
          const hiddenFlow = projection.amountHiddenByNode.get(node.nodeId);

          return (
            <NodeCardAnnotation
              key={node.nodeId}
              node={node}
              center={center}
              size={size}
              isDimmed={isDimmed}
              isSelected={isSelected}
              hiddenFlow={hiddenFlow}
              onHiddenFlow={onHiddenFlow}
            />
          );
        })}
        {renderedEdgeAnnotations.map(({ annotation, label, isPinned, edgeId }) => {
          const isSelected =
            view.selection?.kind === "edge" && view.selection.id === edgeId;
          const isDimmed =
            view.focusedNodeId !== null && !focused.edgeIds.has(edgeId);

          return (
            <EdgeAnnotationView
              key={edgeId}
              annotation={annotation}
              label={label}
              isPinned={isPinned}
              isSelected={isSelected}
              isDimmed={isDimmed}
              onClick={(id) => {
                onSelectionRef.current({ kind: "edge", id });
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
