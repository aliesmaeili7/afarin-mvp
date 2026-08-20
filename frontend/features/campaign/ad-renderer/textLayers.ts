import type {
  AssetRenderSpec,
  TextLayer,
  TextLayerAlign,
  TextLayerBackground,
  TextLayerRole,
  TextLayerWeight,
} from "@/types/domain";
import { getBackground } from "@/lib/content/backgrounds";
import { AD_FONT_IDS, DEFAULT_FONT_ID } from "./fonts";
import { getTemplate, type AdTemplate } from "./templates";

export const MAX_TEXT_LAYERS = 10;
export const MAX_LAYER_TEXT_LENGTH = 200;
export const MIN_VISIBLE_FRACTION = 0.3;
export const EDITOR_CHROME_ATTR = "data-editor-chrome";

export const TEXT_LAYER_ROLES: readonly TextLayerRole[] = [
  "headline",
  "subheadline",
  "cta",
  "price",
  "brand",
  "slide_label",
  "custom",
];

export const ROLE_SPEC_KEYS = {
  headline: "headline_fa",
  subheadline: "subheadline_fa",
  cta: "cta_fa",
  price: "price_text",
  brand: "brand_name",
  slide_label: "slide_label_fa",
} as const;

export type RoleContentKey = (typeof ROLE_SPEC_KEYS)[keyof typeof ROLE_SPEC_KEYS];

const HEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

export function hasPersistedTextLayers(spec: AssetRenderSpec): boolean {
  return Array.isArray(spec.text_layers);
}

/** Layers to draw: persisted custom layout, otherwise null so AdCanvas stays on flex. */
export function persistedTextLayers(spec: AssetRenderSpec): TextLayer[] | null {
  return Array.isArray(spec.text_layers) ? spec.text_layers : null;
}

export function clamp01(value: number, min = 0, max = 1): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

export function clampLayer(layer: TextLayer): TextLayer {
  const width = clamp01(layer.width, 0.12, 1);
  const visible = width * MIN_VISIBLE_FRACTION;
  const fontSize = clamp01(layer.font_size, 0.024, 0.22);
  return {
    ...layer,
    text: layer.text.slice(0, MAX_LAYER_TEXT_LENGTH),
    x: clamp01(layer.x, visible - width, 1 - visible),
    y: clamp01(layer.y, -0.15, 0.92),
    width,
    font_size: fontSize,
    opacity: clamp01(layer.opacity, 0.15, 1),
    background_opacity: clamp01(layer.background_opacity, 0, 1),
    font_weight: layer.font_weight === 700 ? 700 : 400,
  };
}

export function isAllowedFont(id: string): boolean {
  return AD_FONT_IDS.includes(id);
}

export function isHexColor(value: string): boolean {
  return HEX.test(value);
}

function asRole(value: unknown): TextLayerRole | null {
  return TEXT_LAYER_ROLES.includes(value as TextLayerRole)
    ? (value as TextLayerRole)
    : null;
}

function asAlign(value: unknown): TextLayerAlign {
  if (value === "left" || value === "center" || value === "right") return value;
  return "center";
}

function asBackground(value: unknown): TextLayerBackground {
  if (value === "pill" || value === "rect" || value === "none") return value;
  return "none";
}

function asWeight(value: unknown): TextLayerWeight {
  return Number(value) === 700 ? 700 : 400;
}

export function parseTextLayer(raw: unknown): TextLayer | null {
  if (!raw || typeof raw !== "object") return null;
  const row = raw as Record<string, unknown>;
  const id = typeof row.id === "string" ? row.id.trim() : "";
  const role = asRole(row.role);
  const text = typeof row.text === "string" ? row.text : "";
  if (!id || id.length > 64 || !role) return null;
  const fontFamily =
    typeof row.font_family === "string" && isAllowedFont(row.font_family)
      ? row.font_family
      : DEFAULT_FONT_ID;
  const color = typeof row.color === "string" && isHexColor(row.color) ? row.color : "#ffffff";
  const backgroundColor =
    typeof row.background_color === "string" && isHexColor(row.background_color)
      ? row.background_color
      : null;
  return clampLayer({
    id,
    role,
    text: text.slice(0, MAX_LAYER_TEXT_LENGTH),
    x: Number(row.x),
    y: Number(row.y),
    width: Number(row.width),
    font_family: fontFamily,
    font_size: Number(row.font_size),
    font_weight: asWeight(row.font_weight),
    color,
    text_align: asAlign(row.text_align),
    opacity: Number(row.opacity),
    background: asBackground(row.background),
    background_color: backgroundColor,
    background_opacity: Number(row.background_opacity),
    shadow: Boolean(row.shadow),
  });
}

export class TextLayerValidationError extends Error {
  constructor(readonly code: "too_many" | "invalid") {
    super(code);
    this.name = "TextLayerValidationError";
  }
}

export function parseTextLayers(raw: unknown): TextLayer[] {
  if (!Array.isArray(raw)) {
    throw new TextLayerValidationError("invalid");
  }
  if (raw.length > MAX_TEXT_LAYERS) {
    throw new TextLayerValidationError("too_many");
  }
  if (raw.length === 0) {
    throw new TextLayerValidationError("invalid");
  }
  const layers: TextLayer[] = [];
  const ids = new Set<string>();
  const seenRoles = new Set<TextLayerRole>();
  for (const item of raw) {
    const layer = parseTextLayer(item);
    if (!layer) throw new TextLayerValidationError("invalid");
    if (ids.has(layer.id)) throw new TextLayerValidationError("invalid");
    if (layer.role !== "custom") {
      if (seenRoles.has(layer.role)) throw new TextLayerValidationError("invalid");
      seenRoles.add(layer.role);
    }
    ids.add(layer.id);
    layers.push(layer);
  }
  return layers;
}

export function specWithLayers(
  spec: AssetRenderSpec,
  layers: TextLayer[] | null,
): AssetRenderSpec {
  if (layers === null) {
    const next = { ...spec };
    delete next.text_layers;
    return next;
  }
  return { ...spec, text_layers: layers };
}

export function syncContentFieldsFromLayers(
  spec: AssetRenderSpec,
  layers: TextLayer[],
): AssetRenderSpec {
  const next = { ...spec };
  for (const layer of layers) {
    const trimmed = layer.text.trim();
    if (layer.role === "headline") next.headline_fa = trimmed || layer.text;
    if (layer.role === "subheadline") next.subheadline_fa = trimmed || null;
    if (layer.role === "cta") next.cta_fa = trimmed || null;
    if (layer.role === "price") next.price_text = trimmed || null;
    if (layer.role === "brand") next.brand_name = trimmed || null;
    if (layer.role === "slide_label") next.slide_label_fa = trimmed || null;
  }
  return next;
}

export function applyRoleText(
  layers: TextLayer[],
  role: Exclude<TextLayerRole, "custom">,
  text: string,
): TextLayer[] {
  return layers.map((layer) => (layer.role === role ? { ...layer, text } : layer));
}

function newId(role: TextLayerRole): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${role}-${Math.random().toString(36).slice(2, 10)}`;
}

function layer(partial: Omit<TextLayer, "id"> & { id?: string }): TextLayer {
  return clampLayer({
    id: partial.id ?? newId(partial.role),
    ...partial,
  });
}

/**
 * Absolute layout that approximates the current flex templates so the editor
 * opens with type roughly where AdCanvas already puts it.
 */
export function defaultTextLayers(spec: AssetRenderSpec): TextLayer[] {
  const template = getTemplate(spec.template_id);
  const background = getBackground(spec.background_id);
  const pad = template.padding / 100;
  const align: TextLayerAlign = template.align === "center" ? "center" : "right";
  const color = background.text_color;
  const muted = rgbToHex(background.muted_text_color) ?? color;
  const layers: TextLayer[] = [];

  const topY = pad * 0.9;
  const metaWidth = 0.38;
  if (spec.brand_name) {
    layers.push(
      layer({
        id: "role-brand",
        role: "brand",
        text: spec.brand_name,
        x: 1 - pad - metaWidth,
        y: topY,
        width: metaWidth,
        font_family: DEFAULT_FONT_ID,
        font_size: template.meta_size / 100,
        font_weight: 700,
        color,
        text_align: "right",
        opacity: 1,
        background: "none",
        background_color: null,
        background_opacity: 0.55,
        shadow: true,
      }),
    );
  }

  if (spec.slide_label_fa) {
    layers.push(
      layer({
        id: "role-slide_label",
        role: "slide_label",
        text: spec.slide_label_fa,
        x: pad,
        y: topY,
        width: 0.18,
        font_family: DEFAULT_FONT_ID,
        font_size: template.meta_size / 100,
        font_weight: 400,
        color: muted,
        text_align: "center",
        opacity: 1,
        background: "pill",
        background_color: "#ffffff",
        background_opacity: 0.14,
        shadow: false,
      }),
    );
  }

  if (spec.price_text) {
    const priceX = spec.slide_label_fa ? pad + 0.2 : pad;
    layers.push(
      layer({
        id: "role-price",
        role: "price",
        text: spec.price_text,
        x: priceX,
        y: topY,
        width: 0.34,
        font_family: DEFAULT_FONT_ID,
        font_size: template.meta_size / 100,
        font_weight: 700,
        color: background.cta_text,
        text_align: "center",
        opacity: 1,
        background: "pill",
        background_color: background.accent_color,
        background_opacity: 1,
        shadow: false,
      }),
    );
  }

  const body = bodyBand(template);
  if (spec.headline_fa) {
    layers.push(
      layer({
        id: "role-headline",
        role: "headline",
        text: spec.headline_fa,
        x: pad,
        y: body.headlineY,
        width: 1 - pad * 2,
        font_family: DEFAULT_FONT_ID,
        font_size: template.headline_size / 100,
        font_weight: 700,
        color,
        text_align: align,
        opacity: 1,
        background: "none",
        background_color: null,
        background_opacity: 0.55,
        shadow: true,
      }),
    );
  }

  if (spec.subheadline_fa) {
    layers.push(
      layer({
        id: "role-subheadline",
        role: "subheadline",
        text: spec.subheadline_fa,
        x: pad,
        y: body.subY,
        width: 1 - pad * 2,
        font_family: DEFAULT_FONT_ID,
        font_size: template.subheadline_size / 100,
        font_weight: 400,
        color: muted,
        text_align: align,
        opacity: 1,
        background: "none",
        background_color: null,
        background_opacity: 0.55,
        shadow: true,
      }),
    );
  }

  if (template.show_cta && spec.cta_fa) {
    layers.push(
      layer({
        id: "role-cta",
        role: "cta",
        text: spec.cta_fa,
        x: align === "center" ? 0.22 : pad,
        y: body.ctaY,
        width: align === "center" ? 0.56 : 0.62,
        font_family: DEFAULT_FONT_ID,
        font_size: template.cta_size / 100,
        font_weight: 700,
        color: background.cta_text,
        text_align: "center",
        opacity: 1,
        background: "pill",
        background_color: background.cta_bg,
        background_opacity: 1,
        shadow: false,
      }),
    );
  }

  return layers.length > 0
    ? layers
    : [
        layer({
          id: "role-headline",
          role: "headline",
          text: spec.headline_fa || "تیتر تبلیغ",
          x: pad,
          y: 0.72,
          width: 1 - pad * 2,
          font_family: DEFAULT_FONT_ID,
          font_size: template.headline_size / 100,
          font_weight: 700,
          color,
          text_align: align,
          opacity: 1,
          background: "none",
          background_color: null,
          background_opacity: 0.55,
          shadow: true,
        }),
      ];
}

function bodyBand(template: AdTemplate): {
  headlineY: number;
  subY: number;
  ctaY: number;
} {
  if (template.order === "headline_first") {
    return { headlineY: 0.12, subY: 0.28, ctaY: 0.86 };
  }
  if (template.order === "statement") {
    return { headlineY: 0.58, subY: 0.72, ctaY: 0.84 };
  }
  return { headlineY: 0.7, subY: 0.82, ctaY: 0.9 };
}

export function newCustomLayer(spec: AssetRenderSpec): TextLayer {
  const background = getBackground(spec.background_id);
  return layer({
    role: "custom",
    text: "متن شما",
    x: 0.1,
    y: 0.4,
    width: 0.8,
    font_family: DEFAULT_FONT_ID,
    font_size: 0.06,
    font_weight: 700,
    color: background.text_color,
    text_align: "center",
    opacity: 1,
    background: "none",
    background_color: null,
    background_opacity: 0.55,
    shadow: true,
  });
}

export function hydrateEditorLayers(spec: AssetRenderSpec): TextLayer[] {
  if (Array.isArray(spec.text_layers) && spec.text_layers.length > 0) {
    return spec.text_layers.map(clampLayer);
  }
  return defaultTextLayers(spec);
}

export function stageTouchAction(interacting: boolean): "none" | "manipulation" {
  return interacting ? "none" : "manipulation";
}

/** rgba()/hex → #rrggbb when possible so layers persist as hex. */
export function rgbToHex(value: string): string | null {
  if (isHexColor(value)) {
    if (value.length === 4) {
      const r = value[1];
      const g = value[2];
      const b = value[3];
      return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
    }
    return value.toLowerCase();
  }
  const match = value.match(
    /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i,
  );
  if (!match) return null;
  const hex = (n: number) => n.toString(16).padStart(2, "0");
  return `#${hex(Number(match[1]))}${hex(Number(match[2]))}${hex(Number(match[3]))}`;
}
