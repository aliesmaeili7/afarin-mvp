"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { CampaignDetail } from "@/types/domain";
import { furthestAllowedStep, WIZARD_STEPS } from "./wizardSteps";

/**
 * Keeps the wizard honest: deep-linking to a later step without the earlier
 * answers sends the user back to the first missing thing instead of showing an
 * empty screen.
 */
export function useWizardGuard(
  requiredStep: number,
  detail: CampaignDetail | null,
  loading: boolean,
  campaignId: string | null,
): boolean {
  const router = useRouter();

  const allowed = furthestAllowedStep(detail);
  const blocked = !loading && (!campaignId || !detail || requiredStep > allowed);

  useEffect(() => {
    if (loading || !blocked) return;
    if (!campaignId || !detail) {
      router.replace("/create");
      return;
    }
    router.replace(WIZARD_STEPS[allowed - 1].path);
  }, [loading, blocked, campaignId, detail, allowed, router]);

  return blocked;
}
