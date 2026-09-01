export type ConversationMenuAction =
  | "rename"
  | "pin"
  | "unpin"
  | "archive"
  | "share"
  | "delete";

export function overflowActions(pinned: boolean): ConversationMenuAction[] {
  return ["rename", pinned ? "unpin" : "pin", "archive", "share", "delete"];
}

export function shouldLeaveConversation(
  targetId: string,
  currentId: string | null,
): boolean {
  return currentId === targetId;
}

export function isDestructiveMenuAction(
  action: ConversationMenuAction,
): boolean {
  return action === "delete";
}

export function deleteRequiresConfirmation(): boolean {
  return true;
}
