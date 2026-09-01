import { describe, expect, it, vi } from "vitest";
import { t } from "@/lib/i18n/t";
import type { Session } from "@/types/domain";
import {
  accountInitials,
  accountSummaryFromSession,
} from "./accountSummary";
import {
  accountMenuItems,
  accountRowTitle,
  invokeChatSignOut,
} from "./accountMenu";

const session: Session = {
  user: {
    id: "u1",
    email: "ali@example.com",
    display_name: "Ali Esmaeili Askari",
    locale: "fa",
    free_campaigns_remaining: 3,
  },
  access_token: "token",
};

describe("signed-in account footer", () => {
  it("maps session identity without inventing plan labels", () => {
    const account = accountSummaryFromSession(session);
    expect(account).toEqual({
      signedIn: true,
      displayName: "Ali Esmaeili Askari",
      email: "ali@example.com",
      remainingCampaigns: 3,
    });
    expect(accountRowTitle(account, "ورود / ثبت‌نام")).toBe(
      "Ali Esmaeili Askari",
    );
    expect(accountInitials(account.displayName)).toBe("AE");
  });

  it("lists only real signed-in destinations", () => {
    expect(accountMenuItems(true).map((item) => item.id)).toEqual([
      "profile",
      "settings",
      "archive",
      "signOut",
    ]);
    expect(accountMenuItems(true).find((item) => item.id === "profile")?.href).toBe(
      "/dashboard",
    );
    expect(accountMenuItems(true).some((item) => item.id === "signIn")).toBe(
      false,
    );
  });
});

describe("signed-out account footer", () => {
  it("renders the sign-in row without a fake identity", () => {
    const account = accountSummaryFromSession(null);
    expect(account.signedIn).toBe(false);
    expect(accountRowTitle(account, t("fa", "chat.accountSignInRow"))).toBe(
      "ورود / ثبت‌نام",
    );
    expect(accountRowTitle(account, t("en", "chat.accountSignInRow"))).toBe(
      "Sign in / Sign up",
    );
  });

  it("offers login and the existing signup route", () => {
    const items = accountMenuItems(false);
    expect(items.map((item) => item.id)).toEqual([
      "signIn",
      "createAccount",
      "archive",
    ]);
    expect(items.find((item) => item.id === "signIn")?.href).toBe(
      "/login?next=/chat",
    );
    expect(items.find((item) => item.id === "createAccount")?.href).toBe(
      "/create/signup",
    );
  });
});

describe("account menu auth", () => {
  it("logout invokes the existing auth abstraction", async () => {
    const signOut = vi.fn(async () => undefined);
    await invokeChatSignOut({ signOut });
    expect(signOut).toHaveBeenCalledTimes(1);
  });
});
