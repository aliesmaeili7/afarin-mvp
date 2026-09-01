"use client";

import { useCallback, useId, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArchiveIcon,
  ChevronIcon,
  LogoutIcon,
  SettingsIcon,
  UserIcon,
} from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import { formatDigits } from "@/lib/format/display";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { accountInitials } from "./accountSummary";
import {
  accountMenuItems,
  accountRowTitle,
} from "./accountMenu";
import { chatChromeDir, chatMenuSurface } from "./chatChrome";
import { ChatAnchorMenu } from "./primitives/ChatAnchorMenu";
import { ChatMenuButton } from "./primitives/ChatMenuButton";
import { ChatSheet } from "./primitives/ChatSheet";
import { useChatAccount } from "./useChatAccount";
import { useMobileSheet } from "./useChatSession";
import { clearChatDraft } from "./chatDraft";

export function ChatAccountRow({
  collapsed,
  onOpenArchive,
}: {
  collapsed: boolean;
  onOpenArchive: () => void;
}) {
  const { t, locale, openSettings } = useI18n();
  const router = useRouter();
  const { account, signOut } = useChatAccount();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const labelId = useId();
  const mobile = useMobileSheet();
  const surface = chatMenuSurface(mobile);
  const dir = chatChromeDir(locale);
  const name = accountRowTitle(account, t("chat.accountSignInRow"));
  const status =
    account.signedIn && account.remainingCampaigns != null
      ? t("chat.accountFreeLeft", {
          n: formatDigits(account.remainingCampaigns, locale),
        })
      : null;
  const initials = accountInitials(account.displayName);

  const close = useCallback(() => {
    setOpen(false);
  }, []);

  async function handleSignOut() {
    close();
    clearChatDraft();
    await signOut();
    router.push("/chat");
  }

  const items = (
    <div className="flex flex-col gap-0.5" dir={dir}>
      {accountMenuItems(account.signedIn).map((item) => {
        const row = (
          item.id === "profile" ? (
            <Link
              href={item.href ?? "/dashboard"}
              role="menuitem"
              data-chat="account-profile"
              onClick={close}
              className="flex h-11 w-full items-center gap-3 rounded-chat-md px-3 text-sm font-medium text-chat-text hover:bg-chat-surface-secondary"
            >
              <span className="grid size-5 place-items-center text-chat-text-secondary">
                <UserIcon width={18} height={18} />
              </span>
              {t("chat.accountProfile")}
            </Link>
          ) : item.id === "settings" ? (
            <ChatMenuButton
              icon={<SettingsIcon width={18} height={18} />}
              label={t("chat.accountSettings")}
              dataChat="account-settings"
              onClick={() => {
                close();
                openSettings();
              }}
            />
          ) : item.id === "archive" ? (
            <ChatMenuButton
              icon={<ArchiveIcon width={18} height={18} />}
              label={t("chat.archivedChats")}
              dataChat="account-archive"
              onClick={() => {
                close();
                onOpenArchive();
              }}
            />
          ) : item.id === "signOut" ? (
            <ChatMenuButton
              icon={<LogoutIcon width={18} height={18} />}
              label={t("chat.accountSignOut")}
              dataChat="account-signout"
              onClick={() => void handleSignOut()}
            />
          ) : item.id === "signIn" ? (
            <Link
              href={item.href ?? "/login"}
              role="menuitem"
              data-chat="account-signin"
              onClick={close}
              className="flex h-11 w-full items-center gap-3 rounded-chat-md px-3 text-sm font-medium text-chat-text hover:bg-chat-surface-secondary"
            >
              <span className="grid size-5 place-items-center text-chat-text-secondary">
                <UserIcon width={18} height={18} />
              </span>
              {t("chat.accountSignIn")}
            </Link>
          ) : (
            <Link
              href={item.href ?? "/create/signup"}
              role="menuitem"
              data-chat="account-create"
              onClick={close}
              className="flex h-11 w-full items-center gap-3 rounded-chat-md px-3 text-sm font-medium text-chat-text hover:bg-chat-surface-secondary"
            >
              <span className="grid size-5 place-items-center text-chat-text-secondary">
                <UserIcon width={18} height={18} />
              </span>
              {t("chat.accountCreate")}
            </Link>
          )
        );

        return (
          <div key={item.id}>
            {item.dividerBefore ? (
              <div className="mx-3 my-1 h-px bg-chat-border-subtle" />
            ) : null}
            {row}
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="relative mt-auto px-2 pb-safe pt-2">
      <button
        ref={triggerRef}
        type="button"
        id={labelId}
        data-chat="account-row"
        data-signed-in={account.signedIn ? "true" : "false"}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex w-full items-center gap-3 rounded-chat-lg px-2 py-2 text-start",
          "hover:bg-chat-surface-secondary",
          collapsed && "justify-center px-0",
        )}
      >
        <span
          aria-hidden="true"
          className="grid size-9 shrink-0 place-items-center rounded-full bg-chat-accent-soft text-xs font-bold text-chat-accent"
        >
          {account.signedIn && initials ? (
            initials
          ) : (
            <UserIcon width={16} height={16} />
          )}
        </span>
        {collapsed ? (
          <span className="sr-only">{name}</span>
        ) : (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-chat-text">
                {name}
              </span>
              {status ? (
                <span className="block truncate text-xs text-chat-text-secondary">
                  {status}
                </span>
              ) : null}
            </span>
            <ChevronIcon
              width={16}
              height={16}
              className={cn(
                "shrink-0 text-chat-text-secondary/70 chat-motion",
                open && "rotate-180",
              )}
            />
          </>
        )}
      </button>

      {surface === "sheet" ? (
        <ChatSheet
          open={open}
          onClose={close}
          title={t("chat.accountRow")}
          dataChat="account-menu"
          overlayClassName="z-[60]"
          compact
        >
          {items}
        </ChatSheet>
      ) : (
        <ChatAnchorMenu
          open={open}
          onClose={close}
          anchorRef={triggerRef}
          labelledBy={labelId}
          dataChat="account-menu"
          preferUp
        >
          {items}
        </ChatAnchorMenu>
      )}
    </div>
  );
}
