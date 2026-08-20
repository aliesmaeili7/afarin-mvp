import { describe, expect, it } from "vitest";
import {
  clampLayer,
  defaultTextLayers,
  EDITOR_CHROME_ATTR,
  hydrateEditorLayers,
  MAX_TEXT_LAYERS,
  parseTextLayers,
  stageTouchAction,
  TextLayerValidationError,
} from "./textLayers";
import { textLayerBoxStyle, textLayerFillStyle } from "./TextLayerView";
import type { AssetRenderSpec, TextLayer } from "@/types/domain";

function spec(overrides: Partial<AssetRenderSpec> = {}): AssetRenderSpec {
  return {
    template_id: "feed_classic",
    background_id: "luxury_night",
    headline_fa: "آرام و جسور",
    subheadline_fa: "برای روزهای بلند",
    cta_fa: "سفارش بده",
    price_text: "۳۹۹ هزار تومان",
    brand_name: "سحند",
    product_image_path: null,
    ...overrides,
  };
}

function layer(overrides: Partial<TextLayer> = {}): TextLayer {
  return {
    id: "role-headline",
    role: "headline",
    text: "آرام و جسور",
    x: 0.1,
    y: 0.7,
    width: 0.8,
    font_family: "vazirmatn",
    font_size: 0.076,
    font_weight: 700,
    color: "#ffffff",
    text_align: "center",
    opacity: 1,
    background: "none",
    background_color: null,
    background_opacity: 0.55,
    shadow: true,
    ...overrides,
  };
}

describe("defaultTextLayers", () => {
  it("creates role layers that follow the feed template sizes", () => {
    const layers = defaultTextLayers(spec());
    const roles = layers.map((item) => item.role);
    expect(roles).toContain("headline");
    expect(roles).toContain("subheadline");
    expect(roles).toContain("cta");
    expect(roles).toContain("price");
    expect(roles).toContain("brand");
    const headline = layers.find((item) => item.role === "headline");
    expect(headline?.font_size).toBeCloseTo(0.076);
    expect(headline?.text_align).toBe("center");
  });

  it("places hook copy near the top for carousel_hook", () => {
    const layers = defaultTextLayers(
      spec({ template_id: "carousel_hook", slide_label_fa: "۱" }),
    );
    const headline = layers.find((item) => item.role === "headline");
    expect(headline?.y).toBeLessThan(0.25);
    expect(layers.some((item) => item.role === "slide_label")).toBe(true);
  });

  it("uses start alignment for hook slides", () => {
    const layers = defaultTextLayers(spec({ template_id: "carousel_hook" }));
    expect(layers.find((item) => item.role === "headline")?.text_align).toBe("right");
  });
});

describe("parseTextLayers", () => {
  it("rejects more than the cap", () => {
    const raw = Array.from({ length: MAX_TEXT_LAYERS + 1 }, (_, index) =>
      layer({ id: `n-${index}`, role: "custom" }),
    );
    expect(() => parseTextLayers(raw)).toThrow(TextLayerValidationError);
    try {
      parseTextLayers(raw);
    } catch (caught) {
      expect((caught as TextLayerValidationError).code).toBe("too_many");
    }
  });

  it("hydrates persisted layers instead of defaults", () => {
    const saved = [layer({ x: 0.4 })];
    const next = hydrateEditorLayers(spec({ text_layers: saved }));
    expect(next[0]?.x).toBeCloseTo(0.4);
  });
});

describe("clampLayer", () => {
  it("keeps a dragged box partly inside the canvas", () => {
    const next = clampLayer(layer({ x: -2, y: 4, width: 0.4 }));
    expect(next.x).toBeGreaterThan(-0.4);
    expect(next.y).toBeLessThanOrEqual(0.92);
  });
});

describe("theme isolation", () => {
  it("keeps spec colors instead of semantic theme tokens", () => {
    const box = textLayerBoxStyle(
      layer({ color: "#e9b44c", background: "pill", background_color: "#17121f" }),
    );
    const fill = textLayerFillStyle(
      layer({ background: "pill", background_color: "#17121f", background_opacity: 0.7 }),
    );
    expect(box.color).toBe("#e9b44c");
    expect(JSON.stringify(box)).not.toMatch(/var\(--/);
    expect(fill?.backgroundColor).toMatch(/23,\s*18,\s*31/);
    expect(JSON.stringify(fill)).not.toMatch(/var\(--/);
  });
});

describe("editor chrome contract", () => {
  it("keeps chrome on a dedicated attribute AdCanvas does not set", () => {
    expect(EDITOR_CHROME_ATTR).toBe("data-editor-chrome");
  });

  it("disables panning only while a gesture is active", () => {
    expect(stageTouchAction(true)).toBe("none");
    expect(stageTouchAction(false)).toBe("manipulation");
  });
});
