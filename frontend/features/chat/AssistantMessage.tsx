"use client";

import { messageDirFromLanguage } from "./chatDirection";
import { ImageArtifact } from "./artifacts/ImageArtifact";
import { ChatActivityIndicator } from "./artifacts/ChatActivityIndicator";
import type {
  ConversationArtifact,
  ConversationMessage,
} from "@/lib/api/chat/types";

export function AssistantMessage({
  message,
  artifacts,
  onRetry,
  onUseAsReference,
}: {
  message: ConversationMessage;
  artifacts: ConversationArtifact[];
  onRetry: (artifactId: string) => void;
  onUseAsReference: (artifact: ConversationArtifact) => void;
}) {
  const dir = messageDirFromLanguage(message.language);
  const failed = Boolean(message.metadata_json?.failed);
  const generating = message.metadata_json?.status === "generating";
  const related = artifacts.filter((item) => item.message_id === message.id);
  const imageCount = Number(message.metadata_json?.requested_image_count) || 1;
  const phase =
    typeof message.metadata_json?.activity_phase === "string"
      ? message.metadata_json.activity_phase
      : undefined;

  return (
    <div className="flex flex-col gap-3" data-chat="assistant-message" dir={dir}>
      {message.content && !failed && !generating ? (
        <p className="max-w-2xl text-[0.98rem] leading-8 text-chat-text">
          {message.content}
        </p>
      ) : null}
      {generating && related.length === 0 ? (
        <ChatActivityIndicator
          phase={phase}
          language={message.language}
          imageCount={imageCount}
        />
      ) : null}
      {related.map((artifact) => (
        <ImageArtifact
          key={artifact.id}
          artifact={artifact}
          phase={phase}
          language={message.language}
          imageCount={imageCount}
          onRetry={() => onRetry(artifact.id)}
          onUseAsReference={() => onUseAsReference(artifact)}
        />
      ))}
    </div>
  );
}
