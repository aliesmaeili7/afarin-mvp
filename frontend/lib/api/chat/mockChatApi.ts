import { inferMessageLanguage } from "@/features/chat/chatDirection";
import { formatConversationShareText } from "@/features/chat/conversationShare";
import { CHAT_THEMES, snapshotForThemeId } from "./catalog";
import { createSeedConversations } from "./mockChatData";
import type {
  ArtifactAspect,
  ChatApi,
  ChatLanguage,
  ChatTurnResult,
  Conversation,
  ConversationSharePayload,
  ConversationSummary,
  ListConversationsOptions,
  SendMessageInput,
} from "./types";

const SQUARE = "public://mock/chat/square.svg";
const PORTRAIT = "public://mock/chat/portrait.svg";

let delayMs = 900;
let seq = 100;
let conversations = createSeedConversations();

export function setChatMockDelay(ms: number): void {
  delayMs = ms;
}

export function resetChatMock(): void {
  delayMs = 0;
  seq = 100;
  conversations = createSeedConversations();
}

export function restoreChatMockDelay(): void {
  delayMs = 900;
}

function nextId(prefix: string): string {
  seq += 1;
  return `${prefix}-${seq}`;
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

async function pause(): Promise<void> {
  if (delayMs <= 0) return;
  await new Promise((resolve) => setTimeout(resolve, delayMs));
}

function requireConversation(id: string): Conversation {
  const found = conversations.find((item) => item.id === id);
  if (!found) {
    throw new Error("conversation_not_found");
  }
  return found;
}

function toSummary(item: Conversation): ConversationSummary {
  return {
    id: item.id,
    title: item.title,
    language: item.language,
    active_theme: item.active_theme,
    pinned: item.pinned,
    archived: item.archived,
    pinned_at: item.pinned_at,
    created_at: item.created_at,
    updated_at: item.updated_at,
  };
}

function sortByUpdated(items: Conversation[]): Conversation[] {
  return items.slice().sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

function matchesQuery(item: Conversation, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  if (item.title.toLowerCase().includes(needle)) return true;
  return item.messages.some((message) =>
    message.content.toLowerCase().includes(needle),
  );
}

function titleFrom(content: string, language: ChatLanguage | null): string {
  const trimmed = content.trim().replace(/\s+/g, " ");
  if (!trimmed) return language === "en" ? "New chat" : "گفتگوی جدید";
  return trimmed.length > 28 ? `${trimmed.slice(0, 28)}…` : trimmed;
}

function wantsImage(input: SendMessageInput): boolean {
  if (input.generateImage || input.retryArtifactId) return true;
  if (input.referenceArtifactIds?.length) return true;
  if (input.skillHint) return true;
  const text = input.content;
  if (!text.trim()) return false;
  if (/کپشن|caption/i.test(text)) return false;
  return /تصویر|عکس|پست|تبلیغ|بساز|ad\b|image|illustration|post/i.test(text);
}

function pickAspect(input: SendMessageInput): ArtifactAspect {
  if (input.skillHint === "advertising") return "4:5";
  if (input.skillHint === "education" || input.skillHint === "general_image") {
    return "1:1";
  }
  if (/تبلیغ|کفش|luxury|ad\b|shoe|editorial|instagram ad/i.test(input.content)) {
    return "4:5";
  }
  return "1:1";
}

function assistantCopy(
  language: ChatLanguage,
  generated: boolean,
  text: string,
): string {
  if (language === "en") {
    if (generated) {
      return "Here's this version:";
    }
    if (/caption/i.test(text)) {
      return "A friendly caption stays warm and short. A formal one sounds more like a brand statement.";
    }
    return "Sure — tell me what you’d like to make.";
  }
  if (generated) {
    if (/اعشار|کسر|آموزش|کلاس/.test(text)) {
      return "حتما. یه مسیر تمیز و رنگی می‌سازم که برای دانش‌آموزها جذاب باشه ولی زیادی کودکانه نشه.";
    }
    return "این نسخه رو ساختم:";
  }
  if (/کپشن|caption/i.test(text)) {
    return "کپشن دوستانه کوتاه و گرم می‌مونه؛ رسمی‌ترش بیشتر شبیه معرفی برنده.";
  }
  return "باشه. بگو چی برات بسازم.";
}

function touch(conversation: Conversation, language: ChatLanguage): void {
  conversation.updated_at = new Date().toISOString();
  conversation.language = language;
}

async function completeTurn(
  conversation: Conversation,
  input: SendMessageInput,
): Promise<ChatTurnResult> {
  await pause();
  const now = new Date().toISOString();
  const language: ChatLanguage = input.content.trim()
    ? inferMessageLanguage(input.content)
    : conversation.language ?? "fa";
  const generate = wantsImage(input);

  if (input.content.trim() || input.attachment) {
    conversation.messages.push({
      id: nextId("msg"),
      conversation_id: conversation.id,
      role: "user",
      content: input.content.trim(),
      language,
      created_at: now,
      metadata_json: {
        ...(input.attachment ? { attachment: input.attachment } : {}),
        ...(input.skillHint ? { explicit_skill_hint: input.skillHint } : {}),
      },
    });
    if (
      conversation.title === "گفتگوی جدید" ||
      conversation.title === "New chat"
    ) {
      conversation.title = titleFrom(input.content, language);
    }
  }

  const assistantId = nextId("msg");
  conversation.messages.push({
    id: assistantId,
    conversation_id: conversation.id,
    role: "assistant",
    content: assistantCopy(language, generate, input.content),
    language,
    created_at: now,
  });

  if (generate) {
    conversation.artifacts.push({
      id: nextId("art"),
      conversation_id: conversation.id,
      message_id: assistantId,
      artifact_type: "image",
      storage_path: pickAspect(input) === "4:5" ? PORTRAIT : SQUARE,
      aspect_ratio: pickAspect(input),
      status: "ready",
      created_at: now,
    });
  }

  touch(conversation, language);
  return { conversation: clone(conversation) };
}

export const mockChatApi: ChatApi = {
  async createConversation() {
    const now = new Date().toISOString();
    const conversation: Conversation = {
      id: nextId("conv"),
      title: "گفتگوی جدید",
      language: "fa",
      active_theme: null,
      pinned: false,
      archived: false,
      pinned_at: null,
      created_at: now,
      updated_at: now,
      messages: [],
      artifacts: [],
    };
    conversations = [conversation, ...conversations];
    return clone(conversation);
  },

  async listConversations(options: ListConversationsOptions = {}) {
    const archived = Boolean(options.archived);
    return sortByUpdated(
      conversations.filter(
        (item) =>
          item.archived === archived && matchesQuery(item, options.q ?? ""),
      ),
    ).map(toSummary);
  },

  async listArchivedConversations() {
    return mockChatApi.listConversations({ archived: true });
  },

  async searchConversations(query, options = {}) {
    return mockChatApi.listConversations({
      archived: options.archived,
      q: query,
    });
  },

  async getConversation(id) {
    return clone(requireConversation(id));
  },

  async sendMessage(conversationId, input) {
    if (!conversationId) {
      const created = await mockChatApi.createConversation();
      const stored = requireConversation(created.id);
      if (input.activeTheme !== undefined) {
        stored.active_theme = input.activeTheme;
      }
      return completeTurn(stored, input);
    }
    return completeTurn(requireConversation(conversationId), input);
  },

  async generateImage(conversationId) {
    return completeTurn(requireConversation(conversationId), {
      content: "",
      generateImage: true,
    });
  },

  async setActiveTheme(conversationId, themeId) {
    const conversation = requireConversation(conversationId);
    conversation.active_theme = snapshotForThemeId(themeId);
    conversation.updated_at = new Date().toISOString();
    return clone(conversation);
  },

  async listThemes() {
    return clone(CHAT_THEMES);
  },

  async renameConversation(id, title) {
    const conversation = requireConversation(id);
    const next = title.trim();
    if (next) conversation.title = next;
    conversation.updated_at = new Date().toISOString();
    return clone(conversation);
  },

  async deleteConversation(id) {
    requireConversation(id);
    conversations = conversations.filter((item) => item.id !== id);
  },

  async archiveConversation(id) {
    const conversation = requireConversation(id);
    conversation.archived = true;
    conversation.pinned = false;
    conversation.pinned_at = null;
    conversation.updated_at = new Date().toISOString();
    return clone(conversation);
  },

  async restoreConversation(id) {
    const conversation = requireConversation(id);
    conversation.archived = false;
    conversation.updated_at = new Date().toISOString();
    return clone(conversation);
  },

  async pinConversation(id) {
    const conversation = requireConversation(id);
    conversation.pinned = true;
    conversation.pinned_at = new Date().toISOString();
    return clone(conversation);
  },

  async unpinConversation(id) {
    const conversation = requireConversation(id);
    conversation.pinned = false;
    conversation.pinned_at = null;
    return clone(conversation);
  },

  async shareConversation(id): Promise<ConversationSharePayload> {
    const conversation = requireConversation(id);
    return {
      title: conversation.title,
      text: formatConversationShareText(conversation),
      publicUrl: null,
    };
  },
};
