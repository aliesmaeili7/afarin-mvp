import { ChatWorkspace } from "@/features/chat/ChatWorkspace";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.chat");

export default function ChatPage() {
  return <ChatWorkspace conversationId={null} />;
}
