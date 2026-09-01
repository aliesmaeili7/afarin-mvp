import type { ReactNode } from "react";

export default function ChatLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return <div className="h-dvh overflow-hidden bg-chat-bg">{children}</div>;
}
