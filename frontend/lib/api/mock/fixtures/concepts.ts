import type { CampaignObjective, VisualStyle } from "@/types/domain";
import { backgroundsForStyle } from "@/lib/content/backgrounds";
import { pick, rotate, type CopyContext } from "./context";

interface ConceptArchetype {
  title_fa: string;
  description_fa: string;
  visual_direction: string;
  background_prompt: string;
}

const ARCHETYPES: Record<VisualStyle, readonly ConceptArchetype[]> = {
  luxury: [
    {
      title_fa: "هدیه لوکس",
      description_fa:
        "پس‌زمینه تیره و مخملی با نور نقطه‌ای روی محصول و جزئیات طلایی؛ حس یک هدیه گران‌قیمت.",
      visual_direction: "نور نقطه‌ای، سایه‌های عمیق، جزئیات طلایی",
      background_prompt:
        "dark velvet studio backdrop, single soft spotlight, golden accents, premium gift mood, no text",
    },
    {
      title_fa: "سادگی گران‌قیمت",
      description_fa:
        "ترکیب تیره و مینیمال با فضای خالی زیاد، تا تمام توجه روی خود محصول بمونه.",
      visual_direction: "فضای منفی زیاد، کنتراست ملایم، تمرکز روی محصول",
      background_prompt:
        "minimal dark gradient backdrop, generous negative space, soft rim light, no text",
    },
    {
      title_fa: "درخشش شبانه",
      description_fa:
        "نورپردازی دراماتیک با بازتاب ملایم زیر محصول؛ مناسب حس خاص و متفاوت بودن.",
      visual_direction: "نورپردازی دراماتیک، بازتاب زیر محصول",
      background_prompt:
        "dramatic night lighting, subtle reflective surface, deep shadows, no text",
    },
  ],
  minimal: [
    {
      title_fa: "فضای خالی، تمرکز کامل",
      description_fa:
        "پس‌زمینه روشن و یکدست با سایه‌ای نرم؛ ساده، تمیز و بدون حواس‌پرتی.",
      visual_direction: "پس‌زمینه یکدست روشن، سایه نرم",
      background_prompt:
        "clean light seamless backdrop, soft natural shadow, editorial minimal, no text",
    },
    {
      title_fa: "کاغذ و نور",
      description_fa:
        "بافت کاغذی ملایم و نور طبیعی از کنار؛ حس دست‌ساز و باکیفیت.",
      visual_direction: "بافت کاغذی، نور جانبی طبیعی",
      background_prompt:
        "soft paper texture background, natural side light, warm neutral tones, no text",
    },
    {
      title_fa: "خط و ترتیب",
      description_fa:
        "چیدمان هندسی و منظم با خطوط راهنمای نازک؛ مرتب و حرفه‌ای.",
      visual_direction: "شبکه هندسی، خطوط نازک راهنما",
      background_prompt:
        "geometric grid composition, thin guide lines, neutral palette, no text",
    },
  ],
  friendly: [
    {
      title_fa: "گرم و نزدیک",
      description_fa:
        "رنگ‌های گرم هلویی و فرم‌های نرم؛ حس روزمره و صمیمی که مخاطب باهاش راحته.",
      visual_direction: "پالت گرم، فرم‌های نرم و گرد",
      background_prompt:
        "warm peach gradient, soft rounded shapes, friendly everyday mood, no text",
    },
    {
      title_fa: "صبح آفتابی",
      description_fa:
        "نور گرم صبحگاهی و فضایی خودمونی؛ انگار محصول توی خونه خود مشتریه.",
      visual_direction: "نور گرم صبحگاهی، فضای خانگی",
      background_prompt:
        "morning sunlight, cozy home setting, warm cream tones, no text",
    },
    {
      title_fa: "لبخند روی قفسه",
      description_fa:
        "رنگ‌های شاد ملایم با چیدمان بی‌تکلف؛ ساده و دوست‌داشتنی.",
      visual_direction: "رنگ‌های شاد ملایم، چیدمان ساده",
      background_prompt:
        "soft cheerful pastel palette, casual arrangement, no text",
    },
  ],
  bold: [
    {
      title_fa: "رنگ بزن، دیده شو",
      description_fa:
        "گرادیان پرانرژی با کنتراست بالا و تیتر درشت؛ ساخته شده برای دیده شدن.",
      visual_direction: "گرادیان پرانرژی، کنتراست بالا",
      background_prompt:
        "vivid energetic gradient, high contrast, bold poster look, no text",
    },
    {
      title_fa: "انرژی خالص",
      description_fa:
        "رنگ‌های الکتریکی و فرم‌های پویا؛ مناسب مخاطب جوان و پرانرژی.",
      visual_direction: "رنگ‌های الکتریکی، فرم‌های پویا",
      background_prompt:
        "electric neon color blocking, dynamic shapes, youthful energy, no text",
    },
    {
      title_fa: "توقف در اسکرول",
      description_fa:
        "کنتراست شدید رنگی که چشم مخاطب رو وسط اسکرول متوقف می‌کنه.",
      visual_direction: "کنتراست شدید، بلوک‌های رنگی",
      background_prompt:
        "extreme color contrast, scroll-stopping composition, no text",
    },
  ],
  persian_traditional: [
    {
      title_fa: "اصالت ایرانی",
      description_fa:
        "رنگ‌های زمردی و طلایی همراه با قوس‌های الهام‌گرفته از معماری ایرانی.",
      visual_direction: "پالت زمردی و طلایی، قوس ایرانی",
      background_prompt:
        "emerald and gold palette, persian architectural arch silhouette, no text",
    },
    {
      title_fa: "گرمای خاک",
      description_fa:
        "پالت گرم خاکی با بافت پارچه؛ حس دست‌ساز، اصیل و قابل‌اعتماد.",
      visual_direction: "پالت خاکی گرم، بافت پارچه",
      background_prompt:
        "warm earthy palette, woven fabric texture, handcrafted authenticity, no text",
    },
    {
      title_fa: "نقش و قاب",
      description_fa:
        "قاب‌بندی تزئینی الهام‌گرفته از کاشی‌کاری ایرانی، با محصول در مرکز قاب.",
      visual_direction: "قاب تزئینی کاشی‌کاری، تقارن",
      background_prompt:
        "persian tilework inspired decorative frame, symmetrical, no text",
    },
  ],
  modern: [
    {
      title_fa: "مینیمال مدرن",
      description_fa:
        "پالت سرد و روشن با سایه‌های نرم و تایپوگرافی امروزی؛ تمیز و حرفه‌ای.",
      visual_direction: "پالت سرد روشن، سایه نرم",
      background_prompt:
        "cool light palette, soft studio shadows, contemporary product photography, no text",
    },
    {
      title_fa: "شب شهری",
      description_fa:
        "پالت تیره آبی با نور سرد؛ حس امروزی، تکنولوژیک و شیک.",
      visual_direction: "پالت آبی تیره، نور سرد",
      background_prompt:
        "deep blue night palette, cool rim lighting, sleek modern mood, no text",
    },
    {
      title_fa: "کارت شیشه‌ای",
      description_fa:
        "لایه‌های نیمه‌شفاف و ترکیب‌بندی تمیز؛ ظاهری مدرن و مرتب.",
      visual_direction: "لایه‌های شیشه‌ای، ترکیب‌بندی تمیز",
      background_prompt:
        "frosted glass layers, clean composition, modern minimal, no text",
    },
  ],
};

const HEADLINES: Record<CampaignObjective, readonly ((ctx: CopyContext) => string)[]> = {
  sell_product: [
    (ctx) => `${ctx.productName}، همونی که دنبالش بودی`,
    (ctx) => `${ctx.productName} رو همین امروز داشته باش`,
    (ctx) => `کیفیتی که با ${ctx.productName} حس می‌کنی`,
    (ctx) => `${ctx.productName}؛ انتخاب کسانی که فرق رو می‌فهمن`,
  ],
  new_product: [
    (ctx) => `تازه رسید: ${ctx.productName}`,
    (ctx) => `${ctx.productName}، جدیدترین انتخاب ما`,
    (ctx) => `با ${ctx.productName} آشنا شو`,
    (ctx) => `یه شروع تازه با ${ctx.productName}`,
  ],
  promotion: [
    (ctx) => `${ctx.productName} با قیمت ویژه`,
    (ctx) => `فرصت محدود برای ${ctx.productName}`,
    (ctx) => `الان بهترین وقت خرید ${ctx.productName}`,
    (ctx) => `${ctx.productName}، این هفته ویژه‌تر`,
  ],
  brand_awareness: [
    (ctx) =>
      ctx.brandName
        ? `${ctx.brandName}؛ خانه‌ی ${ctx.productName}`
        : `جایی برای ${ctx.productName}`,
    (ctx) => `ما ${ctx.productName} رو جدی می‌گیریم`,
    (ctx) =>
      ctx.brandName
        ? `${ctx.productName}، با امضای ${ctx.brandName}`
        : `${ctx.productName}، ساخته‌شده با وسواس`,
    () => `کیفیت، عادت ماست`,
  ],
};

export function buildSubheadline(ctx: CopyContext): string {
  if (ctx.benefit) return ctx.benefit;
  if (ctx.description) return ctx.description;
  if (ctx.audience) return `مناسب ${ctx.audience}`;
  return "کیفیتی که می‌تونی بهش اعتماد کنی";
}

export interface ConceptFixture {
  title_fa: string;
  headline_fa: string;
  description_fa: string;
  visual_direction: string;
  background_prompt: string;
  background_id: string;
}

/** Three concepts per round; a new round rotates archetypes and headlines. */
export function buildConcepts(ctx: CopyContext): ConceptFixture[] {
  const archetypes = rotate(ARCHETYPES[ctx.style], ctx.round);
  const headlines = HEADLINES[ctx.objective];
  const backgrounds = backgroundsForStyle(ctx.style);

  return archetypes.slice(0, 3).map((archetype, index) => ({
    title_fa: archetype.title_fa,
    headline_fa: pick(headlines, ctx.round + index)(ctx),
    description_fa: archetype.description_fa,
    visual_direction: archetype.visual_direction,
    background_prompt: archetype.background_prompt,
    background_id: pick(backgrounds, ctx.round + index).id,
  }));
}
