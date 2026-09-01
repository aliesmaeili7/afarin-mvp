"use client";

import { useEffect, useState } from "react";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { PendingGeneration } from "../useChatSession";

export function GenerationPlaceholder({
  pending,
}: {
  pending: PendingGeneration;
}) {
  const { t } = useI18n();
  const [seconds, setSeconds] = useState(0);

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
      dir={pending.language === "en" ? "ltr" : "rtl"}
      className="flex flex-col gap-3"
    >
      <p className="text-[0.95rem] leading-8 text-chat-text">{t("chat.generating")}</p>
      <div
        className={cn(
          "chat-shimmer h-56 w-full max-w-md overflow-hidden rounded-chat-lg",
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
