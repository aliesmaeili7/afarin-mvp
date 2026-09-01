/**
 * Controlled Phase C leftover + Phase D live HTTP smoke.
 *
 * Four paid image calls only:
 *   1 advertising (Seedream)
 *   1 general_image (GPT Image 2)
 *   2 image_edit (GPT Image 2)
 *
 * Does not rerun Education, retry, or “another version”.
 *
 *   npm run verify:chat:live-gates
 */
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const APP = process.env.VERIFY_APP_URL ?? "http://localhost:3000";
const API = process.env.VERIFY_API_URL ?? "http://127.0.0.1:8000";
const MAIL = process.env.VERIFY_MAIL_URL ?? "http://127.0.0.1:54324";
const IMAGE_MS = Number(process.env.VERIFY_IMAGE_MS ?? 240_000);
const STAMP = Date.now();
const EMAIL = process.env.VERIFY_EXISTING_EMAIL ?? `chat-live-gates-${STAMP}@example.com`;
const REPORT = path.join(tmpdir(), `afarin-live-gates-${STAMP}.json`);

const ADS_PROMPT = "برای این محصول یه تبلیغ مینیمال و حرفه‌ای بساز";
const GEN_PROMPT = "یه تصویر سه‌بعدی مینیمال از یک کافه کوچک در شب بساز";
const EDIT_PROMPT = "پس‌زمینه رو کمی روشن‌تر کن، به چیزهای دیگه دست نزن";
const TEXT_EDIT_PROMPT = "تیتر رو بکن «تمرین اعشار»";

const MOCK_TITLES = ["ماموریت ممیز کوچولو", "تبلیغ کفش سفید", "Elegant shoe ad"];

const failures = [];
const notes = [];
const report = {
  email: EMAIL,
  conversations: {},
  phases: {},
  models: {},
  costs: {},
};

function check(label, ok, detail = "") {
  console.log(`  [${ok ? "ok  " : "FAIL"}] ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures.push(detail ? `${label}: ${detail}` : label);
}

function note(text) {
  notes.push(text);
  console.log(`  note: ${text}`);
}

function productPng() {
  const dest = path.join(tmpdir(), `afarin-live-gates-${STAMP}.png`);
  const py = spawnSync(
    "uv",
    [
      "run",
      "python",
      "-c",
      `from PIL import Image, ImageDraw; im=Image.new("RGB",(640,800),(196,90,40)); d=ImageDraw.Draw(im); d.rounded_rectangle((80,120,560,680),40,fill=(245,235,220)); d.ellipse((220,220,420,420),fill=(196,90,40)); im.save(${JSON.stringify(dest)})`,
    ],
    { cwd: path.resolve(import.meta.dirname, "../../backend"), encoding: "utf8" },
  );
  if (py.status !== 0) {
    throw new Error(`could not paint product PNG: ${py.stderr || py.stdout}`);
  }
  return dest;
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
  await page.locator('[data-chat="send"]:not([disabled])').click();
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

function assistantCount(detail) {
  return (detail?.messages ?? []).filter((item) => item.role === "assistant").length;
}

function readyImages(detail) {
  return (detail?.artifacts ?? []).filter(
    (item) => item.status === "ready" && item.artifact_type === "image",
  );
}

function foldFa(value) {
  return String(value || "").replace(/[\u200c\s]/g, "");
}

function preservesRequestedEdit(instruction, userText, quotes = []) {
  const hay = foldFa(instruction);
  const hasQuotes = quotes.every(
    (quote) => String(instruction || "").includes(quote) || hay.includes(foldFa(quote)),
  );
  if (quotes.length) return hasQuotes;
  return hay.includes(foldFa(userText));
}

async function waitForRenderedImages(page, min) {
  const imgs = page.locator('[data-chat="image-artifact"] img');
  await imgs.nth(min - 1).waitFor({ state: "visible", timeout: 20000 });
  await page.waitForFunction(
    (n) =>
      [...document.querySelectorAll('[data-chat="image-artifact"] img')].filter(
        (img) => img.complete && img.naturalWidth > 0,
      ).length >= n,
    min,
    { timeout: 20000 },
  );
  return page.locator('[data-chat="image-artifact"] img').count();
}

async function waitImageAndPhases(page, label, minImages = 1) {
  const seen = [];
  const deadline = Date.now() + IMAGE_MS;
  while (Date.now() < deadline) {
    const phase = await page
      .locator("[data-chat-phase]")
      .last()
      .getAttribute("data-chat-phase")
      .catch(() => null);
    if (phase && seen[seen.length - 1] !== phase) seen.push(phase);
    const failed = await page.locator('[data-chat="generation-failed"]').count();
    const ready = await page.locator('[data-chat="image-artifact"] img').count();
    if (failed > 0 || ready >= minImages) {
      report.phases[label] = seen;
      return { ok: failed === 0 && ready >= minImages, seen, failed: failed > 0 };
    }
    await page.waitForTimeout(350);
  }
  report.phases[label] = seen;
  return { ok: false, seen, failed: false };
}

const browser = await chromium.launch({ channel: "chrome" });
const productPath = productPng();

try {
  const desktop = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await desktop.newPage();
  page.setDefaultTimeout(20000);

  const frontendMode = await page.evaluate(async () => {
    const res = await fetch("/");
    return res.headers.get("x-api-mode");
  }).catch(() => null);

  console.log("\nSign in");
  await login(page, EMAIL);
  await page.locator('[data-chat="account-row"]').waitFor({ timeout: 15000 });
  check(
    "signed in",
    (await page.locator('[data-chat="account-row"]').getAttribute("data-signed-in")) ===
      "true",
  );
  const bodyText = await page.locator("body").innerText();
  check("not serving mock seed data", !MOCK_TITLES.some((title) => bodyText.includes(title)));
  note(`frontend origin ${APP}; x-api-mode=${frontendMode ?? "n/a"}`);

  console.log("\nAdvertising (1 paid Seedream call)");
  await page.locator('input[type="file"]').first().setInputFiles(productPath);
  await page.locator('[data-chat="attachment-chip"]').waitFor({ timeout: 8000 });
  check("product attachment chip shown", await page.locator('[data-chat="attachment-chip"]').isVisible());
  await send(page, ADS_PROMPT);
  const adsConv = await convId(page);
  report.conversations.advertising = adsConv;
  const adsWait = await waitImageAndPhases(page, "advertising", 1);
  check("advertising image ready", adsWait.ok, adsWait.failed ? "generation failed" : adsWait.seen.join(" → "));
  check(
    "advertising activity includes preparing_advertising",
    adsWait.seen.includes("preparing_advertising"),
    adsWait.seen.join(" → "),
  );
  check(
    "advertising activity includes generating_image",
    adsWait.seen.includes("generating_image"),
    adsWait.seen.join(" → "),
  );
  let detail = await apiJson(page, "GET", `/api/chat/conversations/${adsConv}`);
  let assistant = lastAssistant(detail.json);
  const adsArtifact = readyImages(detail.json)[0];
  const adsUsers = userCount(detail.json);
  const adsAssistants = assistantCount(detail.json);
  check("ads route", assistant?.metadata_json?.route === "advertising", assistant?.metadata_json?.route);
  check("one user message", adsUsers === 1, String(adsUsers));
  check("one assistant message", adsAssistants === 1, String(adsAssistants));
  check(
    "campaign/domain link metadata",
    Boolean(adsArtifact?.metadata_json?.campaign_id),
    JSON.stringify(adsArtifact?.metadata_json ?? {}).slice(0, 180),
  );
  check("ads storage is campaigns/", Boolean(adsArtifact?.storage_path?.includes("/campaigns/")));
  await page.reload({ waitUntil: "domcontentloaded" });
  check("ads image survives refresh", (await waitForRenderedImages(page, 1)) >= 1);
  const adsAfter = await apiJson(page, "GET", `/api/chat/conversations/${adsConv}`);
  check("ads messages unchanged after refresh", userCount(adsAfter.json) === 1 && assistantCount(adsAfter.json) === 1);

  console.log("\n/create advertising wizard");
  await page.goto(`${APP}/create`, { waitUntil: "domcontentloaded" });
  await page.getByText("عکس محصولت رو آپلود کن").waitFor({ timeout: 15000 });
  check("legacy /create wizard still opens", await page.getByText("عکس محصولت رو آپلود کن").isVisible());

  console.log("\nGeneral image (1 paid GPT Image 2 call)");
  await page.goto(`${APP}/chat`, { waitUntil: "domcontentloaded" });
  await newChat(page);
  await send(page, GEN_PROMPT);
  const genConv = await convId(page);
  report.conversations.general_image = genConv;
  const genWait = await waitImageAndPhases(page, "general_image", 1);
  check("general image ready", genWait.ok, genWait.failed ? "generation failed" : genWait.seen.join(" → "));
  if (genWait.seen.includes("preparing_image")) {
    note("observed preparing_image before generating_image");
  }
  check(
    "general image generating_image",
    genWait.seen.includes("generating_image"),
    genWait.seen.join(" → "),
  );
  detail = await apiJson(page, "GET", `/api/chat/conversations/${genConv}`);
  assistant = lastAssistant(detail.json);
  const genArtifact = readyImages(detail.json)[0];
  check("general_image route", assistant?.metadata_json?.route === "general_image", assistant?.metadata_json?.route);
  check(
    "general image stored under chat/",
    Boolean(
      genArtifact?.storage_path?.includes(`/chat/${genConv}/artifacts/`) ||
        genArtifact?.storage_path?.includes("/chat/") && genArtifact?.storage_path?.includes("/artifacts/"),
    ),
    genArtifact?.storage_path,
  );
  check("one user / one assistant on general image", userCount(detail.json) === 1 && assistantCount(detail.json) === 1);
  await page.reload({ waitUntil: "domcontentloaded" });
  check("general image survives refresh", (await waitForRenderedImages(page, 1)) >= 1);
  const genOriginalPath = genArtifact?.storage_path;
  const genOriginalId = genArtifact?.id;
  report.models.general_image_artifact = genArtifact?.metadata_json ?? {};

  console.log("\nPhase D edit 1 (reference + brighten)");
  await page.locator('[data-chat="use-as-reference"]').last().click();
  await page.locator('[data-chat="reference-chip"]').waitFor({ timeout: 8000 });
  check("reference chip shown", await page.locator('[data-chat="reference-chip"]').isVisible());
  const chipText = (await page.locator('[data-chat="reference-chip"]').innerText()).replaceAll("\n", " ");
  note(`reference chip: ${chipText}`);
  const usersBeforeEdit = userCount(
    (await apiJson(page, "GET", `/api/chat/conversations/${genConv}`)).json,
  );
  await send(page, EDIT_PROMPT);
  const edit1Wait = await waitImageAndPhases(page, "image_edit_1", 2);
  check("first edit image ready", edit1Wait.ok, edit1Wait.failed ? "generation failed" : edit1Wait.seen.join(" → "));
  check("first edit preparing_edit", edit1Wait.seen.includes("preparing_edit"), edit1Wait.seen.join(" → "));
  check(
    "first edit generating_image",
    edit1Wait.seen.includes("generating_image"),
    edit1Wait.seen.join(" → "),
  );
  detail = await apiJson(page, "GET", `/api/chat/conversations/${genConv}`);
  assistant = lastAssistant(detail.json);
  const images = readyImages(detail.json);
  const originalStill = images.find((item) => item.id === genOriginalId);
  const edited = [...images].reverse().find((item) => item.id !== genOriginalId);
  check("edit route", assistant?.metadata_json?.route === "image_edit", assistant?.metadata_json?.route);
  check("new chat artifact created", Boolean(edited), String(images.length));
  check("original artifact still ready", originalStill?.status === "ready" && originalStill?.storage_path === genOriginalPath);
  check(
    "edited stored under chat/{id}/artifacts",
    Boolean(edited?.storage_path?.includes(`/chat/${genConv}/artifacts/`)),
    edited?.storage_path,
  );
  const sourceIds = edited?.metadata_json?.source_artifact_ids ?? assistant?.metadata_json?.source_artifact_ids;
  check("lineage points at original", Array.isArray(sourceIds) && sourceIds.includes(genOriginalId), JSON.stringify(sourceIds));
  const instruction = edited?.metadata_json?.edit_instruction || assistant?.metadata_json?.edit_instruction || "";
  check(
    "edit_instruction preserves requested change",
    preservesRequestedEdit(instruction, EDIT_PROMPT),
    instruction.slice(0, 160),
  );
  check("no duplicate user on first edit", userCount(detail.json) === usersBeforeEdit + 1, String(userCount(detail.json)));
  report.costs.edit1 = edited?.metadata_json?.usage ?? assistant?.metadata_json?.usage;
  report.models.edit1 = edited?.metadata_json ?? {};
  await page.reload({ waitUntil: "domcontentloaded" });
  check(
    "both original and edited visible after refresh",
    (await waitForRenderedImages(page, 2)) >= 2,
  );

  console.log("\nPhase D edit 2 (Persian title on edited result)");
  await page.locator('[data-chat="use-as-reference"]').last().click();
  await page.locator('[data-chat="reference-chip"]').waitFor({ timeout: 8000 });
  const usersBeforeText = userCount(
    (await apiJson(page, "GET", `/api/chat/conversations/${genConv}`)).json,
  );
  await send(page, TEXT_EDIT_PROMPT);
  const edit2Wait = await waitImageAndPhases(page, "image_edit_2", 3);
  check("Persian text edit ready", edit2Wait.ok, edit2Wait.failed ? "generation failed" : edit2Wait.seen.join(" → "));
  check("second edit preparing_edit", edit2Wait.seen.includes("preparing_edit"), edit2Wait.seen.join(" → "));
  detail = await apiJson(page, "GET", `/api/chat/conversations/${genConv}`);
  assistant = lastAssistant(detail.json);
  const afterText = readyImages(detail.json);
  const second = [...afterText].reverse().find((item) => item.id !== edited?.id && item.id !== genOriginalId);
  const textInstruction = second?.metadata_json?.edit_instruction || assistant?.metadata_json?.edit_instruction || "";
  check("second edit route", assistant?.metadata_json?.route === "image_edit", assistant?.metadata_json?.route);
  check("another new artifact", Boolean(second), String(afterText.length));
  check(
    "exact quoted string in edit_instruction",
    preservesRequestedEdit(textInstruction, TEXT_EDIT_PROMPT, ["تمرین اعشار"]),
    textInstruction,
  );
  const secondSources = second?.metadata_json?.source_artifact_ids ?? [];
  check("lineage points at first edit", secondSources.includes(edited?.id), JSON.stringify(secondSources));
  check("original still intact", afterText.some((item) => item.id === genOriginalId && item.storage_path === genOriginalPath));
  check("first edit still intact", afterText.some((item) => item.id === edited?.id && item.storage_path === edited?.storage_path));
  check("no duplicate user on text edit", userCount(detail.json) === usersBeforeText + 1);
  report.costs.edit2 = second?.metadata_json?.usage ?? assistant?.metadata_json?.usage;
  report.models.edit2 = second?.metadata_json ?? {};
  await page.reload({ waitUntil: "domcontentloaded" });
  check(
    "three images persist after refresh",
    (await waitForRenderedImages(page, 3)) >= 3,
  );

  const adsFinal = (await apiJson(page, "GET", `/api/chat/conversations/${adsConv}`)).json;
  const genFinal = (await apiJson(page, "GET", `/api/chat/conversations/${genConv}`)).json;
  report.conversations.ads_campaign_id = adsFinal?.artifacts?.[0]?.metadata_json?.campaign_id;
  report.conversations.gen_artifact_ids = (genFinal?.artifacts ?? []).map((item) => ({
    id: item.id,
    path: item.storage_path,
    skill: item.metadata_json?.skill,
    sources: item.metadata_json?.source_artifact_ids,
    usage: item.metadata_json?.usage,
    instruction: item.metadata_json?.edit_instruction,
  }));
  report.conversations.ads_route = lastAssistant(adsFinal)?.metadata_json?.route;
  report.conversations.gen_routes = (genFinal?.messages ?? [])
    .filter((item) => item.role === "assistant")
    .map((item) => ({
      route: item.metadata_json?.route,
      usage: item.metadata_json?.usage,
      model: item.metadata_json?.usage?.model,
    }));

  await desktop.close();
} catch (error) {
  failures.push(`threw: ${error.message}`);
  console.log(`\n  ${error.stack?.split("\n").slice(0, 8).join("\n  ")}`);
  try {
    const openPage = browser.contexts()[0]?.pages()[0];
    if (openPage) {
      await openPage.screenshot({ path: "verify-chat-live-gates-failure.png" }).catch(() => {});
    }
  } catch {
    /* ignore */
  }
} finally {
  await browser.close();
  writeFileSync(REPORT, JSON.stringify(report, null, 2));
  note(`report json: ${REPORT}`);
}

console.log();
if (notes.length) {
  console.log("notes:");
  notes.forEach((item) => console.log(`  - ${item}`));
  console.log();
}
if (failures.length > 0) {
  console.log(`${failures.length} check(s) failed:`);
  failures.forEach((failure) => console.log(`  - ${failure}`));
  process.exit(1);
}
console.log("all live C+D gates passed");
