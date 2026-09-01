"use client";

import { useEffect, useState } from "react";
import { SparkleIcon } from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import type { ChatLanguage } from "@/lib/api/chat/types";
import { activityCopy } from "../chatActivity";
import { messageDirFromLanguage } from "../chatDirection";

export function ChatActivityIndicator({
  phase,
  language,
  imageCount,
}: {
  phase: string | null | undefined;
  language: ChatLanguage | null | undefined;
  imageCount?: number;
}) {
  const text = activityCopy(phase, language, { imageCount });
  const [shown, setShown] = useState(text);
  const [dimmed, setDimmed] = useState(false);

  useEffect(() => {
    if (text === shown) return;
    setDimmed(true);
    const id = window.setTimeout(() => {
      setShown(text);
      setDimmed(false);
    }, 160);
    return () => window.clearTimeout(id);
  }, [text, shown]);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-chat="activity"
      data-chat-phase={phase || "thinking"}
      dir={messageDirFromLanguage(language)}
      className="flex max-w-md items-center gap-2 text-[0.95rem] leading-8 text-chat-text"
    >
      <SparkleIcon
        width={16}
        height={16}
        className="chat-motion size-4 shrink-0 text-chat-accent motion-safe:animate-pulse"
      />
      <span
        className={cn(
          "chat-motion min-w-0 transition-opacity duration-200",
          dimmed && "opacity-40",
        )}
      >
        {shown}
      </span>
    </div>
  );
}
