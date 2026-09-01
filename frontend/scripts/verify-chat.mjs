/**
 * Walks the Phase A chat prototype in a real browser.
 *
 *   npm run verify:chat
 *
 * Expects the frontend on :3000. Override with VERIFY_APP_URL.
 * Set VERIFY_SHOTS to a directory to save checklist screenshots.
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const APP = process.env.VERIFY_APP_URL ?? "http://localhost:3000";
const SHOTS = process.env.VERIFY_SHOTS ?? null;

const failures = [];

function check(label, ok, detail = "") {
  console.log(`  [${ok ? "ok  " : "FAIL"}] ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures.push(label);
}

async function shot(page, name) {
  if (!SHOTS) return;
  await mkdir(SHOTS, { recursive: true });
  await page.screenshot({
    path: path.join(SHOTS, `${name}.png`),
    fullPage: false,
  });
}

async function visible(page, selector) {
  return page
    .locator(selector)
    .first()
    .isVisible()
    .catch(() => false);
}

const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

const browser = await chromium.launch({ channel: "chrome" });
const consoleErrors = [];

try {
  console.log("\nDesktop chat prototype");
  const desktop = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await desktop.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));

  await page.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="empty"]').waitFor({ timeout: 15000 });
  check("empty /chat", await visible(page, '[data-chat="empty"]'));
  check("composer visible", await visible(page, '[data-chat="composer"]'));
  check("account row", await visible(page, '[data-chat="account-row"]'));
  await page.locator('[data-chat="group-pinned"]').waitFor({ timeout: 8000 });
  check("pinned group", await visible(page, '[data-chat="group-pinned"]'));
  await page.locator('[data-chat="account-row"]').click();
  await page.locator('[data-chat="account-menu"]').waitFor({ timeout: 8000 });
  check("account menu", await visible(page, '[data-chat="account-menu"]'));
  check(
    "account menu surface",
    (await page.locator('[data-chat="account-menu"]').getAttribute("data-chat-surface")) ===
      "popover",
  );
  check(
    "account menu chrome RTL",
    (await page.locator('[data-chat="account-menu"]').getAttribute("data-chat-dir")) === "rtl",
  );
  check("archived chats entry", await visible(page, '[data-chat="account-archive"]'));
  await page.locator('[data-chat="account-archive"]').click();
  await page.locator('[data-chat="archive-sheet"]').waitFor({ timeout: 8000 });
  check("archive sheet", await visible(page, '[data-chat="archive-sheet"]'));
  check(
    "archived conversation listed",
    await visible(page, '[data-chat-archived="conv-failed"]'),
  );
  await page.keyboard.press("Escape");
  await page.locator('[data-chat="archive-sheet"]').waitFor({ state: "detached", timeout: 8000 }).catch(() => {});

  await page.locator('[data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await page.locator('[data-chat="conversation-menu"]').waitFor({ timeout: 8000 });
  check("conversation menu", await visible(page, '[data-chat="conversation-menu"]'));
  check(
    "conversation menu RTL",
    (await page.locator('[data-chat="conversation-menu"]').getAttribute("data-chat-dir")) ===
      "rtl",
  );
  check(
    "delete action is destructive",
    (await page.locator('[data-chat="conv-delete"]').getAttribute("data-destructive")) ===
      "true",
  );
  await page.locator('[data-chat="conv-share"]').click();
  await page.locator('[data-chat="share-sheet"]').waitFor({ timeout: 8000 });
  check("share sheet", await visible(page, '[data-chat="share-sheet"]'));
  check("share copy text", await visible(page, '[data-chat="share-copy"]'));
  check(
    "no fake public link",
    await page.getByText("لینک عمومی هنوز آماده نیست.").isVisible(),
  );
  await page.keyboard.press("Escape");
  await page.locator('[data-chat="share-sheet"]').waitFor({ state: "detached", timeout: 8000 }).catch(() => {});

  await page.locator('[data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await page.locator('[data-chat="conv-delete"]').click();
  await page.locator('[data-chat="delete-confirm"]').waitFor({ timeout: 8000 });
  check("delete confirm", await visible(page, '[data-chat="delete-confirm"]'));
  check(
    "delete confirm is destructive",
    (await page.locator('[data-chat="delete-confirm"]').getAttribute("data-destructive")) ===
      "true",
  );
  await page.locator('[data-chat="confirm-cancel"]').click();
  await page.locator('[data-chat="delete-confirm"]').waitFor({ state: "detached", timeout: 8000 }).catch(() => {});

  await page.locator('[data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await page.locator('[data-chat="conv-rename"]').click();
  const rename = page.locator('[data-chat="rename-input"]');
  await rename.waitFor({ timeout: 8000 });
  await rename.fill("کفش تست");
  await rename.press("Enter");
  await page.getByText("کفش تست").waitFor({ timeout: 8000 });
  check("rename works", await visible(page, '[data-chat-row="conv-shoe"]'));

  await page.locator('[data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await page.locator('[data-chat="conv-pin"]').click();
  await page.locator('[data-chat="group-pinned"] [data-chat-row="conv-shoe"]').waitFor({ timeout: 8000 });
  check(
    "pin moves into pinned group",
    await visible(page, '[data-chat="group-pinned"] [data-chat-row="conv-shoe"]'),
  );
  await page.locator('[data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await page.locator('[data-chat="conv-unpin"]').click();
  await page.waitForFunction(
    () => !document.querySelector('[data-chat="group-pinned"] [data-chat-row="conv-shoe"]'),
    null,
    { timeout: 8000 },
  );
  check(
    "unpin leaves pinned group",
    !(await visible(page, '[data-chat="group-pinned"] [data-chat-row="conv-shoe"]')),
  );

  await page.locator('[data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await page.locator('[data-chat="conv-archive"]').click();
  await page.waitForFunction(
    () => !document.querySelector('[data-chat-row="conv-shoe"]'),
    null,
    { timeout: 8000 },
  );
  check("archive hides from history", !(await visible(page, '[data-chat-row="conv-shoe"]')));
  await page.locator('[data-chat="account-row"]').click();
  await page.locator('[data-chat="account-archive"]').click();
  await page.locator('[data-chat-archived="conv-shoe"] [data-chat="archive-restore"]').click();
  await page.keyboard.press("Escape");
  await page.locator('[data-chat="archive-sheet"]').waitFor({ state: "detached", timeout: 8000 }).catch(() => {});
  await page.locator('[data-chat-row="conv-shoe"]').waitFor({ timeout: 8000 });
  check("restore returns conversation", await visible(page, '[data-chat-row="conv-shoe"]'));
  await shot(page, "desktop-empty");

  await page.locator('[data-chat="plus"]').click();
  check("+ menu open", await visible(page, '[data-chat="plus-menu"]'));
  const plusActions = await page
    .locator('[data-chat="plus-menu"] [data-chat-action]')
    .evaluateAll((els) => els.map((el) => el.getAttribute("data-chat-action")));
  check(
    "five plus menu items",
    plusActions.join(",") === "advertising,education,generate,upload,theme",
  );
  await shot(page, "desktop-plus");
  await page.locator('[data-chat-action="advertising"]').click();
  await page.locator('[data-chat="action-chip"]').waitFor({ timeout: 8000 });
  check(
    "advertising action chip",
    (await page.locator('[data-chat="action-chip"]').getAttribute("data-action")) ===
      "advertising",
  );
  check(
    "action chip does not start generation",
    !(await visible(page, '[data-chat="generation-placeholder"]')),
  );
  await page.locator('[data-chat="plus"]').click();
  await page.locator('[data-chat-action="theme"]').click();
  check("theme picker open", await visible(page, '[data-chat="theme-picker"]'));
  await shot(page, "desktop-theme");
  await page.getByRole("button", { name: "خمیری و بازیگوش" }).click();
  await page.locator('[data-chat="theme-chip"]').waitFor({ timeout: 10000 });
  check("active theme selected", await visible(page, '[data-chat="theme-chip"]'));

  await page.goto(`${APP}/chat/conv-decimals`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="image-artifact"]').waitFor({ timeout: 15000 });
  check(
    "Persian 1:1 artifact",
    (await page.locator('[data-chat="image-artifact"]').getAttribute("data-aspect")) ===
      "1:1",
  );
  await shot(page, "desktop-persian-square");

  await page.goto(`${APP}/chat/conv-shoe`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="image-artifact"]').waitFor({ timeout: 15000 });
  check(
    "4:5 artifact",
    (await page.locator('[data-chat="image-artifact"]').getAttribute("data-aspect")) ===
      "4:5",
  );
  await shot(page, "desktop-portrait");

  await page.goto(`${APP}/chat/conv-english`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="assistant-message"][dir="ltr"]').waitFor({
    timeout: 15000,
  });
  check("English conversation LTR", await visible(page, '[dir="ltr"]'));
  await shot(page, "desktop-english");

  await page.goto(`${APP}/chat/conv-mixed`, { waitUntil: "domcontentloaded" });
  await page.getByText("luxury ad").waitFor({ timeout: 15000 });
  check("mixed Persian/English conversation", true);
  await shot(page, "desktop-mixed");

  await page.goto(`${APP}/chat/conv-failed`, { waitUntil: "domcontentloaded" });
  check(
    "failed generation copy",
    await page
      .locator('[data-chat="generation-failed"]')
      .waitFor({ timeout: 15000 })
      .then(() => true, () => false),
  );
  await shot(page, "desktop-failed");
  await page.getByRole("button", { name: "دوباره بساز" }).click();
  check(
    "retry restores activity",
    await page.locator('[data-chat="activity"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(page, "desktop-retry");

  await page.goto(`${APP}/chat/conv-long`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="user-message"]').first().waitFor({ timeout: 15000 });
  check("long conversation", (await page.locator('[data-chat="user-message"]').count()) > 5);
  await shot(page, "desktop-long");

  await page.locator('[data-chat="sidebar-toggle"]').click();
  const collapsed = await page
    .locator('[data-chat="sidebar"]')
    .waitFor({ timeout: 5000 })
    .then(async () => {
      await page.waitForFunction(
        () =>
          document.querySelector('[data-chat="sidebar"]')?.getAttribute("data-collapsed") ===
          "true",
        null,
        { timeout: 3000 },
      );
      return true;
    }, () => false);
  check("collapsed sidebar", collapsed);
  await shot(page, "desktop-collapsed");
  await page.locator('[data-chat="sidebar-toggle"]').click();

  await page.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="empty"]').waitFor({ timeout: 15000 });
  await page.locator('[data-chat="composer"] textarea').fill("سلام، چطوری؟");
  await page.locator('[data-chat="send"]:not([disabled])').click();
  check(
    "thinking activity",
    await page.locator('[data-chat="activity"][data-chat-phase="thinking"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(page, "desktop-thinking");
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 15000 });
  check(
    "thinking removed after answer",
    !(await visible(page, '[data-chat-phase="thinking"]')),
  );

  await page.locator('[data-chat="new-chat"]').click();
  await page.locator('[data-chat="empty"]').waitFor({ timeout: 8000 });
  await page.locator('[data-chat="plus"]').click();
  await page.locator('[data-chat-action="education"]').click();
  await page.locator('[data-chat="composer"] textarea').fill("یه پست آموزشی بامزه بساز");
  await page.locator('[data-chat="send"]:not([disabled])').click();
  check(
    "preparing education",
    await page.locator('[data-chat-phase="preparing_education"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(page, "desktop-preparing-education");
  check(
    "education generating image phase",
    await page.locator('[data-chat-phase="generating_image"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(page, "desktop-generating-image");
  await page.locator('[data-chat="image-artifact"]').waitFor({ timeout: 20000 });
  check("education image ready", await visible(page, '[data-chat="image-artifact"]'));

  await page.locator('[data-chat="new-chat"]').click();
  await page.locator('[data-chat="plus"]').click();
  await page.locator('[data-chat-action="advertising"]').click();
  await page.locator('[data-chat="composer"] textarea').fill("یه تبلیغ از این کفش بساز");
  await page.locator('[data-chat="send"]:not([disabled])').click();
  check(
    "preparing advertising",
    await page.locator('[data-chat-phase="preparing_advertising"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(page, "desktop-preparing-advertising");
  await page.locator('[data-chat="generation-placeholder"], [data-chat="image-artifact"]').first().waitFor({
    timeout: 20000,
  });
  await page.locator('[data-chat="image-artifact"]').waitFor({ timeout: 20000 });

  await page.locator('[data-chat="plus"]').click();
  await page.locator('[data-chat-action="upload"]').click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "shoe.jpg",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await page.locator('[data-chat="attachment-chip"]').waitFor({ timeout: 8000 });
  check("attachment chip", await visible(page, '[data-chat="attachment-chip"]'));
  await shot(page, "desktop-attachment");
  await desktop.close();

  console.log("\nMobile chat prototype");
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const phone = await mobile.newPage();
  await phone.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await phone.locator('[data-chat="empty"]').waitFor({ timeout: 15000 });
  check("mobile empty chat", await visible(phone, '[data-chat="empty"]'));
  check("mobile composer", await visible(phone, '[data-chat="composer"]'));
  await shot(phone, "mobile-empty");

  await phone.locator('[data-chat="open-sidebar"]').click();
  check("sidebar sheet", await visible(phone, '[data-chat="sidebar-sheet"]'));
  check(
    "mobile account row",
    await visible(phone, '[data-chat="sidebar-sheet"] [data-chat="account-row"]'),
  );
  await phone.locator('[data-chat="sidebar-sheet"] [data-chat="account-row"]').click();
  await phone.locator('[data-chat="account-menu"]').waitFor({ timeout: 8000 });
  check("mobile account menu", await visible(phone, '[data-chat="account-menu"]'));
  check(
    "mobile account sheet",
    (await phone.locator('[data-chat="account-menu"]').getAttribute("data-chat-surface")) ===
      "sheet",
  );
  await phone.keyboard.press("Escape");
  await phone.locator('[data-chat="account-menu"]').waitFor({ state: "detached", timeout: 8000 });
  check("sidebar remains after account menu", await visible(phone, '[data-chat="sidebar-sheet"]'));

  await phone.locator('[data-chat="sidebar-sheet"] [data-chat-row="conv-shoe"] [data-chat="conversation-menu-btn"]').click();
  await phone.locator('[data-chat="conversation-menu"]').waitFor({ timeout: 8000 });
  check("mobile conversation action sheet", await visible(phone, '[data-chat="conversation-menu"]'));
  check(
    "mobile conversation is a sheet",
    (await phone.locator('[data-chat="conversation-menu"]').getAttribute("data-chat-surface")) ===
      "sheet",
  );
  await phone.keyboard.press("Escape");
  await phone.locator('[data-chat="conversation-menu"]').waitFor({ state: "detached", timeout: 8000 });
  check("sidebar remains after conversation menu", await visible(phone, '[data-chat="sidebar-sheet"]'));
  await shot(phone, "mobile-sidebar");
  await phone.locator('[data-chat="sidebar-sheet"] [data-chat="sidebar-toggle"]').click();
  await phone.locator('[data-chat="sidebar-sheet"]').waitFor({ state: "detached", timeout: 8000 });

  await phone.locator('[data-chat="plus"]').click();
  await phone.locator('[data-chat="plus-menu"]').waitFor({ timeout: 8000 });
  check("mobile + sheet", await visible(phone, '[data-chat="plus-menu"]'));
  await shot(phone, "mobile-plus");
  await phone.locator('[data-chat-action="theme"]').click({ force: true });
  await phone.locator('[data-chat="theme-picker"]').waitFor({ timeout: 8000 });
  check("mobile theme picker", await visible(phone, '[data-chat="theme-picker"]'));
  await shot(phone, "mobile-theme");
  await phone.keyboard.press("Escape");
  await phone.locator('[data-chat="theme-picker"]').waitFor({ state: "detached", timeout: 8000 }).catch(() => {});

  await phone.goto(`${APP}/chat/conv-decimals`, { waitUntil: "domcontentloaded" });
  await phone.locator('[data-chat="image-artifact"]').waitFor({ timeout: 15000 });
  check("mobile generated image", await visible(phone, '[data-chat="image-artifact"]'));
  await shot(phone, "mobile-image");

  await phone.goto(`${APP}/chat/conv-mixed`, { waitUntil: "domcontentloaded" });
  check(
    "mobile mixed text",
    await phone
      .getByText("luxury ad")
      .waitFor({ timeout: 15000 })
      .then(() => true, () => false),
  );

  await phone.goto(`${APP}/chat/conv-long`, { waitUntil: "domcontentloaded" });
  check(
    "long Persian message",
    await phone
      .getByText("یه پست آموزشی بلند")
      .waitFor({ timeout: 15000 })
      .then(() => true, () => false),
  );

  await phone.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await phone.locator('[data-chat="empty"]').waitFor({ timeout: 15000 });
  await phone.locator('[data-chat="composer"] textarea').fill("سلام");
  await phone.locator('[data-chat="send"]:not([disabled])').click();
  check(
    "mobile thinking",
    await phone.locator('[data-chat-phase="thinking"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(phone, "mobile-thinking");
  await phone.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 15000 });

  await phone.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await phone.locator('[data-chat="plus"]').click();
  await phone.locator('[data-chat-action="generate"]').click();
  await phone.locator('[data-chat="composer"] textarea').fill("یه تصویر رنگی بساز");
  await phone.locator('[data-chat="send"]:not([disabled])').click();
  check(
    "mobile generating",
    await phone.locator('[data-chat="generation-placeholder"]').waitFor({ timeout: 8000 }).then(
      () => true,
      () => false,
    ),
  );
  await shot(phone, "mobile-generating");
  await phone.locator('[data-chat="image-artifact"]').waitFor({ timeout: 20000 });

  await phone.goto(`${APP}/chat/conv-failed`, { waitUntil: "domcontentloaded" });
  check(
    "mobile failed",
    await phone.locator('[data-chat="generation-failed"]').waitFor({ timeout: 15000 }).then(
      () => true,
      () => false,
    ),
  );

  await phone.locator('input[type="file"]').setInputFiles({
    name: "note.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  check(
    "mobile attachment chip",
    await phone
      .locator('[data-chat="attachment-chip"]')
      .waitFor({ timeout: 8000 })
      .then(() => true, () => false),
  );
  await shot(phone, "mobile-attachment");

  const noise = consoleErrors.filter(
    (text) => !/favicon|React DevTools|Download the React/.test(text),
  );
  check("no console errors", noise.length === 0, noise.slice(0, 2).join(" | "));
  await mobile.close();
} catch (error) {
  failures.push(`threw: ${error.message}`);
  console.log(`\n  ${error.stack?.split("\n").slice(0, 4).join("\n  ")}`);
} finally {
  await browser.close();
}

console.log();
if (failures.length > 0) {
  console.log(`${failures.length} check(s) failed:`);
  failures.forEach((failure) => console.log(`  - ${failure}`));
  process.exit(1);
}
console.log("all checks passed");
