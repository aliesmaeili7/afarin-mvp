export type ChatLanguage = "fa" | "en";
export type ChatRole = "user" | "assistant";
export type ArtifactType = "image" | "audio" | "video" | "subtitle" | "document";
export type ArtifactStatus = "generating" | "ready" | "failed";
export type ArtifactAspect = "1:1" | "4:5";
export type ChatThemeGroup = "saved" | "catalog";

export interface ChatTheme {
  id: string;
  name: string;
  group: ChatThemeGroup;
  swatch: string;
}

/** Semantic snapshot persisted on a conversation. No CSS/swatches. */
export interface ChatThemeSnapshot {
  id: string;
  source: string;
  name: string;
  style_json: Record<string, unknown>;
}

export interface ConversationSummary {
  id: string;
  title: string;
  language: ChatLanguage | null;
  active_theme: ChatThemeSnapshot | null;
  pinned: boolean;
  archived: boolean;
  pinned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatAttachment {
  name: string;
  dataUrl?: string;
  mime_type?: string;
  storage_path?: string;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: ChatRole;
  content: string;
  language: ChatLanguage | null;
  metadata_json?: {
    attachment?: ChatAttachment;
    explicit_skill_hint?: SkillHint;
    failed?: boolean;
    status?: string;
    activity_phase?: string;
    route?: string;
    requested_image_count?: number;
    [key: string]: unknown;
  };
  created_at: string;
  pending?: boolean;
}

export interface ConversationArtifact {
  id: string;
  conversation_id: string;
  message_id: string | null;
  artifact_type: ArtifactType;
  storage_path: string | null;
  url?: string | null;
  mime_type?: string | null;
  width?: number | null;
  height?: number | null;
  aspect_ratio: ArtifactAspect | null;
  status: ArtifactStatus;
  metadata_json?: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  language: ChatLanguage | null;
  active_theme: ChatThemeSnapshot | null;
  pinned: boolean;
  archived: boolean;
  pinned_at: string | null;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
  artifacts: ConversationArtifact[];
  has_older_messages?: boolean;
}

/** Phase A/B share result: plain text only. No public URL. */
export interface ConversationSharePayload {
  title: string;
  text: string;
  publicUrl: null;
}

export type SkillHint = "advertising" | "education" | "general_image";

export interface SendMessageInput {
  content: string;
  attachment?: ChatAttachment | null;
  generateImage?: boolean;
  skillHint?: SkillHint | null;
  retryArtifactId?: string;
  referenceArtifactIds?: string[];
  activeTheme?: ChatThemeSnapshot | null;
  language?: ChatLanguage;
}

export interface ChatTurnResult {
  conversation: Conversation;
}

export interface ListConversationsOptions {
  archived?: boolean;
  q?: string;
}

export interface ChatApi {
  createConversation(): Promise<Conversation>;
  listConversations(
    options?: ListConversationsOptions,
  ): Promise<ConversationSummary[]>;
  listArchivedConversations(): Promise<ConversationSummary[]>;
  searchConversations(
    query: string,
    options?: { archived?: boolean },
  ): Promise<ConversationSummary[]>;
  getConversation(id: string): Promise<Conversation>;
  sendMessage(
    conversationId: string | null,
    input: SendMessageInput,
  ): Promise<ChatTurnResult>;
  generateImage(conversationId: string): Promise<ChatTurnResult>;
  setActiveTheme(
    conversationId: string,
    themeId: string | null,
  ): Promise<Conversation>;
  listThemes(): Promise<ChatTheme[]>;
  renameConversation(id: string, title: string): Promise<Conversation>;
  deleteConversation(id: string): Promise<void>;
  archiveConversation(id: string): Promise<Conversation>;
  restoreConversation(id: string): Promise<Conversation>;
  pinConversation(id: string): Promise<Conversation>;
  unpinConversation(id: string): Promise<Conversation>;
  shareConversation(id: string): Promise<ConversationSharePayload>;
}
