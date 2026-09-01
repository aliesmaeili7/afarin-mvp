"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type {
  ChatAttachment,
  ConversationArtifact,
} from "@/lib/api/chat/types";
import { inferMessageLanguage } from "./chatDirection";
import type { CreationAction } from "./plusMenu";
import { ChatComposer } from "./ChatComposer";
import { ChatSidebar } from "./ChatSidebar";
import { ChatTopBar } from "./ChatTopBar";
import { ConversationView } from "./ConversationView";
import { ThemePickerSheet } from "./ThemePickerSheet";
import { ChatArchiveSheet } from "./ChatArchiveSheet";
import { ChatConfirmDialog } from "./ChatConfirmDialog";
import { ChatShareSheet } from "./ChatShareSheet";
import { ChatSidebarSheet } from "./mobile/ChatSidebarSheet";
import { shouldLeaveConversation } from "./conversationActions";
import type { ConversationControls } from "./history/conversationControls";
import { useStickToBottom } from "./useStickToBottom";
import {
  fileToAttachment,
  useChatSession,
  useMobileSheet,
  useSidebarCollapsed,
} from "./useChatSession";

export function ChatWorkspace({ conversationId }: { conversationId: string | null }) {
  const router = useRouter();
  const { t, locale } = useI18n();
  const session = useChatSession(conversationId);
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState("");
  const [attachment, setAttachment] = useState<ChatAttachment | null>(null);
  const [reference, setReference] = useState<ConversationArtifact | null>(null);
  const [creationAction, setCreationAction] = useState<CreationAction | null>(
    null,
  );
  const [themeOpen, setThemeOpen] = useState(false);
  const [mobileSidebar, setMobileSidebar] = useState(false);
  const [collapsed, setCollapsed] = useSidebarCollapsed();
  const sheetMenu = useMobileSheet();
  const [keyboardOffset, setKeyboardOffset] = useState(0);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [shareId, setShareId] = useState<string | null>(null);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveRevision, setArchiveRevision] = useState(0);

  const { scrollerRef, onScroll, showJump, jumpToLatest, pinToBottom } =
    useStickToBottom([
      session.conversation?.messages.length,
      session.pending?.startedAt,
    ]);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    const sync = () => {
      const offset = Math.max(
        0,
        window.innerHeight - viewport.height - viewport.offsetTop,
      );
      setKeyboardOffset(offset);
    };
    viewport.addEventListener("resize", sync);
    viewport.addEventListener("scroll", sync);
    return () => {
      viewport.removeEventListener("resize", sync);
      viewport.removeEventListener("scroll", sync);
    };
  }, []);

  const activeTheme = useMemo(() => {
    const id = session.conversation?.active_theme_id ?? null;
    if (!id) return null;
    return session.themes.find((theme) => theme.id === id) ?? null;
  }, [session.conversation?.active_theme_id, session.themes]);

  async function navigateIfNew(id: string) {
    if (conversationId !== id) {
      router.replace(`/chat/${id}`);
    }
  }

  async function handleSend() {
    const language = inferMessageLanguage(draft);
    const input = {
      content: draft,
      attachment,
      generateImage: Boolean(reference),
      skillHint: creationAction,
    };
    setDraft("");
    setAttachment(null);
    setReference(null);
    setCreationAction(null);
    pinToBottom();
    const result = await session.send(input, language);
    if (result) await navigateIfNew(result.id);
  }

  async function handleRetry(artifactId: string) {
    pinToBottom();
    await session.retry(artifactId, locale);
  }

  async function handleTheme(themeId: string | null) {
    const result = await session.setTheme(themeId);
    if (result) await navigateIfNew(result.id);
  }

  function leaveIfCurrent(id: string) {
    if (shouldLeaveConversation(id, conversationId)) {
      router.push("/chat");
    }
  }

  async function handleCommitRename(id: string, title: string) {
    setRenamingId(null);
    await session.rename(id, title);
  }

  async function handleArchive(id: string) {
    await session.archive(id);
    setArchiveRevision((value) => value + 1);
    leaveIfCurrent(id);
  }

  async function handleRestore(id: string) {
    await session.restore(id);
    setArchiveRevision((value) => value + 1);
  }

  async function handleDeleteConfirmed() {
    const id = deleteId;
    setDeleteId(null);
    if (!id) return;
    await session.remove(id);
    setArchiveRevision((value) => value + 1);
    leaveIfCurrent(id);
  }

  const controls: ConversationControls = {
    menuId,
    renamingId,
    onMenuId: setMenuId,
    onStartRename: (id) => {
      setMenuId(null);
      setRenamingId(id);
    },
    onCommitRename: (id, title) => {
      void handleCommitRename(id, title);
    },
    onCancelRename: () => setRenamingId(null),
    onPin: (id) => {
      void session.pin(id);
    },
    onUnpin: (id) => {
      void session.unpin(id);
    },
    onArchive: (id) => {
      void handleArchive(id);
    },
    onShare: setShareId,
    onRequestDelete: setDeleteId,
    onOpenArchive: () => setArchiveOpen(true),
  };

  const title =
    session.conversation?.title ??
    (conversationId ? t("chat.untitled") : t("chat.emptyBrand"));

  if (session.notFound) {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-3 bg-chat-bg text-chat-text">
        <p>{t("chat.notFound")}</p>
        <button
          type="button"
          onClick={() => router.push("/chat")}
          className="h-11 rounded-full bg-chat-accent px-5 text-sm font-semibold text-white"
        >
          {t("chat.backHome")}
        </button>
      </div>
    );
  }

  return (
    <div data-chat="workspace" className="flex h-dvh overflow-hidden bg-chat-bg text-chat-text">
      {sheetMenu ? null : (
        <div className="h-full">
          <ChatSidebar
            summaries={session.summaries}
            activeId={conversationId}
            search={search}
            onSearch={setSearch}
            collapsed={collapsed}
            onToggleCollapsed={() => setCollapsed(!collapsed)}
            controls={controls}
          />
        </div>
      )}

      <ChatSidebarSheet
        open={mobileSidebar}
        onClose={() => setMobileSidebar(false)}
        summaries={session.summaries}
        activeId={conversationId}
        search={search}
        onSearch={setSearch}
        controls={controls}
      />

      <div
        className="flex min-w-0 flex-1 flex-col"
        style={{ paddingBottom: keyboardOffset }}
      >
        <ChatTopBar title={title} onOpenSidebar={() => setMobileSidebar(true)} />
        <ConversationView
          conversation={session.conversation}
          pending={session.pending}
          onRetry={(id) => void handleRetry(id)}
          onUseAsReference={setReference}
          onInsertShortcut={setDraft}
          scrollerRef={scrollerRef}
          onScroll={onScroll}
          showJump={showJump}
          onJump={jumpToLatest}
        />
        <ChatComposer
          draft={draft}
          onDraft={setDraft}
          attachment={attachment}
          onAttach={(file) => {
            void fileToAttachment(file).then(setAttachment);
          }}
          onRemoveAttachment={() => setAttachment(null)}
          theme={activeTheme}
          onRemoveTheme={() => void handleTheme(null)}
          referenceLabel={reference ? t("chat.referenceChip") : null}
          onRemoveReference={() => setReference(null)}
          creationAction={creationAction}
          onSelectCreation={setCreationAction}
          onRemoveCreation={() => setCreationAction(null)}
          disabled={session.busy}
          onSend={() => void handleSend()}
          onOpenTheme={() => setThemeOpen(true)}
          sheetMenu={sheetMenu}
        />
      </div>

      <ThemePickerSheet
        open={themeOpen}
        onClose={() => setThemeOpen(false)}
        themes={session.themes}
        selectedId={session.conversation?.active_theme_id ?? null}
        onSelect={(id) => void handleTheme(id)}
      />
      <ChatShareSheet conversationId={shareId} onClose={() => setShareId(null)} />
      <ChatArchiveSheet
        open={archiveOpen}
        revision={archiveRevision}
        onClose={() => setArchiveOpen(false)}
        onRestore={handleRestore}
        onDelete={setDeleteId}
      />
      <ChatConfirmDialog
        open={Boolean(deleteId)}
        onClose={() => setDeleteId(null)}
        title={t("chat.deleteTitle")}
        body={t("chat.deleteBody")}
        confirmLabel={t("chat.delete")}
        destructive
        dataChat="delete-confirm"
        onConfirm={() => void handleDeleteConfirmed()}
      />
    </div>
  );
}
