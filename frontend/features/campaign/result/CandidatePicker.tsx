"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Container } from "@/components/layout/Container";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { CampaignDetail, VisualCandidate } from "@/types/domain";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";

export function CandidatePicker({
  detail,
  onChanged,
}: {
  detail: CampaignDetail;
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const [selecting, setSelecting] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  const visible = (detail.visual_candidates ?? []).filter(
    (item) => !item.hidden && !item.hard_failed,
  );

  async function handleSelect(candidate: VisualCandidate) {
    setSelecting(candidate.id);
    try {
      await api.selectVisualCandidate(detail.campaign.id, candidate.id);
      onChanged();
    } catch (caught) {
      toast(displayError(caught), "error");
      setSelecting(null);
    }
  }

  async function handleRegen() {
    setRegenerating(true);
    try {
      await api.regenerateVisuals(detail.campaign.id);
      onChanged();
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <div className="min-h-dvh bg-background">
      <SiteHeader />
      <Container size="md" className="flex flex-col gap-6 py-8">
        <header className="text-center">
          <h1 className="text-3xl font-extrabold text-foreground">{t("result.pickTitle")}</h1>
          <p className="mt-2 text-sm leading-7 text-muted">{t("result.pickSubtitle")}</p>
        </header>

        {visible.length === 0 ? (
          <p className="text-center text-sm text-muted">{t("result.pickEmpty")}</p>
        ) : (
          <div className="flex flex-col gap-4">
            {visible.map((candidate) => (
              <CandidateCard
                key={candidate.id}
                candidate={candidate}
                loading={selecting === candidate.id}
                disabled={selecting !== null && selecting !== candidate.id}
                onSelect={() => void handleSelect(candidate)}
              />
            ))}
          </div>
        )}

        <Button
          fullWidth
          variant="outline"
          size="lg"
          loading={regenerating}
          onClick={() => void handleRegen()}
        >
          {t("result.generateThree")}
        </Button>
      </Container>
    </div>
  );
}

function CandidateCard({
  candidate,
  loading,
  disabled,
  onSelect,
}: {
  candidate: VisualCandidate;
  loading: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  const { t } = useI18n();
  const url = useResolvedAssetUrl(candidate.storage_path);
  return (
    <Card className="overflow-hidden">
      <div className="relative aspect-4/5 w-full bg-ink-100">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt="" className="h-full w-full object-cover" />
        ) : null}
      </div>
      <div className="p-4">
        <Button fullWidth loading={loading} disabled={disabled} onClick={onSelect}>
          {t("result.pickThis")}
        </Button>
      </div>
    </Card>
  );
}
