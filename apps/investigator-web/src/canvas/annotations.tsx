import React from "react";
import type { TraceNodeResponse } from "../api";
import type { EdgeAnnotation, Point } from "./geometry";
import type { HiddenFlow } from "./model";

let measureCanvas: HTMLCanvasElement | null = null;

function getMeasureContext(): CanvasRenderingContext2D | null {
  if (typeof document === "undefined") return null;
  if (!measureCanvas) {
    measureCanvas = document.createElement("canvas");
  }
  try {
    return measureCanvas.getContext("2d");
  } catch {
    return null;
  }
}
export function measureTextWidth(text: string, font: string): number {
  const ctx = getMeasureContext();
  if (!ctx) return text.length * 8;
  ctx.font = font;
  return ctx.measureText(text).width;
}

export function measureCardSize(
  node: TraceNodeResponse,
  hasHiddenFlow: boolean
): { width: number; height: number } {
  const titleText = node.accountHolderName ?? node.nodeId;
  const titleW = measureTextWidth(
    titleText,
    "600 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
  );

  const badgeText = node.badge ?? (node.isSeed ? "SEED / HUB" : "");
  const badgeW = badgeText
    ? measureTextWidth(
        badgeText,
        "600 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
      ) + 16
    : 0;

  const bankText = `${node.bankShortName ?? "Chưa có dữ liệu"} •••• ${
    node.accountLast4 ?? "----"
  }`;
  const bankW = measureTextWidth(
    bankText,
    "12px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
  );

  const riskText =
    node.riskScore !== null && node.riskScore !== undefined
      ? `Risk: ${node.riskScore.toFixed(2)}`
      : "Risk: —";
  const riskW = measureTextWidth(
    riskText,
    "500 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
  );

  const hiddenW = hasHiddenFlow ? 130 : 0;

  const width = Math.max(
    170,
    24 + titleW + badgeW + 16,
    24 + bankW + riskW + 16,
    24 + hiddenW
  );
  const height = Math.max(52, 24 + 18 + 16) + (hasHiddenFlow ? 28 : 0);

  return { width: Math.ceil(width), height: Math.ceil(height) };
}

export type NodeCardAnnotationProps = {
  node: TraceNodeResponse;
  center: Point;
  size: { width: number; height: number };
  isDimmed: boolean;
  isSelected: boolean;
  hiddenFlow?: HiddenFlow;
  onHiddenFlow?: (nodeId: string) => void;
  onSelectNode?: (nodeId: string) => void;
};

export const NodeCardAnnotation: React.FC<NodeCardAnnotationProps> = ({
  node,
  center,
  size,
  isDimmed,
  isSelected,
  hiddenFlow,
  onHiddenFlow,
  onSelectNode,
}) => {
  const title = node.accountHolderName ?? node.nodeId;
  const bankLine = `${node.bankShortName ?? "Chưa có dữ liệu"} •••• ${
    node.accountLast4 ?? "----"
  }`;
  const riskText =
    node.riskScore !== null && node.riskScore !== undefined
      ? `Risk: ${node.riskScore.toFixed(2)}`
      : "Risk: —";

  let riskClass = "low-risk";
  if (node.isSeed) {
    riskClass = "seed-node";
  } else if (node.riskScore !== null && node.riskScore !== undefined) {
    if (node.riskScore >= 0.85) riskClass = "high-risk";
    else if (node.riskScore >= 0.5) riskClass = "medium-risk";
  }

  const left = center.x - size.width / 2;
  const top = center.y - size.height / 2;

  return (
    <div
      className={`canvas-node-card ${riskClass} ${isDimmed ? "dimmed" : ""} ${
        isSelected ? "selected" : ""
      }`}
      data-node-id={node.nodeId}
      data-annotation-kind="node"
      style={{
        left: `${left}px`,
        top: `${top}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
        pointerEvents: "auto",
        cursor: "pointer",
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelectNode?.(node.nodeId);
      }}
    >
      <div className="canvas-card-header">
        <span className="canvas-card-title">{title}</span>
        {node.badge && (
          <span className={`canvas-card-badge badge-${node.badge}`}>
            {node.badge.replace("_", " ")}
          </span>
        )}
      </div>
      <div className="canvas-card-subline">
        <span>{bankLine}</span>
        <span className="canvas-card-risk">{riskText}</span>
      </div>
      {hiddenFlow && hiddenFlow.edgeIds.length > 0 && (
        <div className="canvas-card-hidden-row">
          <button
            type="button"
            className="canvas-hidden-flow-btn"
            onClick={(e) => {
              e.stopPropagation();
              onHiddenFlow?.(node.nodeId);
            }}
          >
            +{hiddenFlow.edgeIds.length} ẩn
          </button>
        </div>
      )}
    </div>
  );
};

export type EdgeAnnotationViewProps = {
  annotation: EdgeAnnotation;
  label: string;
  isPinned: boolean;
  isSelected: boolean;
  isDimmed: boolean;
  onClick: (edgeId: string) => void;
};

export const EdgeAnnotationView: React.FC<EdgeAnnotationViewProps> = ({
  annotation,
  label,
  isPinned,
  isSelected,
  isDimmed,
  onClick,
}) => {
  const transform = `translate(-50%, -50%) rotate(${annotation.angleDegrees}deg)`;

  return (
    <div
      className={`canvas-edge-annotation ${isPinned ? "pinned" : ""} ${
        isSelected ? "selected" : ""
      }`}
      style={{
        left: `${annotation.center.x}px`,
        top: `${annotation.center.y}px`,
        transform,
        opacity: isDimmed ? 0.2 : 1,
      }}
      data-edge-id={annotation.edgeId}
      data-annotation-kind="edge"
      onClick={(e) => {
        e.stopPropagation();
        onClick(annotation.edgeId);
      }}
    >
      {label}
    </div>
  );
};

export type LeaderLinesProps = {
  annotations: readonly EdgeAnnotation[];
};

export const LeaderLines: React.FC<LeaderLinesProps> = ({ annotations }) => {
  const displaced = annotations.filter((a) => a.displaced);
  if (displaced.length === 0) return null;

  return (
    <svg className="canvas-edge-leader" aria-hidden="true">
      {displaced.map((a) => (
        <line
          key={a.edgeId}
          x1={a.anchor.x}
          y1={a.anchor.y}
          x2={a.center.x}
          y2={a.center.y}
          stroke="#475569"
          strokeWidth="1"
          strokeDasharray="3 3"
        />
      ))}
    </svg>
  );
};
