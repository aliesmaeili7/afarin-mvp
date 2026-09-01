/**
 * Phase C live/HTTP chat smoke in a real browser.
 *
 *   npm run verify:chat:phase-c
 *
 * Expects supabase, Inbucket on :54324, API on :8000 with OpenRouter,
 * and the frontend on :3000 with NEXT_PUBLIC_API_MODE=http.
 *
 * Resume remaining checks without more paid images:
 *
 *   VERIFY_EXISTING_EMAIL=... VERIFY_FROM_STEP=10 npm run verify:chat:phase-c
 */
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const APP = process.env.VERIFY_APP_URL ?? "http://localhost:3000";
const API = process.env.VERIFY_API_URL ?? "http://127.0.0.1:8000";
const MAIL = process.env.VERIFY_MAIL_URL ?? "http://127.0.0.1:54324";
const IMAGE_MS = Number(process.env.VERIFY_IMAGE_MS ?? 180_000);
const STAMP = Date.now();
const EMAIL_A = process.env.VERIFY_EXISTING_EMAIL ?? `chat-c-a-${STAMP}@example.com`;
const EMAIL_B = `chat-c-b-${STAMP}@example.com`;
const FROM_STEP = Number(process.env.VERIFY_FROM_STEP ?? 1);

const FORMAL = /درخواست شما در حال پردازش|لطفاً صبر کنید|orchestrator|OpenRouter|\bGPT\b|skill name/i;
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
const notes = [];

function check(label, ok, detail = "") {
  console.log(`  [${ok ? "ok  " : "FAIL"}] ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures.push(label);
}

function note(text) {
  notes.push(text);
  console.log(`  note: ${text}`);
}

function productPng() {
  const dest = path.join(tmpdir(), `afarin-phase-c-${STAMP}.png`);
  const py = spawnSync(
    "uv",
    [
      "run",
      "python",
      "-c",
      `from PIL import Image; Image.new("RGB",(320,400),(196,90,40)).save(${JSON.stringify(dest)})`,
    ],
    { cwd: path.resolve(import.meta.dirname, "../../backend"), encoding: "utf8" },
  );
  if (py.status !== 0) {
    throw new Error(`could not paint product PNG: ${py.stderr || py.stdout}`);
  }
  return readFileSync(dest);
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

async function login(page, email, next = "/chat") {
  await page.goto(`${APP}/login?next=${next}`, { waitUntil: "domcontentloaded" });
  await page.getByLabel("ایمیل").waitFor({ timeout: 20000 });
  await page.getByLabel("ایمیل").fill(email);
  await page.getByRole("button", { name: "ورود با کد ایمیل" }).click();
  await page.getByLabel("کد تأیید").waitFor({ timeout: 30000 });
  const code = await fetchCode(email);
  check(`code delivered to ${email}`, code !== null, code ?? "never arrived");
  if (!code) throw new Error(`no verification code for ${email}`);
  await page.getByLabel("کد تأیید").fill(code);
  await page.getByRole("button", { name: "ورود", exact: true }).click();
  await page.waitForURL(new RegExp(next.replace("/", "\\/")), { timeout: 30000 });
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

async function pickChip(page, action) {
  await page.locator('[data-chat="plus"]').click();
  await page.locator(`[data-chat-action="${action}"]`).click();
  await page.locator('[data-chat="action-chip"]').waitFor({ timeout: 8000 });
}

async function newChat(page) {
  await page.locator('[data-chat="new-chat"]').click();
  await page.waitForURL(/\/chat\/?$/, { timeout: 15000 });
}

async function convId(page) {
  await page.waitForURL(/\/chat\/[0-9a-f-]{36}/, { timeout: 30000 });
  return new URL(page.url()).pathname.split("/").pop();
}

function lastAssistant(detail) {
  const messages = detail?.messages ?? [];
  return [...messages].reverse().find((item) => item.role === "assistant") ?? null;
}

function userCount(detail) {
  return (detail?.messages ?? []).filter((item) => item.role === "user").length;
}

function toneOk(text, language) {
  if (!text) return false;
  if (FORMAL.test(text)) return false;
  if (language === "fa") return /[\u0600-\u06FF]/.test(text);
  return /[A-Za-z]/.test(text);
}

async function waitForImage(page) {
  const result = page.locator(
    '[data-chat="image-artifact"] img, [data-chat="generation-failed"]',
  );
  await result.first().waitFor({ timeout: IMAGE_MS });
  const failed = await page.locator('[data-chat="generation-failed"]').count();
  return failed === 0;
}

const browser = await chromium.launch({ channel: "chrome" });
const consoleErrors = [];
const product = productPng();

try {
  const desktop = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await desktop.newPage();
  page.setDefaultTimeout(20000);
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));

  console.log("\nSign in");
  await login(page, EMAIL_A);
  await page.locator('[data-chat="account-row"]').waitFor({ timeout: 15000 });
  check(
    "signed in",
    (await page.locator('[data-chat="account-row"]').getAttribute("data-signed-in")) ===
      "true",
  );
  const bodyText = await page.locator("body").innerText();
  check(
    "not serving mock seed data",
    !MOCK_TITLES.some((title) => bodyText.includes(title)),
  );

  let eduConv;
  let eduArtifact;
  let imageConv;
  let genOk = false;
  let detail;

  if (FROM_STEP >= 10) {
    const listing = await apiJson(page, "GET", "/api/chat/conversations");
    const rows = Array.isArray(listing.json) ? listing.json : [];
    for (const row of rows) {
      const one = await apiJson(page, "GET", `/api/chat/conversations/${row.id}`);
      const ready = (one.json?.artifacts ?? []).find(
        (item) => item.status === "ready" && item.storage_path,
      );
      if (ready) {
        eduConv = row.id;
        eduArtifact = ready;
        imageConv = row.id;
        break;
      }
    }
    check("found existing ready artifact for remaining checks", Boolean(imageConv), imageConv);
    if (!imageConv) {
      throw new Error("VERIFY_FROM_STEP>=10 needs a conversation with a ready image");
    }
  } else {
  console.log("\n1. Persian general chat");
  await send(page, "سلام، امروز چه کمکی ازت برمیاد؟");
  const convFa = await convId(page);
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 60000 });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convFa}`);
  let assistant = lastAssistant(detail.json);
  note(`FA reply: ${(assistant?.content || "").slice(0, 120)}`);
  check("Persian reply language", assistant?.language === "fa", assistant?.language);
  check("Persian tone", toneOk(assistant?.content || "", "fa"), assistant?.content?.slice(0, 80));
  check("general_chat route", assistant?.metadata_json?.route === "general_chat", assistant?.metadata_json?.route);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 15000 });
  check("Persian reply survives refresh", await page.locator('[data-chat="assistant-message"]').first().isVisible());

  console.log("\n2. English general chat");
  await newChat(page);
  await send(page, "Please answer in English: what can you make for my shop?");
  const convEn = await convId(page);
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 60000 });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convEn}`);
  assistant = lastAssistant(detail.json);
  note(`EN reply: ${(assistant?.content || "").slice(0, 120)}`);
  check("English reply language", assistant?.language === "en", assistant?.language);
  check("English tone", toneOk(assistant?.content || "", "en"));

  console.log("\n3. Mixed Persian + English terms stay FA");
  await newChat(page);
  await send(page, "برای Instagram یه کپشن کوتاه بده");
  const convMixed = await convId(page);
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 60000 });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convMixed}`);
  assistant = lastAssistant(detail.json);
  note(`mixed reply: ${(assistant?.content || "").slice(0, 120)}`);
  check("mixed reply stays Persian", assistant?.language === "fa", assistant?.language);
  check("mixed tone", toneOk(assistant?.content || "", "fa"));

  console.log("\n4. Education via normal text + English artifact + busy lock");
  await newChat(page);
  const postedEdu = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      /\/api\/chat\/conversations\/?$/.test(new URL(response.url()).pathname),
    { timeout: 90000 },
  );
  await send(
    page,
    "برای کلاس ششم یه پوستر آموزشی درباره اعداد اعشاری بساز ولی متنش انگلیسی باشه",
  );
  eduConv = await convId(page);
  const eduPost = await postedEdu;
  check("education turn accepted", eduPost.ok(), `HTTP ${eduPost.status()}`);
  await page.locator('[data-chat="generation-placeholder"], [data-chat="image-artifact"]').first().waitFor({
    timeout: 30000,
  });
  const busyPost = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes(`/api/chat/conversations/${eduConv}/messages`),
    { timeout: 20000 },
  );
  await send(page, "یه چیز دیگه هم بساز");
  const busyRes = await busyPost;
  check("second send blocked while generating", busyRes.status() === 409, `HTTP ${busyRes.status()}`);
  const imageOk = await waitForImage(page);
  check("education image ready", imageOk);
  detail = await apiJson(page, "GET", `/api/chat/conversations/${eduConv}`);
  assistant = lastAssistant(detail.json);
  note(`edu reply: ${(assistant?.content || "").slice(0, 120)}`);
  check("education route", assistant?.metadata_json?.route === "education", assistant?.metadata_json?.route);
  check(
    "reply FA / artifact EN",
    assistant?.language === "fa" && assistant?.metadata_json?.artifact_language === "en",
    `${assistant?.language}/${assistant?.metadata_json?.artifact_language}`,
  );
  check("education tone", toneOk(assistant?.content || "", "fa"));
  const eduUsers = userCount(detail.json);
  check("busy send did not add a second user turn", eduUsers === 1, String(eduUsers));
  eduArtifact = (detail.json?.artifacts ?? [])[0];
  check("education storage is education/", Boolean(eduArtifact?.storage_path?.includes("/education/")));
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="image-artifact"] img').first().waitFor({ timeout: 20000 });
  check("education image survives refresh", await page.locator('[data-chat="image-artifact"] img').first().isVisible());

  console.log("\n5. Education via + chip skips router");
  await newChat(page);
  await pickChip(page, "education");
  await send(page, "یه پست آموزشی بامزه درباره کسر بساز");
  const convChip = await convId(page);
  const chipImage = await waitForImage(page);
  check("chip education image ready", chipImage);
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convChip}`);
  assistant = lastAssistant(detail.json);
  check("chip skipped orchestrator", assistant?.metadata_json?.orchestrator_called === false);
  check("chip education route", assistant?.metadata_json?.route === "education");

  console.log("\n6. Advertising without image clarifies");
  await newChat(page);
  await pickChip(page, "advertising");
  await send(page, "یه تبلیغ از این کفش بساز");
  const convClarify = await convId(page);
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 30000 });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convClarify}`);
  assistant = lastAssistant(detail.json);
  note(`ads clarify: ${(assistant?.content || "").slice(0, 120)}`);
  check("ads without image is clarify", assistant?.metadata_json?.route === "clarify");
  check("no paid ads artifact", (detail.json?.artifacts ?? []).length === 0);
  check("clarify tone", toneOk(assistant?.content || "", "fa"));

  console.log("\n7. Advertising with product image");
  await newChat(page);
  await page.locator('input[type="file"]').first().setInputFiles({
    name: "shoe.png",
    mimeType: "image/png",
    buffer: product,
  });
  await page.locator('[data-chat="attachment-chip"]').waitFor({ timeout: 8000 });
  await pickChip(page, "advertising");
  await send(page, "یه تبلیغ از این بساز");
  const convAd = await convId(page);
  const adOk = await waitForImage(page);
  check("advertising image ready", adOk);
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convAd}`);
  assistant = lastAssistant(detail.json);
  const adArtifact = (detail.json?.artifacts ?? [])[0];
  check("ads route", assistant?.metadata_json?.route === "advertising");
  check("ads storage is campaigns/", Boolean(adArtifact?.storage_path?.includes("/campaigns/")));
  if (!adOk) {
    note(
      `ads image failed (status=${adArtifact?.status}): live provider did not return a candidate`,
    );
  }

  console.log("\n8. /create still works");
  await page.goto(`${APP}/create`, { waitUntil: "domcontentloaded" });
  await page.getByText("عکس محصولت رو آپلود کن").waitFor({ timeout: 15000 });
  check("legacy /create wizard still opens", await page.getByText("عکس محصولت رو آپلود کن").isVisible());
  await page.goto(`${APP}/chat/${convAd}`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="assistant-message"]').first().waitFor({ timeout: 15000 });

  console.log("\n9. General image");
  await newChat(page);
  await pickChip(page, "generate");
  await send(page, "یه تصویر از یک فنجان چای بساز");
  const convImg = await convId(page);
  genOk = await waitForImage(page);
  check("general image ready", genOk);
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convImg}`);
  assistant = lastAssistant(detail.json);
  const genArtifact = (detail.json?.artifacts ?? [])[0];
  check("general_image route", assistant?.metadata_json?.route === "general_image");
  check(
    "general image stored under chat/",
    Boolean(genArtifact?.storage_path?.includes("/chat/") && genArtifact?.storage_path?.includes("/artifacts/")),
  );
  if (genOk) {
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.locator('[data-chat="image-artifact"] img').first().waitFor({ timeout: 20000 });
    check("general image survives refresh", await page.locator('[data-chat="image-artifact"] img').first().isVisible());
  } else {
    note(
      `general image failed (status=${genArtifact?.status}): skipping refresh image check`,
    );
    check("failed generation UI shown", await page.locator('[data-chat="generation-failed"]').first().isVisible());
  }

  const imageConvFromRun = genOk ? convImg : eduConv;
  imageConv = imageConvFromRun;
  } // FROM_STEP < 10

  console.log("\n10. Failed generation retry does not duplicate the user");
  await newChat(page);
  await page.locator('input[type="file"]').first().setInputFiles({
    name: "tiny.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await pickChip(page, "advertising");
  await send(page, "یه تبلیغ از این بساز");
  const convFail = await convId(page);
  await page.locator('[data-chat="generation-failed"]').waitFor({ timeout: IMAGE_MS });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convFail}`);
  const usersBefore = userCount(detail.json);
  await page.getByRole("button", { name: "دوباره بساز" }).click();
  await page.waitForTimeout(2000);
  await page.locator('[data-chat="generation-placeholder"], [data-chat="generation-failed"], [data-chat="image-artifact"]').first().waitFor({
    timeout: IMAGE_MS,
  });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${convFail}`);
  check(
    "retry did not duplicate the user message",
    userCount(detail.json) === usersBefore,
    `${usersBefore} → ${userCount(detail.json)}`,
  );

  console.log("\n11. Use as reference");
  await page.goto(`${APP}/chat/${imageConv}`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="image-artifact"]').first().waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "استفاده به‌عنوان مرجع" }).click();
  await page.locator('[data-chat="reference-chip"]').waitFor({ timeout: 8000 });
  check("reference chip shown", await page.locator('[data-chat="reference-chip"]').isVisible());
  const postedRef = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes(`/api/chat/conversations/${imageConv}/messages`),
    { timeout: 90000 },
  );
  await send(page, "از روی همین یه نسخه گرم‌تر بساز");
  const postedRefRes = await postedRef;
  check("reference send accepted", postedRefRes.ok(), `HTTP ${postedRefRes.status()}`);
  await page.locator('[data-chat="user-message"]').filter({ hasText: "گرم‌تر" }).first().waitFor({
    timeout: 20000,
  });
  detail = await apiJson(page, "GET", `/api/chat/conversations/${imageConv}`);
  const refUser = [...(detail.json?.messages ?? [])]
    .reverse()
    .find((item) => item.role === "user" && (item.content || "").includes("گرم"));
  check(
    "owned reference persisted",
    Array.isArray(refUser?.metadata_json?.reference_artifact_ids) &&
      refUser.metadata_json.reference_artifact_ids.length > 0,
  );
  const ownedRef = refUser?.metadata_json?.reference_artifact_ids?.[0];

  console.log("\n12. Foreign artifact rejected");
  const other = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const otherPage = await other.newPage();
  await login(otherPage, EMAIL_B);
  await send(otherPage, "سلام از حساب دوم");
  const convB = await convId(otherPage);
  const stolen = await apiJson(otherPage, "POST", `/api/chat/conversations/${convB}/messages`, {
    content: "یه تبلیغ از روی عکس اون یکی بساز",
    language: "fa",
    action_hint: "advertising",
    reference_artifact_ids: ownedRef ? [ownedRef] : [eduArtifact?.id].filter(Boolean),
  });
  check("foreign reference did not 500", stolen.status === 200, `HTTP ${stolen.status}`);
  const stolenAssistant = lastAssistant(stolen.json);
  check(
    "foreign reference did not produce an ads artifact",
    stolenAssistant?.metadata_json?.route === "clarify" ||
      (stolen.json?.artifacts ?? []).length === 0,
    stolenAssistant?.metadata_json?.route,
  );
  const leaked = await otherPage.locator("body").innerText();
  check("second account does not see first chat copy", !leaked.includes("فنجان چای"));
  await other.close();

  console.log("\n13. Logout / login keeps artifacts, no leak");
  await page.goto(`${APP}/chat/${imageConv}`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-chat="account-row"]').click();
  await page.locator('[data-chat="account-signout"]').click();
  await page.waitForFunction(
    () => document.querySelector('[data-chat="account-row"]')?.getAttribute("data-signed-in") === "false",
    null,
    { timeout: 15000 },
  );
  check(
    "signed out history empty",
    (await page.locator("[data-chat-item]").count()) === 0,
  );
  await login(page, EMAIL_A);
  await page.locator(`[data-chat-item="${imageConv}"]`).waitFor({ timeout: 15000 });
  await page.locator(`[data-chat-item="${imageConv}"]`).click();
  await page.locator('[data-chat="image-artifact"] img').first().waitFor({ timeout: 20000 });
  check("generated image returned after login", await page.locator('[data-chat="image-artifact"] img').first().isVisible());
  check(
    "other account’s greeting is not in this session",
    !(await page.locator("body").innerText()).includes("سلام از حساب دوم"),
  );

  const noise = consoleErrors.filter(
    (text) =>
      !/favicon|React DevTools|Download the React|net::ERR|404 \(Not Found\)|403 \(Forbidden\)/.test(text),
  );
  check("no console errors", noise.length === 0, noise.slice(0, 2).join(" | "));
  await desktop.close();
} catch (error) {
  failures.push(`threw: ${error.message}`);
  console.log(`\n  ${error.stack?.split("\n").slice(0, 6).join("\n  ")}`);
  try {
    const openPage = browser.contexts()[0]?.pages()[0];
    if (openPage) {
      await openPage.screenshot({ path: "verify-chat-phase-c-failure.png" }).catch(() => {});
      const snippet = (await openPage.locator("body").innerText()).slice(0, 1000);
      console.log(`\n  page text:\n  ${snippet.replaceAll("\n", "\n  ")}`);
    }
  } catch {
    /* ignore */
  }
} finally {
  await browser.close();
}

console.log();
if (notes.length) {
  console.log("tone samples:");
  notes.forEach((item) => console.log(`  - ${item}`));
  console.log();
}
if (failures.length > 0) {
  console.log(`${failures.length} check(s) failed:`);
  failures.forEach((failure) => console.log(`  - ${failure}`));
  process.exit(1);
}
console.log("all Phase C live checks passed");
