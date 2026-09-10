import React, { useCallback, useEffect, useId, useMemo } from "react";
import { formatVndMillions, LayoutName, ViewState } from "./model";

export type PlaybackSpeed = 1 | 2 | 4;

export type CanvasControlsProps = {
  view: ViewState;
  timeMin: number | null;
  timeMax: number | null;
  playing: boolean;
  speed: PlaybackSpeed;
  expanding: boolean;
  canExpand: boolean;
  hiddenCount: number;
  totalLoadedEdges: number;
  isTruncated: boolean;
  unknownTimeCount: number;
  onLayout: (layout: LayoutName) => void;
  onAmount: (amountVnd: number) => void;
  onCutoff: (cutoffMs: number) => void;
  onPlay: () => void;
  onSpeed: (speed: PlaybackSpeed) => void;
  onFit: () => void;
  onExpand: () => void;
  onRestoreHidden: () => void;
  onTogglePinSelected?: () => void;
  onHideSelected?: () => void;
  onClearSelection?: () => void;
};

export const CanvasControls: React.FC<CanvasControlsProps> = ({
  view,
  timeMin,
  timeMax,
  playing,
  speed,
  expanding,
  canExpand,
  hiddenCount,
  totalLoadedEdges,
  isTruncated,
  unknownTimeCount,
  onLayout,
  onAmount,
  onCutoff,
  onPlay,
  onSpeed,
  onFit,
  onExpand,
  onRestoreHidden,
  onTogglePinSelected,
  onHideSelected,
  onClearSelection,
}) => {
  const thresholdInputId = useId();
  const timelineInputId = useId();

  // Keyboard shortcut handler
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const element = event.target instanceof Element ? event.target : null;
      const editing = element?.closest(
        "input,textarea,select,[contenteditable='true'],[role='textbox']"
      );
      if (editing || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }

      if (event.code === "Space") {
        event.preventDefault();
        onPlay();
      } else if (event.key === "f" || event.key === "F") {
        event.preventDefault();
        onFit();
      } else if (event.key === "p" || event.key === "P") {
        event.preventDefault();
        onTogglePinSelected?.();
      } else if (event.key === "1") {
        event.preventDefault();
        onLayout("causal");
      } else if (event.key === "2") {
        event.preventDefault();
        onLayout("cose");
      } else if (event.key === "3") {
        event.preventDefault();
        onLayout("concentric");
      } else if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        onHideSelected?.();
      } else if (event.key === "Escape") {
        event.preventDefault();
        onClearSelection?.();
      }
    },
    [
      onPlay,
      onFit,
      onTogglePinSelected,
      onLayout,
      onHideSelected,
      onClearSelection,
    ]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Timeline formatted string
  const formattedTime = useMemo(() => {
    if (view.cutoffMs === null) return "Chưa có dữ liệu thời gian";
    const d = new Date(view.cutoffMs);
    return isNaN(d.getTime())
      ? "Thời gian không hợp lệ"
      : d.toLocaleString("vi-VN", {
          timeZone: "Asia/Ho_Chi_Minh",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        });
  }, [view.cutoffMs]);

  const timelinePercent = useMemo(() => {
    if (timeMin === null || timeMax === null || timeMin >= timeMax || view.cutoffMs === null) {
      return 100;
    }
    const ratio = (view.cutoffMs - timeMin) / (timeMax - timeMin);
    return Math.max(0, Math.min(100, Math.round(ratio * 100)));
  }, [timeMin, timeMax, view.cutoffMs]);

  const thresholdLabel = formatVndMillions(BigInt(view.amountThresholdVnd));

  return (
    <>
      {/* Top Floating Toolbar */}
      <div
        className="canvas-toolbar"
        data-testid="canvas-toolbar"
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          background: "rgba(15, 23, 42, 0.92)",
          backdropFilter: "blur(8px)",
          border: "1px solid #334155",
          borderRadius: "8px",
          padding: "8px 14px",
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.4)",
          color: "#f8fafc",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          fontSize: "13px",
        }}
      >
        {/* Layout Buttons */}
        <div style={{ display: "flex", gap: "4px", background: "#0f172a", borderRadius: "6px", padding: "2px" }}>
          <button
            type="button"
            className="canvas-btn"
            style={{
              background: view.layout === "causal" ? "#2563eb" : "transparent",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
            }}
            onClick={() => onLayout("causal")}
            aria-pressed={view.layout === "causal"}
            title="Bố cục Nguyên nhân (Phím 1)"
          >
            Causal (1)
          </button>
          <button
            type="button"
            className="canvas-btn"
            style={{
              background: view.layout === "cose" ? "#2563eb" : "transparent",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
            }}
            onClick={() => onLayout("cose")}
            aria-pressed={view.layout === "cose"}
            title="Bố cục CoSE (Phím 2)"
          >
            CoSE (2)
          </button>
          <button
            type="button"
            className="canvas-btn"
            style={{
              background: view.layout === "concentric" ? "#2563eb" : "transparent",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
            }}
            onClick={() => onLayout("concentric")}
            aria-pressed={view.layout === "concentric"}
            title="Bố cục Đồng tâm (Phím 3)"
          >
            Concentric (3)
          </button>
        </div>

        {/* Amount Threshold Slider */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", borderLeft: "1px solid #334155", paddingLeft: "10px" }}>
          <label htmlFor={thresholdInputId} style={{ color: "#94a3b8", fontSize: "12px", whiteSpace: "nowrap" }}>
            Ngưỡng (VND):
          </label>
          <input
            id={thresholdInputId}
            type="range"
            min={0}
            max={100_000_000}
            step={1_000_000}
            value={view.amountThresholdVnd}
            onChange={(e) => onAmount(Number(e.target.value))}
            aria-valuetext={thresholdLabel}
            style={{ width: "100px", cursor: "pointer" }}
          />
          <span style={{ minWidth: "55px", fontFamily: "monospace", fontSize: "12px", color: "#38bdf8" }}>
            {thresholdLabel}
          </span>
        </div>

        {/* Fit Button */}
        <button
          type="button"
          className="canvas-btn"
          onClick={onFit}
          title="Phóng vừa khung hình (F)"
          style={{
            background: "#1e293b",
            border: "1px solid #475569",
            color: "#f8fafc",
            borderRadius: "6px",
            padding: "5px 10px",
            cursor: "pointer",
            fontSize: "12px",
          }}
        >
          Phóng vừa (F)
        </button>

        {/* Expand Hop Button */}
        <button
          type="button"
          className="canvas-btn"
          disabled={!canExpand || expanding}
          onClick={onExpand}
          title="Mở rộng Hop tiếp theo"
          style={{
            background: canExpand && !expanding ? "#1e293b" : "#0f172a",
            border: "1px solid #475569",
            color: canExpand && !expanding ? "#f8fafc" : "#64748b",
            borderRadius: "6px",
            padding: "5px 10px",
            cursor: canExpand && !expanding ? "pointer" : "not-allowed",
            fontSize: "12px",
          }}
        >
          {expanding ? "Đang mở rộng..." : "Mở rộng Hop"}
        </button>

        {/* Restore Hidden Button */}
        {hiddenCount > 0 && (
          <button
            type="button"
            className="canvas-btn"
            onClick={onRestoreHidden}
            style={{
              background: "#3b82f6",
              border: "none",
              color: "#ffffff",
              borderRadius: "6px",
              padding: "5px 10px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
            }}
          >
            Khôi phục ({hiddenCount})
          </button>
        )}

        {/* Status Indicators */}
        <div style={{ display: "flex", gap: "8px", borderLeft: "1px solid #334155", paddingLeft: "10px", color: "#94a3b8", fontSize: "11px" }}>
          <span>{totalLoadedEdges} giao dịch</span>
          {isTruncated && (
            <span style={{ color: "#f59e0b", fontWeight: 600 }}>
              Giới hạn 100 giao dịch
            </span>
          )}
          {unknownTimeCount > 0 && (
            <span style={{ color: "#f59e0b" }}>
              {unknownTimeCount} không rõ thời gian
            </span>
          )}
        </div>

        {/* Keyboard shortcut guide */}
        <details style={{ cursor: "pointer", fontSize: "11px", color: "#64748b" }}>
          <summary>Phím tắt</summary>
          <div style={{ position: "absolute", top: "100%", left: 0, marginTop: "6px", background: "#0f172a", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", width: "240px", color: "#cbd5e1" }}>
            <div><strong>Space:</strong> Phát / Tạm dừng</div>
            <div><strong>F:</strong> Phóng vừa</div>
            <div><strong>P:</strong> Ghim / Bỏ ghim SAR giao dịch</div>
            <div><strong>1, 2, 3:</strong> Chuyển bố cục</div>
            <div><strong>Del / Backspace:</strong> Ẩn nhánh</div>
            <div><strong>Esc:</strong> Bỏ chọn / Bỏ tiêu điểm</div>
          </div>
        </details>
      </div>

      {/* Bottom 64px Timeline */}
      <div
        className="canvas-timeline"
        data-testid="canvas-timeline"
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: "64px",
          background: "rgba(10, 15, 29, 0.95)",
          backdropFilter: "blur(12px)",
          borderTop: "1px solid #1e293b",
          boxSizing: "border-box",
          padding: "0 20px",
          display: "flex",
          alignItems: "center",
          gap: "16px",
          zIndex: 10,
          color: "#f8fafc",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        }}
      >
        {/* Play/Pause Button */}
        <button
          type="button"
          onClick={onPlay}
          aria-label={playing ? "Tạm dừng phát dòng tiền" : "Phát lại dòng tiền"}
          style={{
            background: "#2563eb",
            color: "#ffffff",
            border: "none",
            borderRadius: "6px",
            width: "36px",
            height: "36px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            fontSize: "16px",
            fontWeight: "bold",
          }}
        >
          {playing ? "⏸" : "▶"}
        </button>

        {/* Speed Selector */}
        <div style={{ display: "flex", gap: "2px", background: "#1e293b", borderRadius: "6px", padding: "2px" }}>
          {([1, 2, 4] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSpeed(s)}
              aria-pressed={speed === s}
              style={{
                background: speed === s ? "#3b82f6" : "transparent",
                color: "#f8fafc",
                border: "none",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {s}.0x
            </button>
          ))}
        </div>

        {/* Timeline Slider */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "2px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#94a3b8" }}>
            <span>{formattedTime}</span>
            <span>{timelinePercent}%</span>
          </div>
          <input
            id={timelineInputId}
            type="range"
            min={timeMin ?? 0}
            max={timeMax ?? 100}
            step={1}
            disabled={timeMin === null || timeMax === null || timeMin >= timeMax}
            value={view.cutoffMs ?? timeMin ?? 0}
            onChange={(e) => onCutoff(Number(e.target.value))}
            aria-valuetext={`${formattedTime} (${timelinePercent}%)`}
            style={{ width: "100%", cursor: "pointer", height: "6px" }}
          />
        </div>
      </div>
    </>
  );
};
