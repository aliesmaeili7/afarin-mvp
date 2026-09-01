"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { toDisplayError } from "@/lib/i18n/errors";
import { resolveStaticAssetUrl } from "@/lib/api";
import { chatApiMode } from "@/lib/api/chat";
import { snapshotForThemeId } from "@/lib/api/chat/catalog";
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
import { useChatAccount } from "./useChatAccount";
import { clearChatDraft, readChatDraft, writeChatDraft } from "./chatDraft";

export function ChatWorkspace({ conversationId }: { conversationId: string | null }) {
  const router = useRouter();
  const { t, locale } = useI18n();
  const { toast } = useToast();
  const { account } = useChatAccount();
  const session = useChatSession(conversationId);
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState("");
  const [draftThemeId, setDraftThemeId] = useState<string | null>(null);
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
      session.pendingUser?.id,
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

  useEffect(() => {
    if (conversationId) return;
    const stored = readChatDraft();
    if (!stored) return;
    setDraft(stored.content);
    setDraftThemeId(stored.themeId);
    setCreationAction(stored.creationAction);
  }, [conversationId]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void session.refreshList(search);
    }, 300);
    return () => window.clearTimeout(handle);
  }, [search, session.refreshList]);

  const activeThemeId = conversationId
    ? (session.conversation?.active_theme?.id ?? null)
    : draftThemeId;

  const activeTheme = useMemo(() => {
    if (!activeThemeId) return null;
    return session.themes.find((theme) => theme.id === activeThemeId) ?? null;
  }, [activeThemeId, session.themes]);

  async function navigateIfNew(id: string) {
    if (conversationId !== id) {
      router.replace(`/chat/${id}`);
    }
  }

  function notice(error: unknown) {
    toast(toDisplayError(error, locale), "error");
  }

  async function handleSend() {
    if (
      chatApiMode === "http" &&
      !account.signedIn &&
      (draft.trim() || attachment)
    ) {
      writeChatDraft({
        content: draft,
        themeId: draftThemeId,
        creationAction,
      });
      toast(t("chat.signInToSave"), "info");
      router.push("/login?next=/chat");
      return;
    }
    const language = inferMessageLanguage(draft);
    const input = {
      content: draft,
      attachment,
      skillHint: creationAction,
      referenceArtifactIds: reference ? [reference.id] : undefined,
      language,
      activeTheme: conversationId ? undefined : snapshotForThemeId(draftThemeId),
    };
    const previousDraft = draft;
    const previousAttachment = attachment;
    const previousAction = creationAction;
    const previousReference = reference;
    setDraft("");
    setAttachment(null);
    setReference(null);
    setCreationAction(null);
    pinToBottom();
    const result = await session.send(input, language);
    if (!result) {
      setDraft(previousDraft);
      setAttachment(previousAttachment);
      setCreationAction(previousAction);
      setReference(previousReference);
      toast(t("chat.sendFailed"), "error");
      return;
    }
    clearChatDraft();
    await navigateIfNew(result.id);
  }

  async function handleRetry(artifactId: string) {
    pinToBottom();
    const artifact = session.conversation?.artifacts.find(
      (item) => item.id === artifactId,
    );
    const message = session.conversation?.messages.find(
      (item) => item.id === artifact?.message_id,
    );
    const language = message?.language === "en" ? "en" : "fa";
    try {
      await session.retry(artifactId, language);
    } catch (error) {
      notice(error);
    }
  }

  async function handleTheme(themeId: string | null) {
    if (!conversationId) {
      setDraftThemeId(themeId);
      return;
    }
    try {
      await session.setTheme(themeId);
    } catch (error) {
      notice(error);
    }
  }

  function leaveIfCurrent(id: string) {
    if (shouldLeaveConversation(id, conversationId)) {
      router.push("/chat");
    }
  }

  async function handleCommitRename(id: string, title: string) {
    setRenamingId(null);
    try {
      await session.rename(id, title);
    } catch (error) {
      notice(error);
    }
  }

  async function handleArchive(id: string) {
    try {
      await session.archive(id);
      setArchiveRevision((value) => value + 1);
      leaveIfCurrent(id);
    } catch (error) {
      notice(error);
    }
  }

  async function handleRestore(id: string) {
    try {
      await session.restore(id);
      setArchiveRevision((value) => value + 1);
    } catch (error) {
      notice(error);
    }
  }

  async function handleDeleteConfirmed() {
    const id = deleteId;
    setDeleteId(null);
    if (!id) return;
    try {
      await session.remove(id);
      setArchiveRevision((value) => value + 1);
      leaveIfCurrent(id);
    } catch (error) {
      notice(error);
    }
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
      void session.pin(id).catch(notice);
    },
    onUnpin: (id) => {
      void session.unpin(id).catch(notice);
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

  if (session.notFound && !session.conversationLoading) {
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
            listLoading={session.listLoading}
            listError={session.listError}
            onRetryList={() => void session.refreshList(search)}
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
        listLoading={session.listLoading}
        listError={session.listError}
        onRetryList={() => void session.refreshList(search)}
      />

      <div
        className="flex min-w-0 flex-1 flex-col"
        style={{ paddingBottom: keyboardOffset }}
      >
        <ChatTopBar title={title} onOpenSidebar={() => setMobileSidebar(true)} />
        <ConversationView
          conversation={session.conversation}
          pending={session.pending}
          pendingUser={session.pendingUser}
          loading={session.conversationLoading && Boolean(conversationId)}
          error={session.conversationError && !session.notFound}
          onRetryLoad={session.reloadConversation}
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
          referenceThumb={
            reference
              ? (reference.url ??
                (reference.storage_path
                  ? resolveStaticAssetUrl(reference.storage_path)
                  : null))
              : null
          }
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
        selectedId={activeThemeId}
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
