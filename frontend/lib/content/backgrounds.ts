import type { VisualStyle } from "@/types/domain";

/**
 * Campaign backgrounds.
 *
 * Phase 1 renders these purely with CSS/SVG in the browser — they stand in for
 * the AI-generated environment of spec §14 Step B. Crucially they contain no
 * text, so the Persian headline is always composed by our own layer (§5.6).
 * When Phase 4 produces real backgrounds, an asset simply gains a
 * `storage_path` and the renderer uses the image instead of `css`.
 */
export type BackgroundMotif =
  | "glow"
  | "grain"
  | "arch"
  | "blobs"
  | "grid"
  | "rays";

export interface BackgroundDefinition {
  id: string;
  style: VisualStyle;
  css: string;
  motif: BackgroundMotif;
  /** Colour of the soft pedestal the product sits on. */
  stage_color: string;
  text_color: string;
  muted_text_color: string;
  accent_color: string;
  cta_bg: string;
  cta_text: string;
}

export const BACKGROUNDS: readonly BackgroundDefinition[] = [
  {
    id: "luxury_night",
    style: "luxury",
    css: "radial-gradient(120% 85% at 68% 12%, #453a5f 0%, #241d33 48%, #0f0b16 100%)",
    motif: "glow",
    stage_color: "rgba(233, 180, 76, 0.16)",
    text_color: "#f6f1e6",
    muted_text_color: "rgba(246, 241, 230, 0.72)",
    accent_color: "#e9b44c",
    cta_bg: "#e9b44c",
    cta_text: "#1a1424",
  },
  {
    id: "luxury_velvet",
    style: "luxury",
    css: "linear-gradient(155deg, #2b1435 0%, #431f45 45%, #180d1f 100%)",
    motif: "rays",
    stage_color: "rgba(255, 214, 165, 0.14)",
    text_color: "#fbf3ea",
    muted_text_color: "rgba(251, 243, 234, 0.7)",
    accent_color: "#f0c987",
    cta_bg: "#f0c987",
    cta_text: "#2b1435",
  },
  {
    id: "minimal_sand",
    style: "minimal",
    css: "linear-gradient(165deg, #faf8f5 0%, #efe9e2 55%, #e3dad0 100%)",
    motif: "grain",
    stage_color: "rgba(120, 100, 80, 0.1)",
    text_color: "#26211b",
    muted_text_color: "rgba(38, 33, 27, 0.62)",
    accent_color: "#a9784f",
    cta_bg: "#26211b",
    cta_text: "#faf8f5",
  },
  {
    id: "minimal_paper",
    style: "minimal",
    css: "linear-gradient(180deg, #ffffff 0%, #f4f4f2 60%, #e9e9e6 100%)",
    motif: "grid",
    stage_color: "rgba(30, 30, 30, 0.07)",
    text_color: "#1c1c1c",
    muted_text_color: "rgba(28, 28, 28, 0.6)",
    accent_color: "#7c3aed",
    cta_bg: "#1c1c1c",
    cta_text: "#ffffff",
  },
  {
    id: "friendly_peach",
    style: "friendly",
    css: "radial-gradient(110% 80% at 22% 18%, #ffe3d2 0%, #ffc0a8 48%, #f79a80 100%)",
    motif: "blobs",
    stage_color: "rgba(255, 255, 255, 0.4)",
    text_color: "#4d1d12",
    muted_text_color: "rgba(77, 29, 18, 0.7)",
    accent_color: "#e8503f",
    cta_bg: "#4d1d12",
    cta_text: "#ffe9e0",
  },
  {
    id: "friendly_cream",
    style: "friendly",
    css: "linear-gradient(150deg, #fff6e9 0%, #ffe2c4 55%, #ffcfae 100%)",
    motif: "glow",
    stage_color: "rgba(255, 255, 255, 0.5)",
    text_color: "#5a3018",
    muted_text_color: "rgba(90, 48, 24, 0.68)",
    accent_color: "#e07a3f",
    cta_bg: "#e07a3f",
    cta_text: "#fff8f1",
  },
  {
    id: "bold_pop",
    style: "bold",
    css: "linear-gradient(135deg, #6d28d9 0%, #c026d3 48%, #fb7263 100%)",
    motif: "blobs",
    stage_color: "rgba(255, 255, 255, 0.22)",
    text_color: "#ffffff",
    muted_text_color: "rgba(255, 255, 255, 0.82)",
    accent_color: "#ffe066",
    cta_bg: "#ffffff",
    cta_text: "#6d28d9",
  },
  {
    id: "bold_electric",
    style: "bold",
    css: "radial-gradient(100% 90% at 80% 10%, #22d3ee 0%, #6366f1 42%, #a21caf 100%)",
    motif: "rays",
    stage_color: "rgba(255, 255, 255, 0.2)",
    text_color: "#ffffff",
    muted_text_color: "rgba(255, 255, 255, 0.8)",
    accent_color: "#fde047",
    cta_bg: "#fde047",
    cta_text: "#3b0764",
  },
  {
    id: "persian_emerald",
    style: "persian_traditional",
    css: "radial-gradient(120% 95% at 50% 0%, #2f6259 0%, #1e443d 52%, #122b27 100%)",
    motif: "arch",
    stage_color: "rgba(233, 196, 106, 0.16)",
    text_color: "#f5e7c8",
    muted_text_color: "rgba(245, 231, 200, 0.72)",
    accent_color: "#e9c46a",
    cta_bg: "#e9c46a",
    cta_text: "#122b27",
  },
  {
    id: "persian_saffron",
    style: "persian_traditional",
    css: "linear-gradient(160deg, #7a2e1e 0%, #a1442a 45%, #5c1f14 100%)",
    motif: "arch",
    stage_color: "rgba(255, 214, 150, 0.18)",
    text_color: "#ffeccd",
    muted_text_color: "rgba(255, 236, 205, 0.72)",
    accent_color: "#f2c14e",
    cta_bg: "#f2c14e",
    cta_text: "#5c1f14",
  },
  {
    id: "modern_ice",
    style: "modern",
    css: "linear-gradient(150deg, #f3f6ff 0%, #dde5ff 48%, #c3d0fb 100%)",
    motif: "grid",
    stage_color: "rgba(46, 60, 120, 0.12)",
    text_color: "#1b2450",
    muted_text_color: "rgba(27, 36, 80, 0.66)",
    accent_color: "#4f46e5",
    cta_bg: "#1b2450",
    cta_text: "#f3f6ff",
  },
  {
    id: "modern_slate",
    style: "modern",
    css: "linear-gradient(165deg, #24304a 0%, #16203a 55%, #0d1424 100%)",
    motif: "glow",
    stage_color: "rgba(148, 187, 255, 0.16)",
    text_color: "#eef3ff",
    muted_text_color: "rgba(238, 243, 255, 0.7)",
    accent_color: "#7dd3fc",
    cta_bg: "#7dd3fc",
    cta_text: "#0d1424",
  },
];

const BY_ID = new Map(BACKGROUNDS.map((background) => [background.id, background]));

export function getBackground(id: string): BackgroundDefinition {
  return BY_ID.get(id) ?? BACKGROUNDS[0];
}

export function backgroundsForStyle(
  style: VisualStyle,
): readonly BackgroundDefinition[] {
  const matches = BACKGROUNDS.filter((background) => background.style === style);
  return matches.length > 0 ? matches : BACKGROUNDS;
}
