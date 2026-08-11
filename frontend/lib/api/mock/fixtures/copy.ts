import type { CampaignObjective, ReelConcept } from "@/types/domain";
import { pick, rotate, type CopyContext } from "./context";

const CTAS: Record<CampaignObjective, readonly string[]> = {
  sell_product: [
    "همین حالا سفارش بده",
    "برای خرید دایرکت بده",
    "سفارشت رو ثبت کن",
  ],
  new_product: ["اولین نفر باش", "همین حالا ببینش", "نظرت رو برامون بنویس"],
  promotion: [
    "تا تموم نشده سفارش بده",
    "از این قیمت جا نمون",
    "همین امروز استفاده کن",
  ],
  brand_awareness: ["ما رو دنبال کن", "با ما همراه شو", "صفحه‌مون رو ببین"],
};

export function buildCtas(ctx: CopyContext): string[] {
  return rotate(CTAS[ctx.objective], ctx.round);
}

export function buildPrimaryCta(ctx: CopyContext): string {
  return buildCtas(ctx)[0];
}

function priceLine(ctx: CopyContext): string | null {
  if (!ctx.priceText) return null;
  return ctx.objective === "promotion"
    ? `💰 ${ctx.priceText} — فرصت محدود`
    : `💰 ${ctx.priceText}`;
}

function brandSignature(ctx: CopyContext): string | null {
  return ctx.brandName ? `— ${ctx.brandName}` : null;
}

function joinLines(lines: (string | null)[]): string {
  return lines.filter((line): line is string => Boolean(line)).join("\n");
}

export interface CaptionSet {
  caption_short: string;
  caption_friendly: string;
  caption_persuasive: string;
}

/** Spec §16 section 4 — three captions with distinct tones. */
export function buildCaptions(ctx: CopyContext): CaptionSet {
  const cta = buildPrimaryCta(ctx);
  const benefit = ctx.benefit ?? ctx.description ?? "کیفیتی که فرقش رو حس می‌کنی";
  const audience = ctx.audience ? `مناسب ${ctx.audience}` : null;

  const shortVariants = [
    joinLines([
      `${ctx.productName} ✨`,
      benefit,
      priceLine(ctx),
      `${cta} 👇`,
      brandSignature(ctx),
    ]),
    joinLines([
      `${ctx.productName} رسید ✨`,
      priceLine(ctx),
      cta,
      brandSignature(ctx),
    ]),
  ];

  const friendlyVariants = [
    joinLines([
      `سلام رفقا 👋`,
      `این ${ctx.productName} یکی از اون چیزهاییه که وقتی امتحانش می‌کنی می‌گی چرا زودتر نخریدم!`,
      benefit ? `${benefit} 🙌` : null,
      audience,
      priceLine(ctx),
      `اگه سوالی داشتی راحت دایرکت بده، جواب می‌دیم 💬`,
      cta,
    ]),
    joinLines([
      `یه پیشنهاد خودمونی 🤍`,
      `${ctx.productName} رو مخصوص کسایی آوردیم که سختگیرن.`,
      benefit,
      priceLine(ctx),
      `کامنت بذار تا راهنماییت کنیم 💬`,
      cta,
    ]),
  ];

  const persuasiveVariants = [
    joinLines([
      `چرا ${ctx.productName}؟`,
      `چون ${benefit}.`,
      audience ? `${audience} — دقیقاً همون چیزی که دنبالشی.` : null,
      priceLine(ctx),
      `تعداد محدوده و ممکنه زود تموم بشه ⏳`,
      `${cta} 👇`,
      brandSignature(ctx),
    ]),
    joinLines([
      `فرق ${ctx.productName} با بقیه چیه؟`,
      `${benefit} — همین.`,
      priceLine(ctx),
      `اگه دنبال یه انتخاب مطمئنی، این همونه.`,
      `${cta} ✅`,
      brandSignature(ctx),
    ]),
  ];

  return {
    caption_short: pick(shortVariants, ctx.round),
    caption_friendly: pick(friendlyVariants, ctx.round),
    caption_persuasive: pick(persuasiveVariants, ctx.round),
  };
}

/** Spec §16 section 5 — three short Story texts. */
export function buildStoryIdeas(ctx: CopyContext): string[] {
  const cta = buildPrimaryCta(ctx);
  const variants: string[][] = [
    [
      `${ctx.productName} موجود شد ✨\nسوایپ کن و ببین`,
      `کدوم رو بیشتر دوست داری؟ 🤔\nتوی نظرسنجی رأی بده`,
      `${ctx.priceText ? `${ctx.priceText} 💰\n` : ""}${cta} 👆`,
    ],
    [
      `یه سؤال 👀\nدنبال ${ctx.productName} خوب بودی؟`,
      `پشت‌صحنه آماده‌سازی سفارش‌ها 📦\nهر سفارش با دقت بسته‌بندی می‌شه`,
      `آخرین فرصت ⏳\n${cta}`,
    ],
  ];
  return pick(variants, ctx.round);
}

export function buildHashtags(ctx: CopyContext): string {
  const base = [
    "#خرید_آنلاین",
    "#فروشگاه_اینترنتی",
    "#ارسال_به_سراسر_کشور",
    "#کیفیت_تضمینی",
  ];
  const byObjective: Record<CampaignObjective, string[]> = {
    sell_product: ["#خرید_مطمئن", "#پیشنهاد_ویژه"],
    new_product: ["#تازه_رسید", "#محصول_جدید"],
    promotion: ["#تخفیف", "#فروش_ویژه", "#حراج"],
    brand_awareness: ["#برند_ایرانی", "#کار_ایرانی"],
  };
  const brandTag = ctx.brandName
    ? [`#${ctx.brandName.trim().replace(/\s+/g, "_")}`]
    : [];

  return rotate([...base, ...byObjective[ctx.objective], ...brandTag], ctx.round).join(
    " ",
  );
}

/** Spec §16 section 6 — storyboard only, no video generation. */
export function buildReelConcept(ctx: CopyContext): ReelConcept {
  const cta = buildPrimaryCta(ctx);
  const benefit = ctx.benefit ?? "کیفیتی که حس می‌شه";

  const variants: ReelConcept[] = [
    {
      hook_fa: `اگه دنبال ${ctx.productName} خوب می‌گردی، سه ثانیه وقت بده`,
      scenes_fa: [
        "نمای نزدیک از محصول در حال باز شدن بسته‌بندی، نور گرم",
        `نمای متوسط از استفاده واقعی از محصول، متن روی تصویر: «${benefit}»`,
        `نمای پایانی از محصول کنار لوگو${ctx.priceText ? ` و قیمت ${ctx.priceText}` : ""}`,
      ],
      cta_fa: cta,
      voiceover_fa: `${ctx.productName}؛ ${benefit}. ${cta}.`,
      duration_seconds: 12,
    },
    {
      hook_fa: `این اشتباه رو موقع خرید ${ctx.productName} نکن!`,
      scenes_fa: [
        "نمای سریع از یک انتخاب اشتباه و بی‌کیفیت",
        `کات به محصول ما، نمای چرخشی آهسته، متن: «${benefit}»`,
        "نمای پایانی: بسته‌بندی آماده ارسال با لوگوی برند",
      ],
      cta_fa: cta,
      voiceover_fa: `فرقش اینجاست: ${benefit}. ${cta}.`,
      duration_seconds: 14,
    },
  ];

  return pick(variants, ctx.round);
}
