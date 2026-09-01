"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { chatApi, chatApiMode } from "@/lib/api/chat";
import type {
  ChatAttachment,
  ChatTheme,
  Conversation,
  ConversationMessage,
  ConversationSummary,
  SendMessageInput,
} from "@/lib/api/chat/types";
import { useSessionStore } from "@/features/auth/sessionStore";
import { preparingPhaseFor, type ChatActivityPhase } from "./chatActivity";

export interface PendingGeneration {
  startedAt: number;
  language: "fa" | "en";
  phase?: ChatActivityPhase;
  aspectRatio?: "1:1" | "4:5" | "9:16";
  expectsImage?: boolean;
  imageCount?: number;
}

function conversationIsGenerating(conversation: Conversation | null): boolean {
  if (!conversation) return false;
  if (conversation.artifacts.some((item) => item.status === "generating")) {
    return true;
  }
  return conversation.messages.some(
    (item) => item.metadata_json?.status === "generating",
  );
}

export function useChatSession(conversationId: string | null) {
  const userId = useSessionStore((state) => state.session?.user.id ?? null);
  const sessionLoaded = useSessionStore((state) => state.loaded);
  const [summaries, setSummaries] = useState<ConversationSummary[]>([]);
  const [themes, setThemes] = useState<ChatTheme[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [pending, setPending] = useState<PendingGeneration | null>(null);
  const [pendingUser, setPendingUser] = useState<ConversationMessage | null>(
    null,
  );
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [listError, setListError] = useState(false);
  const [conversationError, setConversationError] = useState(false);
  const conversationRef = useRef<Conversation | null>(null);
  conversationRef.current = conversation;

  const refreshList = useCallback(async (query = "") => {
    setListError(false);
    try {
      const items = query.trim()
        ? await chatApi.searchConversations(query)
        : await chatApi.listConversations();
      setSummaries(items);
    } catch {
      setListError(true);
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void chatApi.listThemes().then((items) => {
      if (!cancelled) setThemes(items);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sessionLoaded && chatApiMode === "http") return;
    setListLoading(true);
    void refreshList();
  }, [refreshList, userId, sessionLoaded]);

  const loadConversation = useCallback(async (id: string) => {
    setConversationError(false);
    setNotFound(false);
    if (conversationRef.current?.id !== id) setConversationLoading(true);
    try {
      const item = await chatApi.getConversation(id);
      setConversation(item);
      setNotFound(false);
    } catch {
      setConversation(null);
      setNotFound(true);
      setConversationError(true);
    } finally {
      setConversationLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!conversationId) {
      setConversation(null);
      setNotFound(false);
      setConversationLoading(false);
      setPendingUser(null);
      return;
    }
    void loadConversation(conversationId);
  }, [conversationId, userId, loadConversation]);

  const generating = conversationIsGenerating(conversation);

  useEffect(() => {
    if (!conversationId || !generating) return;
    let cancelled = false;
    const started = Date.now();
    const capMs = 180_000;
    const id = conversationId;

    async function tick() {
      if (cancelled) return;
      if (Date.now() - started > capMs) {
        setPending(null);
        return;
      }
      try {
        const next = await chatApi.getConversation(id);
        if (cancelled) return;
        setConversation(next);
        if (!conversationIsGenerating(next)) {
          setPending(null);
          await refreshList();
          return;
        }
      } catch {
        /* keep polling */
      }
      timer = window.setTimeout(tick, 1500);
    }

    let timer = window.setTimeout(tick, 1500);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [conversationId, generating, refreshList]);

  const applyResult = useCallback(
    async (next: Conversation) => {
      setConversation(next);
      setPendingUser(null);
      await refreshList();
      return next;
    },
    [refreshList],
  );

  const runTurn = useCallback(
    async (
      input: SendMessageInput,
      language: "fa" | "en",
      start: (id: string | null) => Promise<{ conversation: Conversation }>,
    ) => {
      if (busy) return null;
      setBusy(true);
      const expectsImage = Boolean(
        input.generateImage || input.retryArtifactId || input.skillHint,
      );
      let phase = preparingPhaseFor(
        input.skillHint ?? (input.generateImage ? "general_image" : null),
      );
      if (input.retryArtifactId && conversationRef.current) {
        const current = conversationRef.current;
        const artifact = current.artifacts.find(
          (item) => item.id === input.retryArtifactId,
        );
        const source = current.messages.find(
          (item) => item.id === artifact?.message_id,
        );
        const route =
          typeof source?.metadata_json?.route === "string"
            ? source.metadata_json.route
            : null;
        phase = preparingPhaseFor(route);
      }
      const startedAt = Date.now();
      setPending({
        startedAt,
        language,
        phase: expectsImage ? phase : "thinking",
        expectsImage,
        aspectRatio: input.skillHint === "advertising" ? "4:5" : "1:1",
      });
      const optimistic: ConversationMessage = {
        id: `pending-${Date.now()}`,
        conversation_id: conversation?.id ?? "draft",
        role: "user",
        content: input.content,
        language,
        created_at: new Date().toISOString(),
        pending: true,
        metadata_json: input.attachment
          ? { attachment: input.attachment }
          : input.skillHint
            ? { explicit_skill_hint: input.skillHint }
            : undefined,
      };
      setPendingUser(optimistic);
      try {
        const result = await start(conversation?.id ?? conversationId);
        const next = result.conversation;
        if (conversationIsGenerating(next)) {
          const assistant = [...next.messages]
            .reverse()
            .find((item) => item.role === "assistant");
          const nextPhase =
            typeof assistant?.metadata_json?.activity_phase === "string"
              ? (assistant.metadata_json.activity_phase as ChatActivityPhase)
              : phase;
          const generating = next.artifacts.find(
            (item) => item.status === "generating",
          );
          setPending({
            startedAt,
            language: assistant?.language === "en" ? "en" : language,
            phase: nextPhase,
            expectsImage: true,
            aspectRatio: generating?.aspect_ratio ?? "1:1",
            imageCount:
              Number(assistant?.metadata_json?.requested_image_count) || 1,
          });
        } else {
          setPending(null);
        }
        await applyResult(next);
        return next;
      } catch {
        setPending(null);
        setPendingUser(null);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [applyResult, busy, conversation?.id, conversationId],
  );

  const send = useCallback(
    async (input: SendMessageInput, language: "fa" | "en") => {
      return runTurn(input, language, (id) => chatApi.sendMessage(id, input));
    },
    [runTurn],
  );

  const generateImage = useCallback(
    async (language: "fa" | "en") => {
      return runTurn({ content: "", generateImage: true }, language, (id) => {
        if (!id) return chatApi.sendMessage(null, { content: "", generateImage: true });
        return chatApi.generateImage(id);
      });
    },
    [runTurn],
  );

  const retry = useCallback(
    async (artifactId: string, language: "fa" | "en") => {
      return runTurn(
        { content: "", generateImage: true, retryArtifactId: artifactId },
        language,
        (id) =>
          chatApi.sendMessage(id, {
            content: "",
            generateImage: true,
            retryArtifactId: artifactId,
          }),
      );
    },
    [runTurn],
  );

  const setTheme = useCallback(
    async (themeId: string | null) => {
      if (!conversationId || !conversation) return null;
      const previous = conversation;
      const previousList = summaries;
      const snapshot =
        themes.find((theme) => theme.id === themeId) ?? null;
      setConversation({
        ...conversation,
        active_theme: snapshot
          ? {
              id: snapshot.id,
              source: "chat_catalog",
              name: snapshot.name,
              style_json: {},
            }
          : null,
      });
      try {
        const next = await chatApi.setActiveTheme(conversationId, themeId);
        await applyResult(next);
        return next;
      } catch (error) {
        setConversation(previous);
        setSummaries(previousList);
        throw error;
      }
    },
    [applyResult, conversation, conversationId, summaries, themes],
  );

  const mutateSummary = useCallback(
    async (
      id: string,
      optimistic: Partial<ConversationSummary>,
      run: () => Promise<Conversation>,
    ) => {
      const previous = summaries;
      setSummaries((current) =>
        current.map((item) =>
          item.id === id ? { ...item, ...optimistic } : item,
        ),
      );
      try {
        const next = await run();
        if (conversation?.id === id) setConversation(next);
        await refreshList();
        return next;
      } catch (error) {
        setSummaries(previous);
        throw error;
      }
    },
    [conversation?.id, refreshList, summaries],
  );

  const rename = useCallback(
    async (id: string, title: string) => {
      return mutateSummary(id, { title }, () =>
        chatApi.renameConversation(id, title),
      );
    },
    [mutateSummary],
  );

  const pin = useCallback(
    async (id: string) => {
      return mutateSummary(
        id,
        { pinned: true, pinned_at: new Date().toISOString(), archived: false },
        () => chatApi.pinConversation(id),
      );
    },
    [mutateSummary],
  );

  const unpin = useCallback(
    async (id: string) => {
      return mutateSummary(id, { pinned: false, pinned_at: null }, () =>
        chatApi.unpinConversation(id),
      );
    },
    [mutateSummary],
  );

  const archive = useCallback(
    async (id: string) => {
      return mutateSummary(id, { archived: true, pinned: false }, () =>
        chatApi.archiveConversation(id),
      );
    },
    [mutateSummary],
  );

  const restore = useCallback(
    async (id: string) => {
      return mutateSummary(id, { archived: false }, () =>
        chatApi.restoreConversation(id),
      );
    },
    [mutateSummary],
  );

  const remove = useCallback(
    async (id: string) => {
      const previous = summaries;
      setSummaries((current) => current.filter((item) => item.id !== id));
      try {
        await chatApi.deleteConversation(id);
        if (conversation?.id === id) setConversation(null);
        await refreshList();
      } catch (error) {
        setSummaries(previous);
        throw error;
      }
    },
    [conversation?.id, refreshList, summaries],
  );

  return {
    summaries,
    themes,
    conversation,
    pending,
    pendingUser,
    notFound,
    busy,
    listLoading,
    conversationLoading,
    listError,
    conversationError,
    send,
    generateImage,
    retry,
    setTheme,
    rename,
    pin,
    unpin,
    archive,
    restore,
    remove,
    refreshList,
    reloadConversation: conversationId
      ? () => loadConversation(conversationId)
      : undefined,
  };
}

const SIDEBAR_KEY = "afarin:chat-sidebar-collapsed";

const sidebarCollapsed = {
  value: false,
  listeners: new Set<() => void>(),
};

function emitSidebar(): void {
  sidebarCollapsed.listeners.forEach((listener) => listener());
}

let sidebarHydrated = false;

function subscribeSidebar(listener: () => void): () => void {
  if (!sidebarHydrated && typeof window !== "undefined") {
    sidebarCollapsed.value = window.localStorage.getItem(SIDEBAR_KEY) === "1";
    sidebarHydrated = true;
  }
  sidebarCollapsed.listeners.add(listener);
  return () => {
    sidebarCollapsed.listeners.delete(listener);
  };
}

export function useSidebarCollapsed(): [boolean, (next: boolean) => void] {
  const collapsed = useSyncExternalStore(
    subscribeSidebar,
    () => sidebarCollapsed.value,
    () => false,
  );

  const setCollapsed = useCallback((next: boolean) => {
    sidebarCollapsed.value = next;
    window.localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
    emitSidebar();
  }, []);

  return [collapsed, setCollapsed];
}

export function useMobileSheet(): boolean {
  return useSyncExternalStore(
    (listener) => {
      const media = window.matchMedia("(max-width: 767px)");
      media.addEventListener("change", listener);
      return () => media.removeEventListener("change", listener);
    },
    () => window.matchMedia("(max-width: 767px)").matches,
    () => false,
  );
}

export function fileToAttachment(file: File): Promise<ChatAttachment> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve({
        name: file.name,
        dataUrl: String(reader.result),
        mime_type: file.type,
      });
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
