"use client";

import { useEffect, useState } from "react";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ArtifactAspect, ChatLanguage } from "@/lib/api/chat/types";
import type { PendingGeneration } from "../useChatSession";
import { ChatActivityIndicator } from "./ChatActivityIndicator";

export function GenerationPlaceholder({
  pending,
  phase,
  language,
  aspectRatio,
  imageCount,
}: {
  pending: PendingGeneration;
  phase?: string | null;
  language?: ChatLanguage | null;
  aspectRatio?: ArtifactAspect | null;
  imageCount?: number;
}) {
  const { t } = useI18n();
  const [seconds, setSeconds] = useState(0);
  const lang = language ?? pending.language;
  const activity = phase ?? pending.phase ?? "generating_image";
  const aspect = aspectRatio ?? pending.aspectRatio ?? "1:1";

  useEffect(() => {
    const tick = () =>
      setSeconds(Math.max(0, Math.floor((Date.now() - pending.startedAt) / 1000)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [pending.startedAt]);

  return (
    <div
      data-chat="generation-placeholder"
      dir={lang === "en" ? "ltr" : "rtl"}
      className="flex max-w-md flex-col gap-3"
    >
      <ChatActivityIndicator
        phase={activity}
        language={lang}
        imageCount={imageCount ?? pending.imageCount}
      />
      <div
        className={cn(
          "chat-shimmer w-full max-h-64 overflow-hidden rounded-chat-lg",
          aspect === "4:5" ? "aspect-[4/5]" : "aspect-square",
          "bg-[linear-gradient(110deg,var(--chat-surface-secondary)_25%,var(--chat-accent-soft)_45%,var(--chat-surface-secondary)_65%)]",
          "bg-[length:200%_100%] animate-[shimmer_1.6s_linear_infinite]",
        )}
      />
      {seconds > 0 ? (
        <p className="text-xs text-chat-text-secondary">
          {t("chat.elapsed", { s: seconds })}
        </p>
      ) : null}
    </div>
  );
}
