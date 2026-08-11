import type { CampaignObjective } from "@/types/domain";

export interface ObjectiveOption {
  value: CampaignObjective;
  label_fa: string;
  description_fa: string;
  emoji: string;
}

/** Spec §8 — one objective is required. */
export const OBJECTIVES: readonly ObjectiveOption[] = [
  {
    value: "sell_product",
    label_fa: "فروش محصول",
    description_fa: "می‌خوام مستقیم بفروشم و سفارش بگیرم",
    emoji: "🛍",
  },
  {
    value: "new_product",
    label_fa: "معرفی محصول جدید",
    description_fa: "یه محصول تازه دارم و می‌خوام معرفیش کنم",
    emoji: "✨",
  },
  {
    value: "promotion",
    label_fa: "تبلیغ تخفیف",
    description_fa: "تخفیف یا پیشنهاد ویژه دارم",
    emoji: "🎯",
  },
  {
    value: "brand_awareness",
    label_fa: "افزایش آگاهی از برند",
    description_fa: "می‌خوام برندم بیشتر دیده بشه",
    emoji: "💜",
  },
];

export function objectiveLabel(objective: CampaignObjective | null): string {
  return OBJECTIVES.find((item) => item.value === objective)?.label_fa ?? "";
}

/** Spec §8 — audience chips plus «خودت پیشنهاد بده». */
export const AUDIENCE_SUGGESTIONS: readonly string[] = [
  "خانم‌های ۲۰ تا ۳۵ سال",
  "خانواده‌ها",
  "کسانی که دنبال هدیه لوکس هستن",
  "دانشجوها",
  "آقایون ۲۵ تا ۴۰ سال",
  "مشتری‌های سختگیر و باکیفیت‌پسند",
];

/** Used when the user picks «مطمئن نیستم — خودت پیشنهاد بده». */
export const SUGGESTED_AUDIENCE: Record<CampaignObjective, string> = {
  sell_product: "خانم‌های ۲۵ تا ۴۰ سال که خرید آنلاین می‌کنن",
  new_product: "دنبال‌کننده‌های علاقه‌مند به محصولات تازه و خاص",
  promotion: "مشتری‌هایی که منتظر تخفیف و پیشنهاد ویژه‌ان",
  brand_awareness: "مخاطب عمومی اینستاگرام که به این دسته محصول علاقه داره",
};
