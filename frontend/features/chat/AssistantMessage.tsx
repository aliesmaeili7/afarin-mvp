"use client";

import { messageDirFromLanguage } from "./chatDirection";
import { ImageArtifact } from "./artifacts/ImageArtifact";
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
  const related = artifacts.filter((item) => item.message_id === message.id);

  return (
    <div className="flex flex-col gap-3" data-chat="assistant-message" dir={dir}>
      {message.content ? (
        <p className="max-w-2xl text-[0.98rem] leading-8 text-chat-text">
          {failed ? null : message.content}
        </p>
      ) : null}
      {related.map((artifact) => (
        <ImageArtifact
          key={artifact.id}
          artifact={artifact}
          onRetry={() => onRetry(artifact.id)}
          onUseAsReference={() => onUseAsReference(artifact)}
        />
      ))}
    </div>
  );
}
