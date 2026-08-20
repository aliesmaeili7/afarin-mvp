import type { CropRect } from "@/types/domain";

export const FULL_CROP: CropRect = { x: 0, y: 0, width: 1, height: 1 };
export const MIN_CROP_SIDE = 0.12;

export function clampCrop(rect: CropRect): CropRect {
  const width = Math.min(1, Math.max(MIN_CROP_SIDE, rect.width));
  const height = Math.min(1, Math.max(MIN_CROP_SIDE, rect.height));
  const x = Math.min(1 - width, Math.max(0, rect.x));
  const y = Math.min(1 - height, Math.max(0, rect.y));
  return { x, y, width, height };
}

export function moveCrop(rect: CropRect, dx: number, dy: number): CropRect {
  return clampCrop({ ...rect, x: rect.x + dx, y: rect.y + dy });
}

export type CropHandle = "move" | "nw" | "ne" | "sw" | "se";

export function resizeCrop(
  rect: CropRect,
  handle: CropHandle,
  dx: number,
  dy: number,
): CropRect {
  if (handle === "move") return moveCrop(rect, dx, dy);
  let { x, y, width, height } = rect;
  if (handle.includes("w")) {
    const nextX = Math.min(x + width - MIN_CROP_SIDE, Math.max(0, x + dx));
    width += x - nextX;
    x = nextX;
  }
  if (handle.includes("e")) {
    width = Math.min(1 - x, Math.max(MIN_CROP_SIDE, width + dx));
  }
  if (handle.includes("n")) {
    const nextY = Math.min(y + height - MIN_CROP_SIDE, Math.max(0, y + dy));
    height += y - nextY;
    y = nextY;
  }
  if (handle.includes("s")) {
    height = Math.min(1 - y, Math.max(MIN_CROP_SIDE, height + dy));
  }
  return clampCrop({ x, y, width, height });
}
