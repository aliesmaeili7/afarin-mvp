import type { CampaignObjective } from "@/types/domain";

export interface ObjectiveOption {
  value: CampaignObjective;
  emoji: string;
}

/** Spec §8 — one objective is required. */
export const OBJECTIVES: readonly ObjectiveOption[] = [
  { value: "sell_product", emoji: "🛍" },
  { value: "new_product", emoji: "✨" },
  { value: "promotion", emoji: "🎯" },
  { value: "brand_awareness", emoji: "💜" },
];

export const ALL_OBJECTIVE_VALUES: readonly CampaignObjective[] = OBJECTIVES.map(
  (item) => item.value,
);

export interface AudienceSuggestion {
  id:
    | "women_20_35"
    | "families"
    | "luxury_gifts"
    | "students"
    | "men_25_40"
    | "quality";
  /** Canonical Persian value persisted to the campaign, independent of UI locale. */
  value_fa: string;
}

/** Spec §8 — audience chips plus «خودت پیشنهاد بده». */
export const AUDIENCE_SUGGESTIONS: readonly AudienceSuggestion[] = [
  { id: "women_20_35", value_fa: "خانم‌های ۲۰ تا ۳۵ سال" },
  { id: "families", value_fa: "خانواده‌ها" },
  { id: "luxury_gifts", value_fa: "کسانی که دنبال هدیه لوکس هستن" },
  { id: "students", value_fa: "دانشجوها" },
  { id: "men_25_40", value_fa: "آقایون ۲۵ تا ۴۰ سال" },
  { id: "quality", value_fa: "مشتری‌های سختگیر و باکیفیت‌پسند" },
];

/** Used when the user picks «مطمئن نیستم — خودت پیشنهاد بده». Persisted in Persian. */
export const SUGGESTED_AUDIENCE: Record<CampaignObjective, string> = {
  sell_product: "خانم‌های ۲۵ تا ۴۰ سال که خرید آنلاین می‌کنن",
  new_product: "دنبال‌کننده‌های علاقه‌مند به محصولات تازه و خاص",
  promotion: "مشتری‌هایی که منتظر تخفیف و پیشنهاد ویژه‌ان",
  brand_awareness: "مخاطب عمومی اینستاگرام که به این دسته محصول علاقه داره",
};
