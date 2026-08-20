"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AssetRenderSpec, CampaignAsset, CampaignDetail } from "@/types/domain";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/layout/Container";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { ArrowBackIcon, PlusIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import { ASSET_LABELS } from "@/features/campaign/ad-renderer/templates";
import { MAX_TEXT_LAYERS } from "@/features/campaign/ad-renderer/textLayers";
import { EditorStage } from "./EditorStage";
import { EditorToolbar, type TabId } from "./EditorToolbar";
import { useEditorSession } from "./useEditorSession";

export function TextEditorPage({
  campaignId,
  assetId,
}: {
  campaignId: string;
  assetId: string;
}) {
  const router = useRouter();
  const { t } = useI18n();
  const { data, loading, error } = useAsyncData<CampaignDetail>(
    () => api.getCampaign(campaignId),
    [campaignId],
  );

  if (loading && !data) {
    return (
      <div className="min-h-dvh bg-ink-900 p-6">
        <Skeleton className="h-10 w-1/2 bg-white/10" />
        <Skeleton className="mt-6 h-80 w-full bg-white/10" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-dvh bg-background">
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("errors.campaignNotFound")}
            description={t("errors.assetEditWrongOwner")}
            action={
              <Button onClick={() => router.push("/dashboard")}>{t("nav.dashboard")}</Button>
            }
          />
        </Container>
      </div>
    );
  }

  const asset = data.assets.find((item) => item.id === assetId);
  const failed = Boolean((asset?.metadata_json as AssetRenderSpec | undefined)?.failed);
  if (!asset || failed) {
    return (
      <div className="min-h-dvh bg-background">
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("errors.assetNotFound")}
            action={
              <Button onClick={() => router.push(`/campaigns/${campaignId}`)}>
                {t("editor.backToCampaign")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  return <EditorShell campaignId={campaignId} asset={asset} />;
}

function EditorShell({
  campaignId,
  asset,
}: {
  campaignId: string;
  asset: CampaignAsset;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const [tab, setTab] = useState<TabId>("text");
  const [leaving, setLeaving] = useState(false);
  const session = useEditorSession(asset, campaignId);
  const label = t(
    (ASSET_LABELS[asset.asset_type] ?? "ad.asset.fallback") as TranslationKey,
  );

  async function handleDone() {
    setLeaving(true);
    try {
      await session.flush();
      router.push(`/campaigns/${campaignId}`);
    } catch (caught) {
      toast(displayError(caught), "error");
      setLeaving(false);
    }
  }

  const statusLabel =
    session.status === "saving"
      ? t("editor.saving")
      : session.status === "saved"
        ? t("editor.saved")
        : session.status === "error"
          ? t("editor.saveFailed")
          : session.mutated
            ? t("editor.mutated")
            : "";

  return (
    <div className="flex min-h-dvh flex-col bg-ink-950 text-white">
      <header className="flex items-center gap-2 px-3 py-3 pt-safe">
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-white/10"
          loading={leaving}
          onClick={() => void handleDone()}
          iconStart={<ArrowBackIcon width={18} height={18} />}
        >
          {t("editor.done")}
        </Button>
        <div className="min-w-0 flex-1 text-center">
          <p className="truncate text-sm font-bold">{label}</p>
          {statusLabel ? (
            <p className="text-[11px] text-white/60">{statusLabel}</p>
          ) : null}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-white/10"
          onClick={session.resetLayout}
        >
          {t("editor.reset")}
        </Button>
      </header>

      <div className="flex flex-1 flex-col gap-3 px-4 py-2">
        <EditorStage
          asset={asset}
          spec={session.previewSpec}
          layers={session.layers}
          selectedId={session.selectedId}
          onSelect={session.setSelectedId}
          onLiveChange={session.liveChange}
          onCommit={session.commit}
        />
        <div className="flex gap-2">
          <Button
            variant="subtle"
            className="flex-1"
            onClick={session.addLayer}
            disabled={session.layers.length >= MAX_TEXT_LAYERS}
            iconStart={<PlusIcon width={16} height={16} />}
          >
            {t("editor.addText")}
          </Button>
          <Button
            variant="ghost"
            className="text-white hover:bg-white/10"
            disabled={!session.canUndo}
            onClick={session.undo}
          >
            {t("editor.undo")}
          </Button>
          <Button
            variant="ghost"
            className="text-white hover:bg-white/10"
            disabled={!session.canRedo}
            onClick={session.redo}
          >
            {t("editor.redo")}
          </Button>
        </div>
      </div>

      <EditorToolbar
        tab={tab}
        onTab={setTab}
        selected={session.selected}
        canDelete={session.layers.length > 1}
        rewriting={session.rewriting}
        onLiveChange={session.patchSelectedLive}
        onCommitChange={session.updateSelected}
        onCommit={() => session.commit()}
        onDelete={session.deleteSelected}
        onRewrite={(intent) => void session.rewrite(intent)}
      />
    </div>
  );
}
