/**
 * Phase B chat persistence in a real browser, NEXT_PUBLIC_API_MODE=http.
 *
 *   npm run verify:chat:http
 *
 * Expects supabase, the backend on :8000, Inbucket on :54324, and the
 * frontend on :3000 built/served with NEXT_PUBLIC_API_MODE=http.
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const APP = process.env.VERIFY_APP_URL ?? "http://localhost:3000";
const API = process.env.VERIFY_API_URL ?? "http://127.0.0.1:8000";
const MAIL = process.env.VERIFY_MAIL_URL ?? "http://127.0.0.1:54324";
const SHOTS = process.env.VERIFY_SHOTS ?? null;
const STAMP = Date.now();
const EMAIL_A = `chat-ui-a-${STAMP}@example.com`;
const EMAIL_B = `chat-ui-b-${STAMP}@example.com`;
const MSG_A = "سلام، این یک پیام فارسی است.";
const MSG_B = "گفتگوی دوم";
const RENAMED = "دوم";
const MISSING_ID = "11111111-1111-4111-8111-111111111111";
const MOCK_TITLES = [
  "ماموریت ممیز کوچولو",
  "تبلیغ کفش سفید",
  "Elegant shoe ad",
];

const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

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

async function fetchCode(email) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const listing = await (await fetch(`${MAIL}/api/v1/messages`)).json();
    for (const message of listing.messages ?? []) {
      const recipients = (message.To ?? []).map((entry) => entry.Address);
      if (!recipients.includes(email)) continue;
      const body = await (await fetch(`${MAIL}/api/v1/message/${message.ID}`)).json();
      const match = /\b(\d{6})\b/.exec(body.Text ?? body.HTML ?? "");
      if (match) return match[1];
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return null;
}

async function login(page, email) {
  await page.goto(`${APP}/login?next=/chat`, { waitUntil: "domcontentloaded" });
  await page.getByLabel("ایمیل").waitFor({ timeout: 20000 });
  await page.getByLabel("ایمیل").fill(email);
  await page.getByRole("button", { name: "ورود با کد ایمیل" }).click();
  await page.getByLabel("کد تأیید").waitFor({ timeout: 30000 });
  const code = await fetchCode(email);
  check(`code delivered to ${email}`, code !== null, code ?? "never arrived");
  if (!code) throw new Error(`no verification code for ${email}`);
  await page.getByLabel("کد تأیید").fill(code);
  await page.getByRole("button", { name: "ورود", exact: true }).click();
  await page.waitForURL(/\/chat/, { timeout: 30000 });
}

async function accessToken(page) {
  return page.evaluate(() => {
    for (const key of Object.keys(window.localStorage)) {
      if (!key.startsWith("sb-")) continue;
      const raw = window.localStorage.getItem(key);
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw);
        const token =
          parsed?.access_token ??
          parsed?.currentSession?.access_token ??
          parsed?.session?.access_token;
        if (token) return token;
      } catch {
        /* ignore */
      }
    }
    return null;
  });
}

async function apiJson(page, method, pathname, body) {
  const token = await accessToken(page);
  const response = await fetch(`${API}${pathname}`, {
    method,
    headers: {
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(body !== undefined ? { "content-type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = text;
  }
  return { status: response.status, json };
}

async function send(page, text) {
  await page.locator('[data-chat="composer"] textarea').fill(text);
  await page.locator('[data-chat="send"]').click();
}

async function openOverflow(page, conversationId) {
  await page.locator(`[data-chat-row="${conversationId}"] [data-chat="conversation-menu-btn"]`).click();
  await page.locator('[data-chat="conversation-menu"]').waitFor({ timeout: 8000 });
}

const browser = await chromium.launch({ channel: "chrome" });
const consoleErrors = [];
const createdPosts = [];

try {
  console.log("\nHTTP chat persistence (signed-in)");
  const desktop = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await desktop.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().includes("/api/chat/conversations")) {
      createdPosts.push(request.url());
    }
  });

  await login(page, EMAIL_A);
  await page.locator('[data-chat="account-row"]').waitFor({ timeout: 15000 });
  check(
    "signed in",
    (await page.locator('[data-chat="account-row"]').getAttribute("data-signed-in")) === "true",
  );
  const bodyText = await page.locator("body").innerText();
  check(
    "not serving mock seed data",
    !MOCK_TITLES.some((title) => bodyText.includes(title)),
  );

  createdPosts.length = 0;
  const before = await apiJson(page, "GET", "/api/chat/conversations");
  check("API history empty before visiting /chat", Array.isArray(before.json) && before.json.length === 0);
  await page.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="empty"]').waitFor({ timeout: 15000 });
  await page.waitForTimeout(800);
  const createOnOpen = createdPosts.filter((url) => /\/api\/chat\/conversations\/?$/.test(new URL(url).pathname));
  check("opening /chat did not POST a conversation", createOnOpen.length === 0, String(createOnOpen.length));
  const afterOpen = await apiJson(page, "GET", "/api/chat/conversations");
  check("still no DB-backed chats", Array.isArray(afterOpen.json) && afterOpen.json.length === 0);
  await shot(page, "empty-chat");

  console.log("\nFirst Persian send");
  await send(page, MSG_A);
  await page.waitForURL(/\/chat\/[0-9a-f-]{36}/, { timeout: 20000 });
  const convA = new URL(page.url()).pathname.split("/").pop();
  check("URL became /chat/{id}", Boolean(convA && convA.includes("-")), convA);
  const userBubble = page.locator('[data-chat="user-message"]').filter({ hasText: MSG_A });
  await userBubble.first().waitFor({ timeout: 10000 });
  await page.reload({ waitUntil: "domcontentloaded" });
  await userBubble.first().waitFor({ timeout: 15000 });
  check("message remains after refresh", await userBubble.first().isVisible());

  console.log("\nTheme");
  await page.locator('[data-chat="plus"]').click();
  await page.locator('[data-chat-action="theme"]').click();
  await page.locator('[data-chat="theme-picker"]').waitFor({ timeout: 8000 });
  await page.getByRole("button", { name: "خمیری و بازیگوش" }).click();
  await page.locator('[data-chat="theme-chip"]').waitFor({ timeout: 8000 });
  check("theme chip shown", await page.locator('[data-chat="theme-chip"]').isVisible());
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="theme-chip"]').waitFor({ timeout: 15000 });
  check(
    "theme remains after refresh",
    (await page.locator('[data-chat="theme-chip"]').innerText()).includes("خمیری"),
  );

  console.log("\nAttachment");
  await userBubble.first().waitFor({ timeout: 10000 });
  await page.locator('input[type="file"]').first().setInputFiles({
    name: "smoke.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await page.locator('[data-chat="attachment-chip"]').waitFor({ timeout: 8000 });
  check("attachment chip before send", await page.locator('[data-chat="attachment-chip"]').isVisible());
  const posted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes(`/api/chat/conversations/${convA}/messages`),
    { timeout: 30000 },
  );
  await send(page, "این عکس");
  const postedResponse = await posted;
  check(
    "attachment message persisted",
    postedResponse.ok(),
    `HTTP ${postedResponse.status()}`,
  );
  const caption = page.locator('[data-chat="user-message"]').filter({ hasText: "این عکس" });
  await caption.first().waitFor({ timeout: 15000 });
  await page.reload({ waitUntil: "domcontentloaded" });
  await caption.first().waitFor({ timeout: 15000 });
  check("caption remains after refresh", await caption.first().isVisible());
  const detail = await apiJson(page, "GET", `/api/chat/conversations/${convA}`);
  const withFile = [...(detail.json?.messages ?? [])]
    .reverse()
    .find((message) => message.metadata_json?.attachment?.storage_path);
  const attachmentPath = withFile?.metadata_json?.attachment?.storage_path ?? null;
  check(
    "attachment storage_path present",
    Boolean(attachmentPath),
    withFile?.metadata_json?.attachment?.name ?? "",
  );
  if (attachmentPath) {
    const resolved = await apiJson(page, "POST", "/api/assets/resolve", { paths: [attachmentPath] });
    const url = resolved.json?.[attachmentPath];
    check("attachment signed URL issued", Boolean(url));
    if (url) {
      const image = await fetch(url);
      check("attachment signed URL loads", image.ok, `HTTP ${image.status}`);
    }
  }

  console.log("\nSecond chat");
  await page.locator('[data-chat="new-chat"]').click();
  await page.waitForURL(/\/chat\/?$/, { timeout: 10000 });
  await send(page, MSG_B);
  await page.waitForURL(/\/chat\/[0-9a-f-]{36}/, { timeout: 20000 });
  const convB = new URL(page.url()).pathname.split("/").pop();
  await page.locator(`[data-chat-item="${convA}"]`).waitFor({ timeout: 10000 });
  const listed = await apiJson(page, "GET", "/api/chat/conversations");
  const listedIds = (listed.json ?? []).map((item) => item.id);
  check("both chats in history", listedIds.includes(convA) && listedIds.includes(convB), String(listedIds.length));
  check("first chat visible in sidebar", await page.locator(`[data-chat-item="${convA}"]`).isVisible());
  check("second chat visible in sidebar", await page.locator(`[data-chat-item="${convB}"]`).isVisible());

  console.log("\nRename, pin, archive, restore");
  await openOverflow(page, convB);
  await page.locator('[data-chat="conv-rename"]').click();
  await page.locator('[data-chat="rename-input"]').fill(RENAMED);
  await page.locator('[data-chat="rename-input"]').press("Enter");
  await page.getByText(RENAMED).first().waitFor({ timeout: 8000 });
  check("renamed", (await page.locator(`[data-chat-item="${convB}"]`).innerText()).includes(RENAMED));

  await openOverflow(page, convB);
  await page.locator('[data-chat="conv-pin"]').click();
  await page.locator('[data-chat="group-pinned"]').waitFor({ timeout: 8000 });
  check("pinned group shown", await page.locator('[data-chat="group-pinned"]').isVisible());

  await openOverflow(page, convB);
  await page.locator('[data-chat="conv-archive"]').click();
  await page.locator(`[data-chat-item="${convB}"]`).waitFor({ state: "detached", timeout: 8000 });
  check("archived chat left the open list", !(await page.locator(`[data-chat-item="${convB}"]`).isVisible().catch(() => false)));

  await page.locator('[data-chat="empty"]').waitFor({ timeout: 10000 });
  await page.locator('[data-chat="account-row"]').click();
  await page.locator('[data-chat="account-menu"]').waitFor({ timeout: 8000 });
  await page.locator('[data-chat="account-archive"]').click({ force: true });
  await page.locator('[data-chat="archive-sheet"]').waitFor({ timeout: 8000 });
  await page.locator('[data-chat="archive-restore"]').click();
  await page.locator(`[data-chat-item="${convB}"]`).waitFor({ timeout: 8000 });
  check("restored chat returned", await page.locator(`[data-chat-item="${convB}"]`).isVisible());
  await page.keyboard.press("Escape").catch(() => {});

  console.log("\nLogout and login");
  await page.locator('[data-chat="account-row"]').click();
  await page.locator('[data-chat="account-signout"]').click();
  await page.waitForURL(/\/chat\/?$/, { timeout: 15000 });
  await page.waitForFunction(
    () => document.querySelector('[data-chat="account-row"]')?.getAttribute("data-signed-in") === "false",
    null,
    { timeout: 15000 },
  );
  check(
    "signed out",
    (await page.locator('[data-chat="account-row"]').getAttribute("data-signed-in")) === "false",
  );
  check(
    "chats disappeared immediately",
    (await page.locator("[data-chat-item]").count()) === 0,
  );

  await login(page, EMAIL_A);
  await page.locator(`[data-chat-item="${convA}"]`).waitFor({ timeout: 15000 });
  check("chats returned after login", await page.locator(`[data-chat-item="${convA}"]`).isVisible());
  check("second chat returned", await page.locator(`[data-chat-item="${convB}"]`).isVisible());

  console.log("\nDelete");
  await openOverflow(page, convB);
  await page.locator('[data-chat="conv-delete"]').click();
  await page.locator('[data-chat="delete-confirm"]').waitFor({ timeout: 8000 });
  await page.locator('[data-chat="confirm-ok"]').click();
  await page.locator(`[data-chat-item="${convB}"]`).waitFor({ state: "detached", timeout: 8000 });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator(`[data-chat-item="${convA}"]`).waitFor({ timeout: 15000 });
  check(
    "deleted chat still gone after refresh",
    (await page.locator(`[data-chat-item="${convB}"]`).count()) === 0,
  );

  console.log("\nUnknown id");
  await page.goto(`${APP}/chat/${MISSING_ID}`, { waitUntil: "domcontentloaded" });
  await page.getByText("این گفتگو پیدا نشد.").waitFor({ timeout: 15000 });
  check("generic not-found for missing id", await page.getByText("این گفتگو پیدا نشد.").isVisible());

  console.log("\nSecond account");
  const other = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const otherPage = await other.newPage();
  await login(otherPage, EMAIL_B);
  await otherPage.goto(`${APP}/chat/${convA}`, { waitUntil: "domcontentloaded" });
  await otherPage.getByText("این گفتگو پیدا نشد.").waitFor({ timeout: 15000 });
  check(
    "second account cannot open first account’s chat",
    await otherPage.getByText("این گفتگو پیدا نشد.").isVisible(),
  );
  const leaked = await otherPage.locator("body").innerText();
  check("second account does not see first message", !leaked.includes(MSG_A));
  await other.close();

  const noise = consoleErrors.filter(
    (text) =>
      !/favicon|React DevTools|Download the React|net::ERR|404 \(Not Found\)/.test(text),
  );
  check("no console errors", noise.length === 0, noise.slice(0, 2).join(" | "));
  await shot(page, "after-http-smoke");
  await desktop.close();
} catch (error) {
  failures.push(`threw: ${error.message}`);
  console.log(`\n  ${error.stack?.split("\n").slice(0, 4).join("\n  ")}`);
  try {
    const openPage = browser.contexts()[0]?.pages()[0];
    if (openPage) {
      await openPage.screenshot({ path: "verify-chat-http-failure.png" }).catch(() => {});
      const snippet = (await openPage.locator("body").innerText()).slice(0, 800);
      console.log(`\n  page text:\n  ${snippet.replaceAll("\n", "\n  ")}`);
    }
  } catch {
    /* ignore */
  }
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
