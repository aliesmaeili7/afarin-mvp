import { describe, expect, it } from "vitest";
import { FULL_CROP, clampCrop, moveCrop, resizeCrop } from "./cropMath";

describe("cropMath", () => {
  it("keeps a full-frame crop inside the image", () => {
    expect(clampCrop(FULL_CROP)).toEqual(FULL_CROP);
  });

  it("moves a crop without leaving the frame", () => {
    const moved = moveCrop({ x: 0.2, y: 0.2, width: 0.4, height: 0.4 }, 0.9, -0.5);
    expect(moved.x).toBeCloseTo(0.6);
    expect(moved.y).toBe(0);
    expect(moved.width).toBeCloseTo(0.4);
  });

  it("resizes from the south-east handle", () => {
    const next = resizeCrop(
      { x: 0.1, y: 0.1, width: 0.4, height: 0.4 },
      "se",
      0.2,
      0.1,
    );
    expect(next.width).toBeCloseTo(0.6);
    expect(next.height).toBeCloseTo(0.5);
  });
});
