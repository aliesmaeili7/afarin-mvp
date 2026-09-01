"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { chatApi } from "@/lib/api/chat";
import type {
  ChatAttachment,
  ChatTheme,
  Conversation,
  ConversationSummary,
  SendMessageInput,
} from "@/lib/api/chat/types";

export interface PendingGeneration {
  startedAt: number;
  language: "fa" | "en";
}

export function useChatSession(conversationId: string | null) {
  const [summaries, setSummaries] = useState<ConversationSummary[]>([]);
  const [themes, setThemes] = useState<ChatTheme[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [pending, setPending] = useState<PendingGeneration | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void chatApi.listConversations().then((items) => {
      if (!cancelled) setSummaries(items);
    });
    void chatApi.listThemes().then((items) => {
      if (!cancelled) setThemes(items);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    void chatApi.getConversation(conversationId).then(
      (item) => {
        if (cancelled) return;
        setConversation(item);
        setNotFound(false);
      },
      () => {
        if (cancelled) return;
        setConversation(null);
        setNotFound(true);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  const refreshList = useCallback(async () => {
    setSummaries(await chatApi.listConversations());
  }, []);

  const applyResult = useCallback(
    async (next: Conversation) => {
      setConversation(next);
      await refreshList();
      return next;
    },
    [refreshList],
  );

  const ensureConversation = useCallback(async () => {
    if (conversation) return conversation;
    const created = await chatApi.createConversation();
    await refreshList();
    setConversation(created);
    return created;
  }, [conversation, refreshList]);

  const runTurn = useCallback(
    async (
      input: SendMessageInput,
      language: "fa" | "en",
      start: (id: string) => Promise<{ conversation: Conversation }>,
    ) => {
      if (busy) return null;
      setBusy(true);
      setPending({ startedAt: Date.now(), language });
      try {
        const current = await ensureConversation();
        const result = await start(current.id);
        setPending(null);
        await applyResult(result.conversation);
        return result.conversation;
      } catch {
        setPending(null);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [applyResult, busy, ensureConversation],
  );

  const send = useCallback(
    async (input: SendMessageInput, language: "fa" | "en") => {
      return runTurn(input, language, (id) => chatApi.sendMessage(id, input));
    },
    [runTurn],
  );

  const generateImage = useCallback(
    async (language: "fa" | "en") => {
      return runTurn({ content: "", generateImage: true }, language, (id) =>
        chatApi.generateImage(id),
      );
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
      const current = await ensureConversation();
      const next = await chatApi.setActiveTheme(current.id, themeId);
      await applyResult(next);
      return next;
    },
    [applyResult, ensureConversation],
  );

  const rename = useCallback(
    async (id: string, title: string) => {
      const next = await chatApi.renameConversation(id, title);
      if (conversation?.id === id) setConversation(next);
      await refreshList();
      return next;
    },
    [conversation?.id, refreshList],
  );

  const pin = useCallback(
    async (id: string) => {
      const next = await chatApi.pinConversation(id);
      if (conversation?.id === id) setConversation(next);
      await refreshList();
      return next;
    },
    [conversation?.id, refreshList],
  );

  const unpin = useCallback(
    async (id: string) => {
      const next = await chatApi.unpinConversation(id);
      if (conversation?.id === id) setConversation(next);
      await refreshList();
      return next;
    },
    [conversation?.id, refreshList],
  );

  const archive = useCallback(
    async (id: string) => {
      const next = await chatApi.archiveConversation(id);
      if (conversation?.id === id) setConversation(next);
      await refreshList();
      return next;
    },
    [conversation?.id, refreshList],
  );

  const restore = useCallback(
    async (id: string) => {
      const next = await chatApi.restoreConversation(id);
      if (conversation?.id === id) setConversation(next);
      await refreshList();
      return next;
    },
    [conversation?.id, refreshList],
  );

  const remove = useCallback(
    async (id: string) => {
      await chatApi.deleteConversation(id);
      if (conversation?.id === id) setConversation(null);
      await refreshList();
    },
    [conversation?.id, refreshList],
  );

  return {
    summaries,
    themes,
    conversation,
    pending,
    notFound,
    busy,
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
      resolve({ name: file.name, dataUrl: String(reader.result) });
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
