"use client";

import type { RefObject } from "react";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import type {
  Conversation,
  ConversationArtifact,
} from "@/lib/api/chat/types";
import { AssistantMessage } from "./AssistantMessage";
import { UserMessage } from "./UserMessage";
import { GenerationPlaceholder } from "./artifacts/GenerationPlaceholder";
import type { PendingGeneration } from "./useChatSession";

const SHORTCUTS: { label: TranslationKey; insert: TranslationKey }[] = [
  { label: "chat.shortcutAd", insert: "chat.shortcutAdInsert" },
  { label: "chat.shortcutEdu", insert: "chat.shortcutEduInsert" },
  { label: "chat.shortcutImage", insert: "chat.shortcutImageInsert" },
  { label: "chat.shortcutCaption", insert: "chat.shortcutCaptionInsert" },
];

export function ConversationView({
  conversation,
  pending,
  onRetry,
  onUseAsReference,
  onInsertShortcut,
  scrollerRef,
  onScroll,
  showJump,
  onJump,
}: {
  conversation: Conversation | null;
  pending: PendingGeneration | null;
  onRetry: (artifactId: string) => void;
  onUseAsReference: (artifact: ConversationArtifact) => void;
  onInsertShortcut: (text: string) => void;
  scrollerRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
  showJump: boolean;
  onJump: () => void;
}) {
  const { t } = useI18n();
  const empty = !conversation || conversation.messages.length === 0;

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollerRef}
        onScroll={onScroll}
        className="h-full overflow-y-auto px-4"
      >
        <div className="mx-auto flex min-h-full w-full max-w-[52rem] flex-col gap-6 py-8">
          {empty && !pending ? (
            <EmptyState onInsertShortcut={onInsertShortcut} />
          ) : (
            <>
              {conversation?.messages.map((message) =>
                message.role === "user" ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AssistantMessage
                    key={message.id}
                    message={message}
                    artifacts={conversation.artifacts}
                    onRetry={onRetry}
                    onUseAsReference={onUseAsReference}
                  />
                ),
              )}
              {pending ? <GenerationPlaceholder pending={pending} /> : null}
            </>
          )}
        </div>
      </div>
      {showJump ? (
        <button
          type="button"
          data-chat="jump-latest"
          onClick={onJump}
          className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full bg-chat-surface px-4 py-2 text-xs font-semibold text-chat-text shadow-chat-soft"
        >
          {t("chat.jumpToLatest")}
        </button>
      ) : null}
    </div>
  );
}

function EmptyState({
  onInsertShortcut,
}: {
  onInsertShortcut: (text: string) => void;
}) {
  const { t } = useI18n();
  return (
    <div
      data-chat="empty"
      className="flex flex-1 flex-col items-center justify-center gap-6 py-16 text-center"
    >
      <div>
        <p className="text-3xl font-extrabold tracking-tight text-chat-text">
          {t("chat.emptyBrand")}
        </p>
        <p className="mt-2 text-base text-chat-text-secondary">
          {t("chat.emptyPrompt")}
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {SHORTCUTS.map((item) => (
          <button
            key={item.label}
            type="button"
            onClick={() => onInsertShortcut(t(item.insert))}
            className="h-11 rounded-full border border-chat-border-subtle bg-chat-surface px-4 text-sm font-semibold text-chat-text hover:bg-chat-surface-secondary"
          >
            {t(item.label)}
          </button>
        ))}
      </div>
    </div>
  );
}
