"use client";

import { useCallback } from "react";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

export function useClipboard() {
  const { toast } = useToast();
  const { t } = useI18n();

  return useCallback(
    async (text: string, message?: string) => {
      try {
        await navigator.clipboard.writeText(text);
        toast(message ?? t("common.copied"));
        return true;
      } catch {
        toast(t("common.copyFailed"), "error");
        return false;
      }
    },
    [toast, t],
  );
}
