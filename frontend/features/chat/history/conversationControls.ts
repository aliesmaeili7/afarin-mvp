export interface ConversationControls {
  menuId: string | null;
  renamingId: string | null;
  onMenuId: (id: string | null) => void;
  onStartRename: (id: string) => void;
  onCommitRename: (id: string, title: string) => void;
  onCancelRename: () => void;
  onPin: (id: string) => void;
  onUnpin: (id: string) => void;
  onArchive: (id: string) => void;
  onShare: (id: string) => void;
  onRequestDelete: (id: string) => void;
  onOpenArchive: () => void;
}
