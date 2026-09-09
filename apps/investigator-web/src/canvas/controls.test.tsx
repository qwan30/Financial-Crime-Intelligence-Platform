import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanvasControls } from "./CanvasControls";
import { initialView } from "./model";

describe("CanvasControls", () => {
  const dummyTrace = {
    nodes: [],
    edges: [],
    isTruncated: false,
    totalHops: 0,
    hopByNodeId: {},
    timeMin: "2026-09-08T08:00:00+07:00",
    timeMax: "2026-09-08T10:00:00+07:00",
    unknownTimeEdgeCount: 0,
  };

  const defaultProps = {
    view: {
      ...initialView(dummyTrace),
      cutoffMs: Date.parse("2026-09-08T09:00:00+07:00"),
    },
    timeMin: Date.parse("2026-09-08T08:00:00+07:00"),
    timeMax: Date.parse("2026-09-08T10:00:00+07:00"),
    playing: false,
    speed: 1 as const,
    expanding: false,
    canExpand: true,
    hiddenCount: 0,
    totalLoadedEdges: 10,
    isTruncated: false,
    unknownTimeCount: 0,
    onLayout: vi.fn(),
    onAmount: vi.fn(),
    onCutoff: vi.fn(),
    onPlay: vi.fn(),
    onSpeed: vi.fn(),
    onFit: vi.fn(),
    onExpand: vi.fn(),
    onRestoreHidden: vi.fn(),
    onTogglePinSelected: vi.fn(),
    onHideSelected: vi.fn(),
    onClearSelection: vi.fn(),
  };

  it("renders toolbar and timeline with local time and percentage", () => {
    render(<CanvasControls {...defaultProps} />);

    expect(screen.getByTestId("canvas-toolbar")).toBeInTheDocument();
    expect(screen.getByTestId("canvas-timeline")).toBeInTheDocument();

    // 09:00 is exactly 50% between 08:00 and 10:00
    expect(screen.getByText(/50%/)).toBeInTheDocument();
    expect(screen.getByText("10 giao dịch")).toBeInTheDocument();
  });

  it("triggers keyboard shortcuts when not editing form elements", () => {
    const onPlay = vi.fn();
    const onFit = vi.fn();
    const onLayout = vi.fn();
    const onTogglePinSelected = vi.fn();

    render(
      <CanvasControls
        {...defaultProps}
        onPlay={onPlay}
        onFit={onFit}
        onLayout={onLayout}
        onTogglePinSelected={onTogglePinSelected}
      />
    );

    // Space toggles play
    fireEvent.keyDown(window, { code: "Space" });
    expect(onPlay).toHaveBeenCalledTimes(1);

    // F fits
    fireEvent.keyDown(window, { key: "f" });
    expect(onFit).toHaveBeenCalledTimes(1);

    // P toggles pin
    fireEvent.keyDown(window, { key: "p" });
    expect(onTogglePinSelected).toHaveBeenCalledTimes(1);

    // 1, 2, 3 switch layout
    fireEvent.keyDown(window, { key: "1" });
    expect(onLayout).toHaveBeenCalledWith("causal");
    fireEvent.keyDown(window, { key: "2" });
    expect(onLayout).toHaveBeenCalledWith("cose");
    fireEvent.keyDown(window, { key: "3" });
    expect(onLayout).toHaveBeenCalledWith("concentric");
  });

  it("guards against shortcuts when user is typing in input or textarea", () => {
    const onPlay = vi.fn();
    const onFit = vi.fn();
    const onTogglePinSelected = vi.fn();

    render(
      <div>
        <input data-testid="test-input" type="text" />
        <textarea data-testid="test-textarea" />
        <CanvasControls
          {...defaultProps}
          onPlay={onPlay}
          onFit={onFit}
          onTogglePinSelected={onTogglePinSelected}
        />
      </div>
    );

    const input = screen.getByTestId("test-input");
    input.focus();

    // In input: Space, F, P must not trigger shortcuts
    fireEvent.keyDown(input, { code: "Space", key: " " });
    fireEvent.keyDown(input, { key: "f" });
    fireEvent.keyDown(input, { key: "p" });

    expect(onPlay).not.toHaveBeenCalled();
    expect(onFit).not.toHaveBeenCalled();
    expect(onTogglePinSelected).not.toHaveBeenCalled();

    const textarea = screen.getByTestId("test-textarea");
    textarea.focus();
    fireEvent.keyDown(textarea, { code: "Space", key: " " });
    fireEvent.keyDown(textarea, { key: "f" });
    expect(onPlay).not.toHaveBeenCalled();
    expect(onFit).not.toHaveBeenCalled();
  });
});
