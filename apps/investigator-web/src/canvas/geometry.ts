export type Point = { x: number; y: number };
export type Rect = { x: number; y: number; width: number; height: number };
export type PositionMap = Record<string, Point>;

export type LayoutItem = {
  id: string;
  kind: "node" | "cluster";
  column: 0 | 1 | 2 | 3;
};

export type EdgeAnnotation = {
  edgeId: string;
  center: Point;
  angleDegrees: number;
  rect: Rect;
  anchor: Point;
  displaced: boolean;
};

export function causalPositions(
  items: readonly LayoutItem[],
  sizes: ReadonlyMap<string, { width: number; height: number }>
): PositionMap {
  const colItems: Record<0 | 1 | 2 | 3, LayoutItem[]> = {
    0: [],
    1: [],
    2: [],
    3: [],
  };

  for (const item of items) {
    colItems[item.column].push(item);
  }

  // Sort each column by item ID
  for (const c of [0, 1, 2, 3] as const) {
    colItems[c].sort((a, b) => a.id.localeCompare(b.id));
  }

  // Max width per column
  const colMaxWidth: Record<0 | 1 | 2 | 3, number> = {
    0: 170,
    1: 170,
    2: 170,
    3: 170,
  };
  for (const c of [0, 1, 2, 3] as const) {
    let maxW = 170;
    for (const item of colItems[c]) {
      const s = sizes.get(item.id);
      if (s && s.width > maxW) maxW = s.width;
    }
    colMaxWidth[c] = maxW;
  }

  // Column centers
  const colCenters: Record<0 | 1 | 2 | 3, number> = {
    0: 120,
    1: 430,
    2: 740,
    3: 1050,
  };
  const baselineDiffs = [310, 310, 310]; // 430-120, 740-430, 1050-740
  for (let c = 1; c <= 3; c++) {
    const prevCol = (c - 1) as 0 | 1 | 2;
    const currCol = c as 1 | 2 | 3;
    const baselineDiff = baselineDiffs[c - 1];
    const neededDiff = Math.max(
      baselineDiff,
      300,
      colMaxWidth[prevCol] / 2 + colMaxWidth[currCol] / 2 + 80
    );
    colCenters[currCol] = colCenters[prevCol] + neededDiff;
  }

  const positions: PositionMap = {};
  for (const c of [0, 1, 2, 3] as const) {
    let currentY = 100;
    let prevHeight = 0;
    for (let i = 0; i < colItems[c].length; i++) {
      const item = colItems[c][i];
      const s = sizes.get(item.id) ?? { width: 170, height: 52 };
      if (i > 0) {
        currentY += prevHeight / 2 + s.height / 2 + 40;
      }
      positions[item.id] = { x: colCenters[c], y: currentY };
      prevHeight = s.height;
    }
  }

  return positions;
}

function rectsOverlap(
  r1: Rect,
  r2: Rect,
  clearance: number
): boolean {
  const xOverlap =
    Math.abs(r1.x - r2.x) < (r1.width + r2.width) / 2 + clearance;
  const yOverlap =
    Math.abs(r1.y - r2.y) < (r1.height + r2.height) / 2 + clearance;
  return xOverlap && yOverlap;
}

export function separateCards(
  positions: PositionMap,
  sizes: ReadonlyMap<string, { width: number; height: number }>,
  fixedIds: ReadonlySet<string>,
  clearance: number
): PositionMap {
  const res: PositionMap = {};
  const accepted: Rect[] = [];

  // 1. Process fixed IDs first
  for (const id of Object.keys(positions)) {
    if (fixedIds.has(id)) {
      const pos = positions[id];
      const s = sizes.get(id) ?? { width: 170, height: 52 };
      const rect = { x: pos.x, y: pos.y, width: s.width, height: s.height };
      res[id] = { x: pos.x, y: pos.y };
      accepted.push(rect);
    }
  }

  // 2. Process remaining IDs in deterministic alphabetical order
  const remainingIds = Object.keys(positions)
    .filter((id) => !fixedIds.has(id))
    .sort();

  for (const id of remainingIds) {
    const pos = positions[id];
    const s = sizes.get(id) ?? { width: 170, height: 52 };
    let curY = pos.y;
    let candidateRect: Rect = {
      x: pos.x,
      y: curY,
      width: s.width,
      height: s.height,
    };

    let collided = true;
    while (collided) {
      collided = false;
      for (const r of accepted) {
        if (rectsOverlap(candidateRect, r, clearance)) {
          collided = true;
          const conflictingBottom = r.y + r.height / 2;
          curY = Math.max(curY, conflictingBottom + clearance + s.height / 2);
          candidateRect = {
            x: pos.x,
            y: curY,
            width: s.width,
            height: s.height,
          };
        }
      }
    }

    res[id] = { x: pos.x, y: curY };
    accepted.push(candidateRect);
  }

  return res;
}

export function readPositions(storage: Storage, caseId: string): PositionMap {
  try {
    const raw = storage.getItem(`graph_pos_${caseId}`);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return {};
    }
    const clean: PositionMap = {};
    for (const [k, v] of Object.entries(parsed)) {
      if (
        typeof v === "object" &&
        v !== null &&
        !Array.isArray(v) &&
        "x" in v &&
        typeof v.x === "number" &&
        Number.isFinite(v.x) &&
        "y" in v &&
        typeof v.y === "number" &&
        Number.isFinite(v.y)
      ) {
        clean[k] = { x: v.x, y: v.y };
      }
    }
    return clean;
  } catch {
    return {};
  }
}
export function writePositions(
  storage: Storage,
  caseId: string,
  positions: PositionMap
): boolean {
  try {
    storage.setItem(`graph_pos_${caseId}`, JSON.stringify(positions));
    return true;
  } catch {
    return false;
  }
}

export function placeEdgeAnnotations(
  candidates: readonly {
    edgeId: string;
    anchor: Point;
    angleDegrees: number;
    textWidth: number;
    textHeight: number;
  }[],
  occupied: readonly Rect[],
  clearance: number
): EdgeAnnotation[] {
  const allOccupied: Rect[] = [...occupied];
  const placed: EdgeAnnotation[] = [];

  // Generate normal offsets: 0, 24, -24, 48, -48, ..., 480, -480
  const offsets: number[] = [0];
  for (let step = 1; step <= 20; step++) {
    offsets.push(step * 24);
    offsets.push(-step * 24);
  }

  let gutterNextY = 100;

  for (const cand of candidates) {
    const rad = (cand.angleDegrees * Math.PI) / 180;
    // Normal vector perpendicular to tangent
    const nx = -Math.sin(rad);
    const ny = Math.cos(rad);

    const w = cand.textWidth + 24; // 12px inset padding
    const h = cand.textHeight + 12;

    // Axis-aligned bounding box of rotated rectangle
    const cosA = Math.abs(Math.cos(rad));
    const sinA = Math.abs(Math.sin(rad));
    const aabbWidth = w * cosA + h * sinA;
    const aabbHeight = w * sinA + h * cosA;

    let foundPlacement: { center: Point; rect: Rect } | null = null;

    for (const offset of offsets) {
      const cx = cand.anchor.x + offset * nx;
      const cy = cand.anchor.y + offset * ny;
      const testRect: Rect = {
        x: cx,
        y: cy,
        width: aabbWidth,
        height: aabbHeight,
      };

      let collides = false;
      for (const occ of allOccupied) {
        if (rectsOverlap(testRect, occ, clearance)) {
          collides = true;
          break;
        }
      }

      if (!collides) {
        foundPlacement = { center: { x: cx, y: cy }, rect: testRect };
        break;
      }
    }

    if (foundPlacement) {
      placed.push({
        edgeId: cand.edgeId,
        center: foundPlacement.center,
        angleDegrees: cand.angleDegrees,
        rect: foundPlacement.rect,
        anchor: cand.anchor,
        displaced: false,
      });
      allOccupied.push(foundPlacement.rect);
    } else {
      // Gutter fallback
      let maxX = 1200;
      for (const r of allOccupied) {
        const right = r.x + r.width / 2;
        if (right > maxX) maxX = right;
      }
      const gutterX = maxX + 60 + aabbWidth / 2;
      const gutterY = gutterNextY + aabbHeight / 2;
      gutterNextY += aabbHeight + clearance;

      const gutterRect: Rect = {
        x: gutterX,
        y: gutterY,
        width: aabbWidth,
        height: aabbHeight,
      };

      placed.push({
        edgeId: cand.edgeId,
        center: { x: gutterX, y: gutterY },
        angleDegrees: 0, // gutter labels are horizontal
        rect: gutterRect,
        anchor: cand.anchor,
        displaced: true,
      });
      allOccupied.push(gutterRect);
    }
  }

  return placed;
}
