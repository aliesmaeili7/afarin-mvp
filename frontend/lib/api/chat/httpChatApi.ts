import { ApiError } from "@/lib/api/types";
import { request } from "@/lib/api/http/request";
import { formatConversationShareText } from "@/features/chat/conversationShare";
import { CHAT_THEMES, snapshotForThemeId } from "./catalog";
import type {
  ChatApi,
  ChatAttachment,
  Conversation,
  ConversationSummary,
  ListConversationsOptions,
  SendMessageInput,
} from "./types";

interface MessagePayload {
  content: string;
  language?: "fa" | "en";
  action_hint?: SendMessageInput["skillHint"];
  active_theme?: SendMessageInput["activeTheme"];
  reference_artifact_ids?: string[];
}

function dataUrlToBlob(dataUrl: string): Blob {
  const [header, data] = dataUrl.split(",");
  const mime = /data:(.*?);/.exec(header)?.[1] ?? "application/octet-stream";
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mime });
}

function attachmentFile(attachment: ChatAttachment | null | undefined): File | Blob | null {
  if (!attachment?.dataUrl) return null;
  const blob = dataUrlToBlob(attachment.dataUrl);
  return new File([blob], attachment.name, {
    type: attachment.mime_type || blob.type,
  });
}

function messageBody(input: SendMessageInput, includeTheme: boolean): MessagePayload {
  const body: MessagePayload = {
    content: input.content,
    language: input.language,
    action_hint: input.skillHint ?? null,
  };
  if (includeTheme) body.active_theme = input.activeTheme ?? null;
  if (input.referenceArtifactIds?.length) {
    body.reference_artifact_ids = input.referenceArtifactIds;
  }
  return body;
}

async function postTurn(
  path: string,
  input: SendMessageInput,
  includeTheme: boolean,
): Promise<Conversation> {
  const file = attachmentFile(input.attachment);
  const payload = messageBody(input, includeTheme);
  if (file) {
    const form = new FormData();
    form.append("payload", JSON.stringify(payload));
    form.append("attachment", file, input.attachment?.name ?? "attachment");
    return hydrate(await request<Conversation>(path, { method: "POST", formData: form }));
  }
  return hydrate(
    await request<Conversation>(path, { method: "POST", body: payload }),
  );
}

function collectPaths(conversation: Conversation): string[] {
  const paths: string[] = [];
  for (const artifact of conversation.artifacts) {
    if (artifact.storage_path) paths.push(artifact.storage_path);
  }
  for (const message of conversation.messages) {
    const path = message.metadata_json?.attachment?.storage_path;
    if (path) paths.push(path);
  }
  return [...new Set(paths)].filter(
    (path) => path.startsWith("supabase://") || path.startsWith("public://"),
  );
}

function publicOrResolved(
  path: string | null | undefined,
  resolved: Record<string, string | null>,
): string | null {
  if (!path) return null;
  if (path.startsWith("data:")) return path;
  if (path.startsWith("public://")) return `/${path.slice("public://".length)}`;
  return resolved[path] ?? null;
}

async function hydrate(conversation: Conversation): Promise<Conversation> {
  const paths = collectPaths(conversation);
  const supabasePaths = paths.filter((path) => path.startsWith("supabase://"));
  const resolved =
    supabasePaths.length > 0
      ? await request<Record<string, string | null>>("/api/assets/resolve", {
          method: "POST",
          body: { paths: supabasePaths },
        })
      : {};
  return {
    ...conversation,
    artifacts: conversation.artifacts.map((artifact) => ({
      ...artifact,
      url: publicOrResolved(artifact.storage_path, resolved),
    })),
    messages: conversation.messages.map((message) => {
      const attachment = message.metadata_json?.attachment;
      if (!attachment?.storage_path) return message;
      return {
        ...message,
        metadata_json: {
          ...message.metadata_json,
          attachment: {
            ...attachment,
            dataUrl: publicOrResolved(attachment.storage_path, resolved) ?? undefined,
          },
        },
      };
    }),
  };
}

async function patchConversation(
  id: string,
  body: Record<string, unknown>,
): Promise<Conversation> {
  return hydrate(
    await request<Conversation>(`/api/chat/conversations/${id}`, {
      method: "PATCH",
      body,
    }),
  );
}

function queryString(options: ListConversationsOptions = {}): string {
  const params = new URLSearchParams();
  if (options.archived) params.set("archived", "true");
  if (options.q?.trim()) params.set("q", options.q.trim());
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const httpChatApi: ChatApi = {
  async createConversation() {
    throw new ApiError(
      "validation_error",
      "گفتگو با اولین پیام ساخته می‌شود.",
    );
  },

  async listConversations(options: ListConversationsOptions = {}) {
    return request<ConversationSummary[]>(
      `/api/chat/conversations${queryString(options)}`,
    );
  },

  async listArchivedConversations() {
    return httpChatApi.listConversations({ archived: true });
  },

  async searchConversations(query, options = {}) {
    return httpChatApi.listConversations({
      archived: options.archived,
      q: query,
    });
  },

  async getConversation(id) {
    return hydrate(
      await request<Conversation>(`/api/chat/conversations/${id}`),
    );
  },

  async sendMessage(conversationId, input) {
    if (input.retryArtifactId && conversationId) {
      const current = await hydrate(
        await request<Conversation>(`/api/chat/conversations/${conversationId}`),
      );
      const artifact = current.artifacts.find(
        (item) => item.id === input.retryArtifactId,
      );
      const messageId = artifact?.message_id;
      if (!messageId) {
        throw new ApiError("validation_error", "این پیام رو نمی‌شه دوباره ساخت.");
      }
      const conversation = await hydrate(
        await request<Conversation>(
          `/api/chat/conversations/${conversationId}/messages/${messageId}/retry`,
          { method: "POST" },
        ),
      );
      return { conversation };
    }
    if (!conversationId) {
      const conversation = await postTurn(
        "/api/chat/conversations",
        input,
        true,
      );
      return { conversation };
    }
    const conversation = await postTurn(
      `/api/chat/conversations/${conversationId}/messages`,
      input,
      false,
    );
    return { conversation };
  },

  async generateImage(conversationId) {
    return httpChatApi.sendMessage(conversationId, {
      content: "",
      skillHint: "general_image",
    });
  },

  async setActiveTheme(conversationId, themeId) {
    return patchConversation(conversationId, {
      active_theme: snapshotForThemeId(themeId),
    });
  },

  async listThemes() {
    return structuredClone(CHAT_THEMES);
  },

  async renameConversation(id, title) {
    return patchConversation(id, { title });
  },

  async deleteConversation(id) {
    await request<void>(`/api/chat/conversations/${id}`, { method: "DELETE" });
  },

  async archiveConversation(id) {
    return patchConversation(id, { archived: true });
  },

  async restoreConversation(id) {
    return patchConversation(id, { archived: false });
  },

  async pinConversation(id) {
    return patchConversation(id, { pinned: true });
  },

  async unpinConversation(id) {
    return patchConversation(id, { pinned: false });
  },

  async shareConversation(id) {
    const conversation = await httpChatApi.getConversation(id);
    return {
      title: conversation.title,
      text: formatConversationShareText(conversation),
      publicUrl: null,
    };
  },
};
