"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Feedback";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { useToast } from "@/components/ui/Toast";
import { normalizePersian } from "@/lib/format/persian";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

interface FormState {
  name: string;
  description: string;
  price_text: string;
  main_benefit: string;
  brand_name: string;
}

const EMPTY: FormState = {
  name: "",
  description: "",
  price_text: "",
  main_benefit: "",
  brand_name: "",
};

export function ProductStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, campaignId, loading } = useDraftCampaign();
  const blocked = useWizardGuard(2, detail, loading, campaignId);

  const [form, setForm] = useHydratedForm<FormState>(
    detail?.campaign.id ?? null,
    () => ({
      name: detail?.product?.name ?? "",
      description: detail?.product?.description ?? "",
      price_text: detail?.product?.price_text ?? "",
      main_benefit: detail?.product?.main_benefit ?? "",
      brand_name: detail?.brand?.name ?? "",
    }),
    EMPTY,
  );
  const [nameError, setNameError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  function update(key: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
    if (key === "name" && value.trim()) setNameError(null);
  }

  async function handleContinue() {
    if (!detail) return;
    if (!form.name.trim()) {
      setNameError("اسم محصول رو بنویس.");
      return;
    }

    setSaving(true);
    try {
      await api.saveProduct(detail.campaign.id, {
        name: normalizePersian(form.name),
        description: normalizePersian(form.description),
        price_text: normalizePersian(form.price_text),
        main_benefit: normalizePersian(form.main_benefit),
        brand_name: normalizePersian(form.brand_name),
      });
      router.push("/create/objective");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[1]}
      backHref="/create"
      heading="کمی درباره محصولت بگو"
      description="هرچی بیشتر بگی، تبلیغ دقیق‌تری می‌سازیم. فقط اسم محصول لازمه."
      footer={
        <Button fullWidth size="lg" loading={saving} onClick={handleContinue}>
          ادامه
        </Button>
      }
    >
      {loading || blocked ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          <TextField
            label="اسم محصول"
            placeholder="مثلاً زعفران ممتاز"
            value={form.name}
            error={nameError}
            onChange={(event) => update("name", event.target.value)}
          />

          <TextAreaField
            label="توضیح کوتاه"
            optional
            placeholder="مثلاً زعفران یک گرمی مناسب هدیه"
            value={form.description}
            onChange={(event) => update("description", event.target.value)}
          />

          <TextField
            label="قیمت یا تخفیف"
            optional
            placeholder="مثلاً ۳۹۹ هزار تومان یا ۲۰٪ تخفیف"
            hint="اگه ننویسی، تبلیغ بدون قیمت ساخته می‌شه."
            value={form.price_text}
            onChange={(event) => update("price_text", event.target.value)}
          />

          <TextAreaField
            label="مهم‌ترین مزیت محصول"
            optional
            rows={2}
            placeholder="چرا مشتری باید این محصول رو انتخاب کنه؟"
            value={form.main_benefit}
            onChange={(event) => update("main_benefit", event.target.value)}
          />

          <TextField
            label="اسم برند یا کسب‌وکار"
            optional
            placeholder="مثلاً سحند"
            hint="روی تبلیغ نمایش داده می‌شه."
            value={form.brand_name}
            onChange={(event) => update("brand_name", event.target.value)}
          />

          <div className="rounded-2xl border border-ink-100 bg-white p-4">
            <button
              type="button"
              onClick={() => setShowExamples((current) => !current)}
              className="text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              نمی‌دونم چی بنویسم
            </button>
            {showExamples ? (
              <ul className="mt-3 flex flex-col gap-2 text-sm leading-7 text-ink-500">
                <li>
                  <span className="font-semibold text-ink-700">توضیح کوتاه:</span> در
                  یک جمله بگو محصول چیه و چه اندازه/مدلی داره.
                </li>
                <li>
                  <span className="font-semibold text-ink-700">مزیت:</span> بگو چه
                  چیزی محصولت رو از بقیه جدا می‌کنه؛ مثلاً بسته‌بندی هدیه، ارسال
                  سریع یا کیفیت صادراتی.
                </li>
                <li>
                  <span className="font-semibold text-ink-700">قیمت:</span> اگه
                  تخفیف داری، همون رو بنویس؛ مثل «۲۰٪ تخفیف تا پایان هفته».
                </li>
              </ul>
            ) : null}
          </div>
        </div>
      )}
    </WizardShell>
  );
}
