"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Feedback";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { CloseIcon, ImageIcon, SparkleIcon, UploadIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { normalizePersian } from "@/lib/format/persian";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import { ACCEPTED_MIME_TYPES } from "@/lib/storage/imageStore";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";
import type { CropRect, ProductImage } from "@/types/domain";
import { CropEditor } from "../CropEditor";
import { FULL_CROP } from "../cropMath";
import { useDraftCampaign } from "../useDraftCampaign";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

interface ProductForm {
  name: string;
  description: string;
  price_text: string;
  main_benefit: string;
  brand_name: string;
}

const EMPTY_PRODUCT: ProductForm = {
  name: "",
  description: "",
  price_text: "",
  main_benefit: "",
  brand_name: "",
};

const MAX_IMAGES = 3;

export function UploadStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const { detail, loading, reload, ensureCampaign } = useDraftCampaign();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [cropByImage, setCropByImage] = useState<Record<string, CropRect>>({});

  const images = detail?.product_images ?? [];
  const primary = images.find((image) => image.is_primary) ?? images[0];
  const [form, setForm] = useHydratedForm<ProductForm>(
    detail
      ? `${detail.campaign.id}:${detail.product?.name ?? ""}:${primary?.id ?? ""}`
      : null,
    () => ({
      name: detail?.product?.name ?? "",
      description: detail?.product?.description ?? "",
      price_text: detail?.product?.price_text ?? "",
      main_benefit: detail?.product?.main_benefit ?? "",
      brand_name: detail?.brand?.name ?? "",
    }),
    EMPTY_PRODUCT,
  );
  const [nameError, setNameError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const hasExtras = Boolean(
    form.description.trim() ||
      form.price_text.trim() ||
      form.main_benefit.trim() ||
      form.brand_name.trim(),
  );
  const canContinue = images.length > 0 && Boolean(form.name.trim());
  const campaignId = detail?.campaign.id;
  const imageId = primary?.id;
  const cropDraft = primary
    ? (cropByImage[primary.id] ?? primary.crop ?? FULL_CROP)
    : null;

  const setCropDraft = useCallback((next: CropRect) => {
    if (!imageId) return;
    setCropByImage((current) => ({ ...current, [imageId]: next }));
  }, [imageId]);

  const persistCrop = useCallback(
    async (rect: CropRect) => {
      if (!campaignId || !imageId) return;
      try {
        await api.updateProductCrop(campaignId, imageId, rect);
      } catch (caught) {
        toast(displayError(caught), "error");
      }
    },
    [campaignId, imageId, toast, displayError],
  );

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files).slice(0, MAX_IMAGES - images.length);
    if (list.length === 0) return;

    setBusy(true);
    try {
      const nextCampaignId = await ensureCampaign();
      await api.uploadProductImages(nextCampaignId, list);
      await reload();
      track("photo_uploaded", { count: list.length });
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleSample() {
    setBusy(true);
    try {
      const nextCampaignId = await ensureCampaign();
      await api.useSampleProduct(nextCampaignId);
      await reload();
      track("photo_uploaded", { sample: true });
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(removedId: string) {
    if (!detail) return;
    setBusy(true);
    try {
      await api.deleteProductImage(detail.campaign.id, removedId);
      await reload();
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleContinue() {
    if (!detail || !primary || !cropDraft) return;
    if (!form.name.trim()) {
      setNameError(t("errors.productNameRequired"));
      return;
    }
    setBusy(true);
    try {
      await api.updateProductCrop(detail.campaign.id, primary.id, cropDraft);
      await api.saveProduct(detail.campaign.id, {
        name: normalizePersian(form.name),
        description: normalizePersian(form.description),
        price_text: normalizePersian(form.price_text),
        main_benefit: normalizePersian(form.main_benefit),
        brand_name: normalizePersian(form.brand_name),
      });
      router.push("/create/brief");
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[0]}
      heading={t("wizard.uploadTitle")}
      description={t("wizard.uploadDescription")}
      footer={
        <>
          <Button
            fullWidth
            size="lg"
            disabled={!canContinue}
            loading={busy}
            onClick={() => void handleContinue()}
          >
            {t("common.continue")}
          </Button>
          {!canContinue ? (
            <button
              type="button"
              onClick={handleSample}
              className="flex h-11 items-center justify-center rounded-xl text-sm font-semibold text-brand-700 underline-offset-4 hover:bg-brand-50 hover:underline"
            >
              {t("wizard.sample")}
            </button>
          ) : null}
        </>
      }
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_MIME_TYPES.join(",")}
        multiple
        className="hidden"
        onChange={(event) => {
          if (event.target.files) void handleFiles(event.target.files);
        }}
      />

      {loading ? (
        <Skeleton className="h-56 w-full" />
      ) : (
        <div className="flex flex-col gap-4">
          {images.length < MAX_IMAGES ? (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                void handleFiles(event.dataTransfer.files);
              }}
              className={`flex w-full flex-col items-center gap-3 rounded-3xl border-2 border-dashed px-6 py-12 transition-colors ${
                dragging
                  ? "border-brand-500 bg-brand-50"
                  : "border-ink-200 bg-surface hover:border-brand-300 hover:bg-brand-50/40"
              }`}
            >
              <span className="grid size-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
                <UploadIcon width={24} height={24} />
              </span>
              <span className="text-base font-bold text-foreground">
                {t("wizard.dropTitle")}
              </span>
              <span className="text-xs text-ink-400">{t("wizard.dropHint")}</span>
            </button>
          ) : null}

          {primary && cropDraft ? (
            <PrimaryCrop
              image={primary}
              crop={cropDraft}
              onChange={setCropDraft}
              onCommit={(rect) => void persistCrop(rect)}
              onRemove={() => handleRemove(primary.id)}
            />
          ) : null}

          {images.length > 1 ? (
            <div className="grid grid-cols-3 gap-3">
              {images
                .filter((image) => image.id !== primary?.id)
                .map((image) => (
                  <ImageThumb
                    key={image.id}
                    storagePath={image.storage_path}
                    isPrimary={false}
                    onRemove={() => handleRemove(image.id)}
                  />
                ))}
            </div>
          ) : null}

          {primary ? (
            <div className="flex flex-col gap-4">
              <TextField
                label={t("wizard.productName")}
                placeholder={t("wizard.productNamePlaceholder")}
                value={form.name}
                error={nameError}
                onChange={(event) => {
                  const value = event.target.value;
                  setForm((current) => ({ ...current, name: value }));
                  if (value.trim()) setNameError(null);
                }}
              />
              {showDetails || hasExtras ? (
                <>
                  <TextAreaField
                    label={t("wizard.productDesc")}
                    optional
                    placeholder={t("wizard.productDescPlaceholder")}
                    value={form.description}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                  />
                  <TextField
                    label={t("wizard.productPrice")}
                    optional
                    placeholder={t("wizard.productPricePlaceholder")}
                    hint={t("wizard.productPriceHint")}
                    value={form.price_text}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        price_text: event.target.value,
                      }))
                    }
                  />
                  <TextAreaField
                    label={t("wizard.productBenefit")}
                    optional
                    rows={2}
                    placeholder={t("wizard.productBenefitPlaceholder")}
                    value={form.main_benefit}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        main_benefit: event.target.value,
                      }))
                    }
                  />
                  <TextField
                    label={t("wizard.productBrand")}
                    optional
                    placeholder={t("wizard.productBrandPlaceholder")}
                    hint={t("wizard.productBrandHint")}
                    value={form.brand_name}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        brand_name: event.target.value,
                      }))
                    }
                  />
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowDetails(true)}
                  className="-mx-2 flex h-11 items-center self-start rounded-xl px-2 text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
                >
                  {t("wizard.moreDetails")}
                </button>
              )}
            </div>
          ) : null}

          <div className="flex items-start gap-3 rounded-2xl bg-brand-50/70 p-4">
            <span className="mt-0.5 text-brand-600">
              <SparkleIcon width={18} height={18} />
            </span>
            <p className="text-sm leading-7 text-ink-600">{t("wizard.uploadTip")}</p>
          </div>
        </div>
      )}
    </WizardShell>
  );
}

function PrimaryCrop({
  image,
  crop,
  onChange,
  onCommit,
  onRemove,
}: {
  image: ProductImage;
  crop: CropRect;
  onChange: (crop: CropRect) => void;
  onCommit: (crop: CropRect) => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const url = useResolvedAssetUrl(image.storage_path);
  if (!url) {
    return <Skeleton className="h-72 w-full" />;
  }
  return (
    <div className="relative">
      <CropEditor src={url} crop={crop} onChange={onChange} onCommit={onCommit} />
      <button
        type="button"
        onClick={onRemove}
        aria-label={t("wizard.removePhoto")}
        className="absolute top-3 end-3 grid size-10 place-items-center rounded-full bg-ink-900/70 text-white transition-colors hover:bg-coral-600"
      >
        <CloseIcon width={14} height={14} />
      </button>
    </div>
  );
}

function ImageThumb({
  storagePath,
  isPrimary,
  onRemove,
}: {
  storagePath: string;
  isPrimary: boolean;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const url = useResolvedAssetUrl(storagePath);

  return (
    <div className="relative aspect-square overflow-hidden rounded-2xl border border-border bg-surface">
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt={t("wizard.photoAlt")} className="h-full w-full object-cover" />
      ) : (
        <div className="grid h-full place-items-center text-ink-300">
          <ImageIcon />
        </div>
      )}
      {isPrimary ? (
        <span className="absolute bottom-1.5 start-1.5 rounded-full bg-ink-900/80 px-2 py-0.5 text-[0.65rem] font-semibold text-white">
          {t("wizard.primaryPhoto")}
        </span>
      ) : null}
      <button
        type="button"
        onClick={onRemove}
        aria-label={t("wizard.removePhoto")}
        className="absolute top-1.5 end-1.5 grid size-9 place-items-center rounded-full bg-ink-900/70 text-white transition-colors hover:bg-coral-600"
      >
        <CloseIcon width={14} height={14} />
      </button>
    </div>
  );
}
