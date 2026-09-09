import { describe, expect, it } from "vitest";
import {
  causalPositions,
  LayoutItem,
  placeEdgeAnnotations,
  readPositions,
  separateCards,
  writePositions,
} from "./geometry";

describe("canvas geometry", () => {
  it("computes causal layout positions with column rules and dynamic spacing", () => {
    const items: LayoutItem[] = [
      { id: "mule1", kind: "node", column: 0 },
      { id: "mule2", kind: "node", column: 0 },
      { id: "hub", kind: "node", column: 1 },
      { id: "shell", kind: "node", column: 2 },
      { id: "atm", kind: "node", column: 3 },
    ];
    const sizes = new Map([
      ["mule1", { width: 170, height: 52 }],
      ["mule2", { width: 170, height: 52 }],
      ["hub", { width: 220, height: 60 }],
      ["shell", { width: 350, height: 70 }], // wide card
      ["atm", { width: 170, height: 52 }],
    ]);

    const positions = causalPositions(items, sizes);

    // Column 0 items sorted by ID
    expect(positions["mule1"].x).toBe(120);
    expect(positions["mule2"].x).toBe(120);
    expect(positions["mule1"].y).toBeLessThan(positions["mule2"].y);

    // Column 1 (hub) X is separated
    expect(positions["hub"].x).toBeGreaterThan(120);

    // Column 2 (shell) X is pushed right because shell is 350px wide
    expect(positions["shell"].x).toBeGreaterThan(positions["hub"].x + 200);

    // Column 3 (atm) X is to the right of shell
    expect(positions["atm"].x).toBeGreaterThan(positions["shell"].x + 200);
  });

  it("separates overlapping cards deterministically downward", () => {
    // Two cards overlapping at same (100, 100)
    const positions = {
      cardA: { x: 100, y: 100 },
      cardB: { x: 100, y: 100 },
    };
    const sizes = new Map([
      ["cardA", { width: 170, height: 52 }],
      ["cardB", { width: 170, height: 52 }],
    ]);
    const fixed = new Set(["cardA"]);
    const separated = separateCards(positions, sizes, fixed, 12);

    // cardA remains fixed at 100, 100
    expect(separated["cardA"]).toEqual({ x: 100, y: 100 });

    // cardB moved down so top >= bottom of cardA + clearance (12)
    // cardA bottom = 100 + 26 = 126. cardB top = y - 26.
    // cardB y - 26 >= 126 + 12 => cardB y >= 164
    expect(separated["cardB"].x).toBe(100);
    expect(separated["cardB"].y).toBeGreaterThanOrEqual(164);
  });

  it("places edge annotations without collision and falls back to gutter if crowded", () => {
    const occupied = [
      { x: 100, y: 100, width: 170, height: 52 },
    ];
    const candidates = [
      {
        edgeId: "e1",
        anchor: { x: 300, y: 100 },
        angleDegrees: 0,
        textWidth: 80,
        textHeight: 24,
      },
    ];

    const placed = placeEdgeAnnotations(candidates, occupied, 12);
    expect(placed.length).toBe(1);
    expect(placed[0].displaced).toBe(false);
    expect(placed[0].center.x).toBeCloseTo(300);

    // Crowded scenario: occupied rect blocks the midpoint and all nearby normal offsets
    const blockAllOccupied = Array.from({ length: 45 }).map((_, i) => ({
      x: 300,
      y: 100 + (i - 22) * 24,
      width: 100,
      height: 24,
    }));
    const placedGutter = placeEdgeAnnotations(candidates, blockAllOccupied, 12);
    expect(placedGutter.length).toBe(1);
    expect(placedGutter[0].displaced).toBe(true);
    // Placed in right-side gutter
    expect(placedGutter[0].center.x).toBeGreaterThan(350);
  });

  it("safely reads and writes position maps to storage", () => {
    const storageMock: Record<string, string> = {};
    const storage: Storage = {
      getItem: (key: string) => storageMock[key] ?? null,
      setItem: (key: string, value: string) => {
        storageMock[key] = value;
      },
      removeItem: (key: string) => {
        delete storageMock[key];
      },
      clear: () => {
        for (const k of Object.keys(storageMock)) delete storageMock[k];
      },
      key: (index: number) => Object.keys(storageMock)[index] ?? null,
      length: Object.keys(storageMock).length,
    };

    // Missing key returns empty map
    expect(readPositions(storage, "case1")).toEqual({});

    // Write positions
    const pos = { node1: { x: 120, y: 150 }, node2: { x: 340, y: 200 } };
    const success = writePositions(storage, "case1", pos);
    expect(success).toBe(true);

    // Read back
    expect(readPositions(storage, "case1")).toEqual(pos);

    // Corrupt JSON returns empty map without throwing
    storage.setItem("graph_pos_case1", "{invalid json");
    expect(readPositions(storage, "case1")).toEqual({});

    // Invalid coordinates (NaN, non-numbers) filtered out
    storage.setItem("graph_pos_case1", JSON.stringify({ valid: { x: 10, y: 20 }, bad: { x: "abc", y: null } }));
    expect(readPositions(storage, "case1")).toEqual({ valid: { x: 10, y: 20 } });
  });
});
