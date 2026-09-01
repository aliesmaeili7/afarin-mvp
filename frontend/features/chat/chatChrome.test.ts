import { describe, expect, it } from "vitest";
import { t } from "@/lib/i18n/t";
import { chatChromeDir, chatMenuSurface } from "./chatChrome";

describe("chat chrome direction", () => {
  it("uses RTL for Persian menus and LTR for English", () => {
    expect(chatChromeDir("fa")).toBe("rtl");
    expect(chatChromeDir("en")).toBe("ltr");
  });

  it("translates account and conversation labels in both locales", () => {
    expect(t("fa", "chat.accountProfile")).toBe("حساب کاربری");
    expect(t("en", "chat.accountProfile")).toBe("Profile");
    expect(t("fa", "chat.rename")).toBe("تغییر نام");
    expect(t("en", "chat.rename")).toBe("Rename");
    expect(t("fa", "chat.deleteTitle")).toBe("این گفتگو حذف شود؟");
    expect(t("en", "chat.deleteTitle")).toBe("Delete this chat?");
    expect(t("fa", "chat.referenceChip")).toBe("مرجع: آخرین تصویر");
    expect(t("en", "chat.referenceChip")).toBe("Reference: last image");
  });

  it("uses a bottom sheet on mobile and a popover on desktop", () => {
    expect(chatMenuSurface(true)).toBe("sheet");
    expect(chatMenuSurface(false)).toBe("popover");
  });
});
