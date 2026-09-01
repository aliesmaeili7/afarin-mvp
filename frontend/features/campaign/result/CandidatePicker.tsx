"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { CampaignDetail, VisualCandidate } from "@/types/domain";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";

export function ConceptSwitcher({
  detail,
  onChanged,
}: {
  detail: CampaignDetail;
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const [focusing, setFocusing] = useState<string | null>(null);

  const visible = (detail.visual_candidates ?? []).filter(
    (item) => !item.hidden && !item.hard_failed,
  );
  if (visible.length < 2) return null;

  const focusedId = detail.visual_attempt?.selected_candidate_id ?? visible[0]?.id;

  async function handleFocus(candidate: VisualCandidate) {
    if (candidate.id === focusedId) return;
    setFocusing(candidate.id);
    try {
      await api.focusVisualCandidate(detail.campaign.id, candidate.id);
      onChanged();
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setFocusing(null);
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <header>
        <h2 className="text-lg font-extrabold text-foreground">{t("result.conceptsTitle")}</h2>
        <p className="mt-1 text-sm leading-7 text-muted">{t("result.conceptsDescription")}</p>
      </header>
      <div className="grid grid-cols-3 gap-2">
        {visible.map((candidate) => (
          <ConceptCard
            key={candidate.id}
            candidate={candidate}
            selected={candidate.id === focusedId}
            loading={focusing === candidate.id}
            disabled={focusing !== null && focusing !== candidate.id}
            onSelect={() => void handleFocus(candidate)}
          />
        ))}
      </div>
    </section>
  );
}

function ConceptCard({
  candidate,
  selected,
  loading,
  disabled,
  onSelect,
}: {
  candidate: VisualCandidate;
  selected: boolean;
  loading: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  const { t } = useI18n();
  const url = useResolvedAssetUrl(candidate.storage_path);
  return (
    <Card className={selected ? "ring-2 ring-brand-400" : undefined}>
      <button
        type="button"
        onClick={onSelect}
        disabled={disabled}
        className="block w-full overflow-hidden"
      >
        <div className="relative aspect-4/5 w-full bg-ink-100">
          {url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={url} alt="" className="h-full w-full object-cover" />
          ) : null}
        </div>
      </button>
      <div className="p-2">
        <Button
          fullWidth
          size="sm"
          variant={selected ? "primary" : "outline"}
          loading={loading}
          disabled={disabled}
          onClick={onSelect}
        >
          {selected ? t("result.usingThisAd") : t("result.useThisAd")}
        </Button>
      </div>
    </Card>
  );
}
