"use client";

import { useCallback } from "react";
import { useToast } from "@/components/ui/Toast";

export function useClipboard() {
  const { toast } = useToast();

  return useCallback(
    async (text: string, message = "کپی شد") => {
      try {
        await navigator.clipboard.writeText(text);
        toast(message);
        return true;
      } catch {
        toast("کپی نشد. متن رو دستی انتخاب کن.", "error");
        return false;
      }
    },
    [toast],
  );
}
