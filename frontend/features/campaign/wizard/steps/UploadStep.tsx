"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Feedback";
import { CloseIcon, ImageIcon, SparkleIcon, UploadIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { ACCEPTED_MIME_TYPES } from "@/lib/storage/imageStore";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";
import { useDraftCampaign } from "../useDraftCampaign";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

const MAX_IMAGES = 3;

export function UploadStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, loading, reload, ensureCampaign } = useDraftCampaign();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  const images = detail?.product_images ?? [];
  const canContinue = images.length > 0;

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files).slice(0, MAX_IMAGES - images.length);
    if (list.length === 0) return;

    setBusy(true);
    try {
      const campaignId = await ensureCampaign();
      await api.uploadProductImages(campaignId, list);
      await reload();
      track("photo_uploaded", { count: list.length });
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleSample() {
    setBusy(true);
    try {
      const campaignId = await ensureCampaign();
      await api.useSampleProduct(campaignId);
      await reload();
      track("photo_uploaded", { sample: true });
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(imageId: string) {
    if (!detail) return;
    setBusy(true);
    try {
      await api.deleteProductImage(detail.campaign.id, imageId);
      await reload();
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[0]}
      heading="عکس محصولت رو آپلود کن"
      description="یه عکس معمولی با موبایل هم کافیه. می‌تونی تا ۳ عکس اضافه کنی."
      footer={
        <>
          <Button
            fullWidth
            size="lg"
            disabled={!canContinue}
            loading={busy}
            onClick={() => router.push("/create/product")}
          >
            ادامه
          </Button>
          {!canContinue ? (
            <button
              type="button"
              onClick={handleSample}
              className="flex h-11 items-center justify-center rounded-xl text-sm font-semibold text-brand-700 underline-offset-4 hover:bg-brand-50 hover:underline"
            >
              عکس ندارم، با نمونه امتحان می‌کنم
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
                  : "border-ink-200 bg-white hover:border-brand-300 hover:bg-brand-50/40"
              }`}
            >
              <span className="grid size-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
                <UploadIcon width={24} height={24} />
              </span>
              <span className="text-base font-bold text-ink-900">
                عکس محصولت رو انتخاب کن
              </span>
              <span className="text-xs text-ink-400">
                از گالری موبایل یا کامپیوترت
              </span>
            </button>
          ) : null}

          {images.length > 0 ? (
            <div className="grid grid-cols-3 gap-3">
              {images.map((image) => (
                <ImageThumb
                  key={image.id}
                  storagePath={image.storage_path}
                  isPrimary={image.is_primary}
                  onRemove={() => handleRemove(image.id)}
                />
              ))}
            </div>
          ) : null}

          <div className="flex items-start gap-3 rounded-2xl bg-brand-50/70 p-4">
            <span className="mt-0.5 text-brand-600">
              <SparkleIcon width={18} height={18} />
            </span>
            <p className="text-sm leading-7 text-ink-600">
              نگران کیفیت عکس نباش. ما محصولت رو توی یک صحنه تبلیغاتی می‌ذاریم و
              متن‌های فارسی رو خودمون اضافه می‌کنیم.
            </p>
          </div>
        </div>
      )}
    </WizardShell>
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
  const url = useResolvedAssetUrl(storagePath);

  return (
    <div className="relative aspect-square overflow-hidden rounded-2xl border border-ink-100 bg-white">
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt="عکس محصول" className="h-full w-full object-cover" />
      ) : (
        <div className="grid h-full place-items-center text-ink-300">
          <ImageIcon />
        </div>
      )}
      {isPrimary ? (
        <span className="absolute bottom-1.5 start-1.5 rounded-full bg-ink-900/80 px-2 py-0.5 text-[0.65rem] font-semibold text-white">
          عکس اصلی
        </span>
      ) : null}
      <button
        type="button"
        onClick={onRemove}
        aria-label="حذف عکس"
        className="absolute top-1.5 end-1.5 grid size-9 place-items-center rounded-full bg-ink-900/70 text-white transition-colors hover:bg-coral-600"
      >
        <CloseIcon width={14} height={14} />
      </button>
    </div>
  );
}
