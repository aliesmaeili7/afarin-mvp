"use client";

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { PlusIcon, SendIcon } from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ChatAttachment, ChatTheme } from "@/lib/api/chat/types";
import { inferMessageDir } from "./chatDirection";
import { shouldSendOnEnter } from "./composerKeys";
import { ActiveThemeChip } from "./ActiveThemeChip";
import { ChatPlusMenu } from "./ChatPlusMenu";
import { ComposerAttachmentStrip } from "./ComposerAttachmentStrip";
import { CreationActionChip } from "./CreationActionChip";
import { ChatIconButton } from "./primitives/ChatIconButton";
import type { CreationAction } from "./plusMenu";

export function ChatComposer({
  draft,
  onDraft,
  attachment,
  onAttach,
  onRemoveAttachment,
  theme,
  onRemoveTheme,
  referenceLabel,
  referenceThumb,
  onRemoveReference,
  creationAction,
  onSelectCreation,
  onRemoveCreation,
  disabled,
  onSend,
  onOpenTheme,
  sheetMenu,
}: {
  draft: string;
  onDraft: (value: string) => void;
  attachment: ChatAttachment | null;
  onAttach: (file: File) => void;
  onRemoveAttachment: () => void;
  theme: ChatTheme | null;
  onRemoveTheme: () => void;
  referenceLabel: string | null;
  referenceThumb?: string | null;
  onRemoveReference: () => void;
  creationAction: CreationAction | null;
  onSelectCreation: (action: CreationAction) => void;
  onRemoveCreation: () => void;
  disabled: boolean;
  onSend: () => void;
  onOpenTheme: () => void;
  sheetMenu: boolean;
}) {
  const { t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [coarse, setCoarse] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const media = window.matchMedia("(pointer: coarse)");
    const sync = () => setCoarse(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`;
  }, [draft]);

  const canSend =
    Boolean(draft.trim() || attachment || creationAction) && !disabled;
  const dir = inferMessageDir(draft);

  function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    if (!canSend) return;
    onSend();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      shouldSendOnEnter(
        {
          key: event.key,
          shiftKey: event.shiftKey,
          isComposing: event.nativeEvent.isComposing,
        },
        coarse,
      )
    ) {
      event.preventDefault();
      handleSubmit();
    }
  }

  return (
    <form
      data-chat="composer"
      onSubmit={handleSubmit}
      className="mx-auto w-full max-w-[52rem] px-3 pb-safe pt-2 sm:px-4"
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onAttach(file);
          event.target.value = "";
        }}
      />
      <div
        className={cn(
          "relative rounded-chat-xl border border-chat-border-subtle bg-chat-surface-elevated",
          "px-2 py-2 shadow-chat-soft",
        )}
      >
        {(creationAction || theme || attachment || referenceLabel) && (
          <div className="flex flex-wrap items-center gap-2 px-2 pb-2">
            {creationAction ? (
              <CreationActionChip
                action={creationAction}
                onRemove={onRemoveCreation}
              />
            ) : null}
            {theme ? <ActiveThemeChip theme={theme} onRemove={onRemoveTheme} /> : null}
            {attachment ? (
              <ComposerAttachmentStrip
                attachment={attachment}
                onRemove={onRemoveAttachment}
              />
            ) : null}
            {referenceLabel ? (
              <span
                data-chat="reference-chip"
                className="inline-flex h-9 max-w-full items-center gap-2 rounded-full bg-chat-surface-secondary pe-1 ps-1.5 text-xs font-semibold text-chat-text"
              >
                {referenceThumb ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={referenceThumb}
                    alt=""
                    width={28}
                    height={28}
                    className="size-7 shrink-0 rounded-full object-cover"
                  />
                ) : null}
                <span className="truncate ps-1">{referenceLabel}</span>
                <ChatIconButton
                  label={t("chat.referenceRemove")}
                  onClick={onRemoveReference}
                  className="size-8"
                >
                  ×
                </ChatIconButton>
              </span>
            ) : null}
          </div>
        )}
        <div className="flex items-end gap-1">
          <div className="relative">
            <ChatIconButton
              label={t("chat.plusMenu")}
              data-chat="plus"
              active={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <PlusIcon width={20} height={20} />
            </ChatIconButton>
            <ChatPlusMenu
              open={menuOpen}
              onClose={() => setMenuOpen(false)}
              sheet={sheetMenu}
              onSelectCreation={onSelectCreation}
              onUpload={() => fileRef.current?.click()}
              onTheme={onOpenTheme}
            />
          </div>
          <textarea
            ref={textareaRef}
            rows={1}
            dir={dir}
            value={draft}
            disabled={disabled}
            onChange={(event) => onDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("chat.composerPlaceholder")}
            className="max-h-42 min-h-11 flex-1 resize-none bg-transparent py-2.5 text-[0.95rem] leading-7 text-chat-text outline-none placeholder:text-chat-text-secondary"
          />
          <button
            type="submit"
            data-chat="send"
            disabled={!canSend}
            aria-label={t("chat.send")}
            className={cn(
              "grid size-11 shrink-0 place-items-center rounded-full chat-motion",
              canSend
                ? "bg-chat-accent text-white"
                : "bg-chat-surface-secondary text-chat-text-secondary",
            )}
          >
            <SendIcon width={18} height={18} className="rtl:rotate-180" />
          </button>
        </div>
      </div>
    </form>
  );
}
