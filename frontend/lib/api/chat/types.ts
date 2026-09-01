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

export interface ConversationSummary {
  id: string;
  title: string;
  language: ChatLanguage;
  active_theme_id: string | null;
  pinned: boolean;
  archived: boolean;
  pinned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatAttachment {
  name: string;
  dataUrl: string;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: ChatRole;
  content: string;
  language: ChatLanguage;
  metadata_json?: {
    attachment?: ChatAttachment;
    failed?: boolean;
    [key: string]: unknown;
  };
  created_at: string;
}

export interface ConversationArtifact {
  id: string;
  conversation_id: string;
  message_id: string | null;
  artifact_type: ArtifactType;
  storage_path: string | null;
  aspect_ratio: ArtifactAspect;
  status: ArtifactStatus;
  metadata_json?: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  language: ChatLanguage;
  active_theme_id: string | null;
  pinned: boolean;
  archived: boolean;
  pinned_at: string | null;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
  artifacts: ConversationArtifact[];
}

/** Phase A share result: plain text only. No public URL until a real share route exists. */
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
}

export interface ChatTurnResult {
  conversation: Conversation;
}

export interface ChatApi {
  createConversation(): Promise<Conversation>;
  listConversations(): Promise<ConversationSummary[]>;
  listArchivedConversations(): Promise<ConversationSummary[]>;
  getConversation(id: string): Promise<Conversation>;
  sendMessage(
    conversationId: string,
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
