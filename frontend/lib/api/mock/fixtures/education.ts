import type {
  BuiltinEducationalTheme,
  EducationalAgentResult,
  EducationalThemeSpec,
} from "@/types/domain";
import { buildEducationalRenderSpec } from "@/features/education/educationSpec";
import { listingTitle } from "@/features/education/educationPost";

export { buildEducationalRenderSpec };

/**
 * The Phase 1 built-in themes, mirroring
 * backend/app/content/education_themes.json.
 *
 * Themes are semantic: a palette, an illustration language, mood, lighting and
 * motifs. They are never a pasted image prompt and never a layout.
 */
export const BUILTIN_EDUCATION_THEMES: BuiltinEducationalTheme[] = [
  {
    id: "clay_playful",
    name: "خمیری و بازیگوش",
    source: "builtin",
    palette: {
      primary: ["#7c3aed", "#22d3ee"],
      secondary: ["#fde047", "#fb7185"],
      background: "#f6f1ff",
      text: "#1e1b4b",
    },
    illustration_style:
      "soft 3D clay render, rounded matte forms, gentle ambient occlusion",
    mood: "playful, tactile, inviting for children",
    lighting: "soft wraparound studio light, warm highlights",
    shape_language: "pill and blob shapes, thick rounded edges, no sharp corners",
    decorative_motifs: ["stars", "floating cubes", "dotted paths", "small flags"],
  },
  {
    id: "pastel_classroom",
    name: "کلاس پاستلی",
    source: "builtin",
    palette: {
      primary: ["#f472b6", "#60a5fa"],
      secondary: ["#a7f3d0", "#fcd34d"],
      background: "#fdf6f0",
      text: "#3f3351",
    },
    illustration_style:
      "flat pastel illustration with soft grain and light paper texture",
    mood: "calm, tidy, gentle",
    lighting: "even daylight, no harsh shadows",
    shape_language:
      "gentle rounded rectangles and soft arcs, generous white space",
    decorative_motifs: ["pencils", "notebooks", "small clouds", "leaf sprigs"],
  },
  {
    id: "modern_educational",
    name: "آموزشی مدرن",
    source: "builtin",
    palette: {
      primary: ["#0ea5e9", "#111827"],
      secondary: ["#f97316", "#e5e7eb"],
      background: "#ffffff",
      text: "#111827",
    },
    illustration_style:
      "clean vector infographic style, crisp geometry, confident flat fills",
    mood: "clear, credible, focused",
    lighting: "flat even illumination, high contrast shapes",
    shape_language:
      "precise geometric shapes, clear grid alignment, deliberate negative space",
    decorative_motifs: ["arrows", "simple charts", "numbered steps", "thin rules"],
  },
  {
    id: "chalkboard",
    name: "تخته‌سیاه",
    source: "builtin",
    palette: {
      primary: ["#f8fafc", "#fcd34d"],
      secondary: ["#86efac", "#93c5fd"],
      background: "#1f2937",
      text: "#f8fafc",
    },
    illustration_style:
      "chalk drawing on a dark slate board, dusty strokes, hand-sketched lines",
    mood: "informal, immediate, teacher-at-the-board",
    lighting: "classroom overhead light on a matte slate surface",
    shape_language: "loose hand-drawn outlines, uneven strokes, sketchy underlines",
    decorative_motifs: [
      "chalk doodles",
      "sketched arrows",
      "dashed underlines",
      "small diagrams",
    ],
  },
  {
    id: "colorful_illustrated",
    name: "تصویرسازی رنگی",
    source: "builtin",
    palette: {
      primary: ["#ef4444", "#3b82f6"],
      secondary: ["#22c55e", "#eab308"],
      background: "#fffbeb",
      text: "#1c1917",
    },
    illustration_style:
      "bold storybook illustration, saturated colours, visible outlines",
    mood: "high energy, friendly, storybook",
    lighting: "bright even colour, graphic rather than photographic",
    shape_language: "chunky friendly shapes with confident dark outlines",
    decorative_motifs: ["speech bubbles", "sunbursts", "little characters", "banners"],
  },
];

const PERSIAN = /[\u0600-\u06FF]/;

export function detectLanguage(prompt: string): "fa" | "en" {
  return PERSIAN.test(prompt) ? "fa" : "en";
}

const WORDS = {
  fa: {
    prompt:
      "یک پوستر آموزشی مربعی 1:1 برای اینستاگرام بساز. صحنه روشن و تمام‌شده است. دکمه فراخوان، نشان امتیاز، برچسب قیمت یا برند نکش.",
  },
  en: {
    prompt:
      "Create a finished square 1:1 Instagram educational poster. Fill the frame with the lesson scene. Do not add CTA buttons, score badges, price tags or brand chips.",
  },
} as const;

/**
 * Stand-in for the Educational Agent.
 *
 * Deterministic, and shaped like the real output: language, a single image
 * prompt that carries the teacher's wording, and a style-only theme.
 */
export function buildEducationalResult(
  prompt: string,
  theme: EducationalThemeSpec,
): EducationalAgentResult {
  const language = detectLanguage(prompt);
  const words = WORDS[language];
  const trimmed = prompt.trim().replace(/\s+/g, " ");
  const style = [theme.illustration_style, theme.mood, theme.lighting]
    .filter(Boolean)
    .join(". ");
  const finalPrompt =
    language === "fa"
      ? `${words.prompt} سبک: ${style}. اگر درخواست معلم متن مشخصی دارد، همان را در پوستر بنویس: ${trimmed}`
      : `${words.prompt} Look: ${style}. If the teacher already gave exact wording, paint it on the poster: ${trimmed}`;
  return {
    language,
    final_prompt: finalPrompt.slice(0, 800),
    theme_style_notes: style || null,
    safety_notes: null,
  };
}

export function listingHeadline(prompt: string): string {
  return listingTitle(prompt);
}

/** The theme the agent would have designed when the user picked none. */
export function designedTheme(prompt: string): EducationalThemeSpec {
  const language = detectLanguage(prompt);
  const base = BUILTIN_EDUCATION_THEMES[0];
  return {
    ...base,
    name: language === "fa" ? "تم پیشنهادی آفرین" : "Afarin suggested theme",
  };
}

/**
 * A saveable theme: the visual system only. The topic and the image prompt of
 * the post it came from are deliberately dropped.
 */
export function sanitizeEducationalTheme(
  theme: EducationalThemeSpec,
  name: string,
): EducationalThemeSpec {
  return {
    name,
    palette: {
      primary: [...theme.palette.primary],
      secondary: [...theme.palette.secondary],
      ...(theme.palette.background ? { background: theme.palette.background } : {}),
      ...(theme.palette.text ? { text: theme.palette.text } : {}),
    },
    illustration_style: theme.illustration_style,
    ...(theme.mood ? { mood: theme.mood } : {}),
    ...(theme.lighting ? { lighting: theme.lighting } : {}),
    shape_language: theme.shape_language,
    decorative_motifs: [...theme.decorative_motifs],
    ...(theme.background_treatment
      ? { background_treatment: theme.background_treatment }
      : {}),
  };
}
