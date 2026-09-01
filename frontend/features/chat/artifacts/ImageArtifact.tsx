"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/components/ui/cn";
import {
  DownloadIcon,
  ImageIcon,
  MoreIcon,
  RefreshIcon,
} from "@/components/ui/icons";
import { useClipboard } from "@/lib/hooks/useClipboard";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { resolveStaticAssetUrl } from "@/lib/api";
import type { ConversationArtifact } from "@/lib/api/chat/types";
import { ChatIconButton } from "../primitives/ChatIconButton";
import { ChatPopover } from "../primitives/ChatPopover";

export function ImageArtifact({
  artifact,
  onRetry,
  onUseAsReference,
}: {
  artifact: ConversationArtifact;
  onRetry?: () => void;
  onUseAsReference?: () => void;
}) {
  const { t } = useI18n();
  const copy = useClipboard();
  const [menuOpen, setMenuOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointer(event: MouseEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [menuOpen]);

  const src =
    artifact.storage_path?.startsWith("data:")
      ? artifact.storage_path
      : resolveStaticAssetUrl(artifact.storage_path);

  if (artifact.status === "failed") {
    return (
      <div data-chat="generation-failed" className="flex max-w-md flex-col gap-3">
        <p className="text-[0.95rem] leading-8 text-chat-text">
          {t("chat.generateFailed")}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-11 w-fit items-center gap-2 rounded-full bg-chat-accent-soft px-4 text-sm font-semibold text-chat-accent"
        >
          <RefreshIcon width={16} height={16} />
          {t("chat.retry")}
        </button>
      </div>
    );
  }

  if (!src) return null;

  const aspectClass =
    artifact.aspect_ratio === "4:5" ? "aspect-[4/5]" : "aspect-square";

  return (
    <figure data-chat="image-artifact" data-aspect={artifact.aspect_ratio} className="max-w-md">
      <div
        className={cn(
          "overflow-hidden rounded-chat-lg bg-chat-surface-secondary shadow-chat-soft",
          aspectClass,
        )}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt=""
          width={artifact.aspect_ratio === "4:5" ? 800 : 800}
          height={artifact.aspect_ratio === "4:5" ? 1000 : 800}
          loading="lazy"
          className="size-full object-contain"
        />
      </div>
      <div className="relative mt-2 flex items-center gap-1" ref={wrapRef}>
        <a
          href={src}
          download
          className="inline-flex h-11 items-center gap-2 rounded-full px-3 text-sm font-semibold text-chat-text-secondary hover:bg-chat-surface-secondary hover:text-chat-text"
        >
          <DownloadIcon width={16} height={16} />
          {t("chat.download")}
        </a>
        <button
          type="button"
          onClick={onUseAsReference}
          className="inline-flex h-11 items-center gap-2 rounded-full px-3 text-sm font-semibold text-chat-text-secondary hover:bg-chat-surface-secondary hover:text-chat-text"
        >
          <ImageIcon width={16} height={16} />
          {t("chat.useAsReference")}
        </button>
        <ChatIconButton
          label={t("chat.moreActions")}
          onClick={() => setMenuOpen((open) => !open)}
          className="size-11"
        >
          <MoreIcon width={18} height={18} />
        </ChatIconButton>
        <ChatPopover
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          className="start-auto end-0 min-w-40"
        >
          <button
            type="button"
            role="menuitem"
            className="flex h-11 w-full items-center rounded-chat-md px-3 text-sm text-chat-text hover:bg-chat-surface-secondary"
            onClick={() => {
              void copy(src, t("chat.copyLink"));
              setMenuOpen(false);
            }}
          >
            {t("chat.copyLink")}
          </button>
        </ChatPopover>
      </div>
    </figure>
  );
}
