import "@testing-library/jest-dom/vitest";

if (typeof window !== "undefined") {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.ResizeObserver = window.ResizeObserver || ResizeObserverMock;
  globalThis.ResizeObserver = globalThis.ResizeObserver || ResizeObserverMock;

  if (typeof HTMLCanvasElement !== "undefined") {
    HTMLCanvasElement.prototype.getContext = ((contextId: string) => {
      if (contextId === "2d") {
        return {
          measureText: (text: string) => ({ width: text.length * 8 }),
          font: "",
        } as unknown as CanvasRenderingContext2D;
      }
      return null;
    }) as unknown as typeof HTMLCanvasElement.prototype.getContext;
  }
}
