import { describe, expect, it } from "vitest";
import { t } from "@/lib/i18n/t";
import {
  PLUS_MENU_ITEMS,
  clearCreationAction,
  emptyComposerContext,
  plusMenuHrefs,
  selectCreationAction,
  setComposerAttachment,
  setComposerTheme,
  skillHintFromAction,
} from "./plusMenu";

describe("plus menu catalog", () => {
  it("renders five items in the requested order", () => {
    expect(PLUS_MENU_ITEMS.map((item) => item.action)).toEqual([
      "advertising",
      "education",
      "generate",
      "upload",
      "theme",
    ]);
    expect(t("fa", PLUS_MENU_ITEMS[0].labelKey)).toBe("تبلیغ بساز");
    expect(t("en", PLUS_MENU_ITEMS[0].labelKey)).toBe("Create advertisement");
    expect(t("fa", PLUS_MENU_ITEMS[1].labelKey)).toBe("پست آموزشی");
    expect(t("en", PLUS_MENU_ITEMS[1].labelKey)).toBe("Educational post");
    expect(t("fa", PLUS_MENU_ITEMS[2].labelKey)).toBe("تصویر بساز");
    expect(t("en", PLUS_MENU_ITEMS[2].labelKey)).toBe("Generate image");
    expect(t("fa", PLUS_MENU_ITEMS[3].labelKey)).toBe("بارگذاری تصویر");
    expect(t("fa", PLUS_MENU_ITEMS[4].labelKey)).toBe("انتخاب تم");
  });

  it("does not link to advertising or education wizard routes", () => {
    expect(plusMenuHrefs()).toEqual([]);
    for (const item of PLUS_MENU_ITEMS) {
      expect(JSON.stringify(item)).not.toMatch(/\/create/);
    }
  });
});

describe("creation action chips", () => {
  it("selecting each creation action creates the matching chip key", () => {
    expect(
      selectCreationAction(emptyComposerContext(), "advertising").creationAction,
    ).toBe("advertising");
    expect(
      selectCreationAction(emptyComposerContext(), "education").creationAction,
    ).toBe("education");
    expect(
      selectCreationAction(emptyComposerContext(), "general_image")
        .creationAction,
    ).toBe("general_image");
    expect(t("fa", "chat.actionAd")).toBe("📣 تبلیغ");
    expect(t("fa", "chat.actionEdu")).toBe("🎓 پست آموزشی");
    expect(t("fa", "chat.actionImage")).toBe("🖼 ساخت تصویر");
  });

  it("selecting another creation action replaces the previous primary action", () => {
    const first = selectCreationAction(emptyComposerContext(), "advertising");
    const next = selectCreationAction(first, "education");
    expect(next.creationAction).toBe("education");
  });

  it("removing the chip returns to automatic routing", () => {
    const selected = selectCreationAction(emptyComposerContext(), "advertising");
    expect(skillHintFromAction(selected.creationAction)).toBe("advertising");
    const cleared = clearCreationAction(selected);
    expect(cleared.creationAction).toBeNull();
    expect(skillHintFromAction(cleared.creationAction)).toBeNull();
  });

  it("lets theme and attachment coexist with an action chip", () => {
    let context = selectCreationAction(emptyComposerContext(), "advertising");
    context = setComposerTheme(context, "catalog-modern");
    context = setComposerAttachment(context, "shoe.jpg");
    expect(context).toEqual({
      creationAction: "advertising",
      themeId: "catalog-modern",
      attachmentName: "shoe.jpg",
    });

    context = selectCreationAction(context, "general_image");
    expect(context.creationAction).toBe("general_image");
    expect(context.themeId).toBe("catalog-modern");
    expect(context.attachmentName).toBe("shoe.jpg");
  });
});
