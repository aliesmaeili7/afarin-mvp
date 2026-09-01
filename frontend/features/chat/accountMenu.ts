import type { AccountSummary } from "./accountSummary";

export type AccountMenuItemId =
  | "profile"
  | "settings"
  | "archive"
  | "signOut"
  | "signIn"
  | "createAccount";

export interface AccountMenuItem {
  id: AccountMenuItemId;
  href?: string;
  dividerBefore?: boolean;
}

const SIGNED_IN: AccountMenuItem[] = [
  { id: "profile", href: "/dashboard" },
  { id: "settings" },
  { id: "archive" },
  { id: "signOut", dividerBefore: true },
];

const SIGNED_OUT: AccountMenuItem[] = [
  { id: "signIn", href: "/login?next=/chat" },
  { id: "createAccount", href: "/create/signup" },
  { id: "archive", dividerBefore: true },
];

export function accountMenuItems(signedIn: boolean): AccountMenuItem[] {
  return signedIn ? SIGNED_IN : SIGNED_OUT;
}

export function accountRowTitle(
  account: AccountSummary,
  signedOutLabel: string,
): string {
  if (account.signedIn) return account.displayName ?? signedOutLabel;
  return signedOutLabel;
}

export async function invokeChatSignOut(auth: {
  signOut: () => Promise<void>;
}): Promise<void> {
  await auth.signOut();
}
