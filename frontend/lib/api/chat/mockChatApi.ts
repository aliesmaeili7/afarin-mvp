import { inferMessageLanguage } from "@/features/chat/chatDirection";
import { preparingPhaseFor } from "@/features/chat/chatActivity";
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

type MockJob = {
  startedAt: number;
  assistantId: string;
  artifactId: string;
  route: "advertising" | "education" | "general_image" | "image_edit";
  language: ChatLanguage;
};

const mockJobs = new Map<string, MockJob>();

export function setChatMockDelay(ms: number): void {
  delayMs = ms;
}

export function resetChatMock(): void {
  delayMs = 0;
  seq = 100;
  conversations = createSeedConversations();
  mockJobs.clear();
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

function isEditRequest(text: string): boolean {
  return /روشن‌تر|تاریک‌تر|پس‌زمینه|بک‌گراند|حذف کن|تیتر|عوض کن|استوری|مربعش|make this brighter|remove the|change the title|change the background|vertical|square/i.test(
    text,
  );
}

function isRegenerateRequest(text: string): boolean {
  return /یکی\s+دیگه|یه\s+نسخه\s+دیگه|another (one|version)|one more/i.test(
    text,
  );
}

function isCaptionRequest(text: string): boolean {
  return /کپشن|caption/i.test(text);
}

function isDeicticLatest(text: string): boolean {
  return /عکس قبلی|تصویر قبلی|همین|همون|آخری|this one|the previous image|the last image/i.test(
    text,
  );
}

function lastReadyImage(conversation: Conversation | undefined) {
  if (!conversation) return undefined;
  return [...conversation.artifacts]
    .reverse()
    .find((item) => item.artifact_type === "image" && item.status === "ready");
}

function generationRoute(
  input: SendMessageInput,
  conversation?: Conversation,
): "advertising" | "education" | "general_image" | "image_edit" {
  if (input.skillHint === "advertising") return "advertising";
  if (input.skillHint === "education") return "education";
  if (input.skillHint === "general_image") return "general_image";
  const origin =
    lastReadyImage(conversation)?.metadata_json?.skill ??
    [...(conversation?.messages ?? [])]
      .reverse()
      .find((item) => item.role === "assistant")?.metadata_json?.route;
  if (isRegenerateRequest(input.content)) {
    if (origin === "advertising" || origin === "education" || origin === "general_image") {
      return origin;
    }
  }
  if (isEditRequest(input.content)) return "image_edit";
  if (/تبلیغ|کفش|luxury|ad\b|shoe|editorial|instagram ad/i.test(input.content)) {
    return "advertising";
  }
  if (/آموزش|کلاس|اعشار|کسر|پست/i.test(input.content)) return "education";
  return "general_image";
}

function advanceMockJob(conversation: Conversation): void {
  const job = mockJobs.get(conversation.id);
  if (!job) return;
  const assistant = conversation.messages.find((item) => item.id === job.assistantId);
  const artifact = conversation.artifacts.find((item) => item.id === job.artifactId);
  if (!assistant || !artifact) {
    mockJobs.delete(conversation.id);
    return;
  }
  const elapsed = Date.now() - job.startedAt;
  const meta = {
    ...(assistant.metadata_json ?? {}),
    status: "generating" as const,
    route: job.route,
  };
  if (elapsed < delayMs) {
    assistant.metadata_json = {
      ...meta,
      activity_phase: preparingPhaseFor(job.route),
    };
    return;
  }
  if (elapsed < delayMs * 2) {
    assistant.metadata_json = { ...meta, activity_phase: "generating_image" };
    return;
  }
  if (job.route === "advertising" && elapsed < delayMs * 2.5) {
    assistant.metadata_json = { ...meta, activity_phase: "finalizing" };
    return;
  }
  const { activity_phase: _dropped, ...rest } = meta;
  assistant.metadata_json = { ...rest, status: "ready" };
  assistant.content = assistantCopy(job.language, true, "");
  artifact.status = "ready";
  artifact.storage_path =
    artifact.aspect_ratio === "9:16"
      ? PORTRAIT
      : artifact.aspect_ratio === "4:5"
        ? PORTRAIT
        : SQUARE;
  mockJobs.delete(conversation.id);
}

function wantsImage(
  input: SendMessageInput,
  conversation: Conversation,
): boolean {
  if (input.generateImage || input.retryArtifactId) return true;
  if (/__fail_edit__/i.test(input.content)) return true;
  if (input.skillHint) return true;
  const text = input.content;
  if (!text.trim()) return false;
  if (isCaptionRequest(text)) return false;
  if (isEditRequest(text)) {
    const ready = conversation.artifacts.filter(
      (item) => item.artifact_type === "image" && item.status === "ready",
    );
    if (input.referenceArtifactIds?.length || input.attachment) return true;
    if (isDeicticLatest(text) && ready.length) return true;
    if (ready.length === 1) return true;
    return false;
  }
  return /تصویر|عکس|پست|تبلیغ|بساز|ad\b|image|illustration|post/i.test(text);
}

function pickAspect(
  input: SendMessageInput,
  conversation: Conversation,
): ArtifactAspect {
  if (/استوری|عمودی|9:16|story|vertical/i.test(input.content)) return "9:16";
  if (/مربع|1:1|square/i.test(input.content)) return "1:1";
  if (/فید|4:5|feed/i.test(input.content)) return "4:5";
  if (input.skillHint === "advertising") return "4:5";
  if (input.skillHint === "education" || input.skillHint === "general_image") {
    return "1:1";
  }
  const referenced = conversation.artifacts.find((item) =>
    input.referenceArtifactIds?.includes(item.id),
  );
  if (referenced?.aspect_ratio) return referenced.aspect_ratio;
  const latest = lastReadyImage(conversation);
  if (isEditRequest(input.content) && latest?.aspect_ratio) {
    return latest.aspect_ratio;
  }
  if (/تبلیغ|کفش|luxury|ad\b|shoe|editorial|instagram ad/i.test(input.content)) {
    return "4:5";
  }
  return "1:1";
}

function pathForAspect(aspect: ArtifactAspect): string {
  return aspect === "1:1" ? SQUARE : PORTRAIT;
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

  if (input.retryArtifactId) {
    const artifact = conversation.artifacts.find(
      (item) => item.id === input.retryArtifactId,
    );
    const assistant = conversation.messages.find(
      (item) => item.id === artifact?.message_id,
    );
    if (artifact && assistant) {
      const stored = assistant.metadata_json?.route;
      const route =
        stored === "advertising" ||
        stored === "education" ||
        stored === "general_image" ||
        stored === "image_edit"
          ? stored
          : "general_image";
      artifact.status = delayMs === 0 ? "ready" : "generating";
      artifact.storage_path =
        delayMs === 0 ? pathForAspect(artifact.aspect_ratio ?? "1:1") : null;
      assistant.metadata_json = {
        ...(assistant.metadata_json ?? {}),
        status: delayMs === 0 ? "ready" : "generating",
        failed: false,
        retryable: false,
        route,
        ...(delayMs === 0 ? {} : { activity_phase: preparingPhaseFor(route) }),
      };
      if (delayMs === 0) {
        delete assistant.metadata_json.activity_phase;
        assistant.content = assistantCopy(language, true, "");
      } else {
        assistant.content = "";
        mockJobs.set(conversation.id, {
          startedAt: Date.now(),
          assistantId: assistant.id,
          artifactId: artifact.id,
          route,
          language: assistant.language === "en" ? "en" : "fa",
        });
      }
      touch(conversation, language);
      return { conversation: clone(conversation) };
    }
  }

  const failEdit = /__fail_edit__/i.test(input.content);
  const generate = wantsImage(input, conversation) || failEdit;
  const readyImages = conversation.artifacts.filter(
    (item) => item.artifact_type === "image" && item.status === "ready",
  );
  const ambiguousEdit =
    isEditRequest(input.content) &&
    !generate &&
    !input.referenceArtifactIds?.length &&
    readyImages.length > 1;

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
        ...(input.referenceArtifactIds?.length
          ? { reference_artifact_ids: input.referenceArtifactIds }
          : {}),
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
  const route = failEdit
    ? "image_edit"
    : generate
      ? generationRoute(input, conversation)
      : null;
  conversation.messages.push({
    id: assistantId,
    conversation_id: conversation.id,
    role: "assistant",
    content: ambiguousEdit
      ? language === "en"
        ? "Which image do you mean? Tap Use as reference on that photo and I’ll edit exactly that one."
        : "کدوم تصویر رو می‌گی؟ اگه روی همون عکس «استفاده به‌عنوان مرجع» بزنی، دقیقاً همونو تغییر می‌دم."
      : !generate && isEditRequest(input.content)
        ? language === "en"
          ? "Which image should I change? Send a photo or choose one from this chat as a reference."
          : "کدوم تصویر رو می‌خوای تغییر بدم؟ یه عکس بفرست یا یکی از تصاویر گفتگو رو به‌عنوان مرجع انتخاب کن."
        : assistantCopy(language, generate && delayMs === 0 && !failEdit, input.content),
    language,
    created_at: now,
    metadata_json: generate
      ? {
          route: route ?? "general_image",
          status: failEdit
            ? "failed"
            : delayMs === 0
              ? "ready"
              : "generating",
          ...(failEdit ? { failed: true, retryable: true } : {}),
          ...(delayMs === 0 || failEdit
            ? {}
            : { activity_phase: preparingPhaseFor(route) }),
        }
      : {
          route: "clarify",
          status: "ready",
          ...(ambiguousEdit || isEditRequest(input.content)
            ? { needs_clarification: true }
            : { route: "general_chat", status: "ready" }),
        },
  });

  if (generate) {
    const artifactId = nextId("art");
    const aspect = pickAspect(input, conversation);
    const source = conversation.artifacts.find((item) =>
      input.referenceArtifactIds?.includes(item.id),
    ) ?? lastReadyImage(conversation);
    conversation.artifacts.push({
      id: artifactId,
      conversation_id: conversation.id,
      message_id: assistantId,
      artifact_type: "image",
      storage_path:
        failEdit || delayMs > 0 ? null : pathForAspect(aspect),
      aspect_ratio: aspect,
      status: failEdit ? "failed" : delayMs === 0 ? "ready" : "generating",
      created_at: now,
      metadata_json:
        route === "image_edit"
          ? {
              skill: "image_edit",
              source_artifact_ids: source ? [source.id] : [],
              generation: 2,
            }
          : { skill: route ?? "general_image" },
    });
    if (delayMs > 0 && route && !failEdit) {
      mockJobs.set(conversation.id, {
        startedAt: Date.now(),
        assistantId,
        artifactId,
        route,
        language,
      });
    }
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
    const conversation = requireConversation(id);
    advanceMockJob(conversation);
    return clone(conversation);
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
