/**
 * Walks the real UI against the real backend, the way a seller would.
 *
 * backend/scripts/verify_flow.py proves the API is correct; this proves the
 * browser is actually wired to it — the anonymous cookie, signed image URLs,
 * the emailed code screen, adoption, and history on a second device.
 *
 *   node scripts/verify-ui.mjs
 *
 * Expects `supabase start`, the backend on :8000, and a frontend on :3000 built
 * with NEXT_PUBLIC_API_MODE=http. Override the origin with VERIFY_APP_URL.
 */
import { chromium } from "playwright";

const APP = process.env.VERIFY_APP_URL ?? "http://localhost:3000";
const MAIL = process.env.VERIFY_MAIL_URL ?? "http://127.0.0.1:54324";
const PHOTO = process.env.VERIFY_PHOTO ?? "/tmp/afarin-verify-product.png";
const EMAIL = `ui-${Date.now()}@example.com`;
const PRODUCT = "زعفران ممتاز قائنات";
/** Set VERIFY_SHOTS to a directory to save screenshots of the key screens. */
const SHOTS = process.env.VERIFY_SHOTS ?? null;

const failures = [];

function check(label, ok, detail = "") {
  console.log(`  [${ok ? "ok  " : "FAIL"}] ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures.push(label);
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

const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});
const page = await context.newPage();

const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(String(error)));

try {
  console.log("\n1. landing → wizard, anonymous session");
  await page.goto(APP, { waitUntil: "networkidle" });
  check("landing renders", await page.getByRole("heading", { level: 1 }).first().isVisible());
  await page.getByRole("link", { name: "ورود" }).waitFor({ timeout: 10000 });
  check("login entry is visible while logged out", await page.getByRole("link", { name: "ورود" }).isVisible());

  await page.locator('a[href="/create"]').first().click();
  await page.waitForURL(/\/create$/, { timeout: 20000 });

  console.log("\n2. photo upload");
  await page.setInputFiles('input[type="file"]', PHOTO);
  await page.getByRole("button", { name: "ادامه", exact: true }).waitFor({ timeout: 30000 });
  await page.waitForFunction(
    () => {
      const button = [...document.querySelectorAll("button")].find(
        (element) => element.textContent?.trim() === "ادامه",
      );
      return button && !button.disabled;
    },
    { timeout: 30000 },
  );

  const uploaded = page.locator("main img").first();
  const source = await uploaded.getAttribute("src");
  check(
    "photo comes back as a signed Supabase URL",
    Boolean(source && source.includes("/storage/v1/") && source.includes("token=")),
    source ? `${source.slice(0, 72)}…` : "no image",
  );

  const jar = await context.cookies(["http://localhost:8000", APP]);
  const anon = jar.find((cookie) => cookie.name === "afarin_anon");
  check("backend issued the anonymous cookie", Boolean(anon), jar.map((c) => c.name).join(", "));
  check("cookie is HttpOnly", anon?.httpOnly === true);
  check("cookie is SameSite=Lax", anon?.sameSite === "Lax", anon?.sameSite ?? "-");
  check(
    "JavaScript cannot read the token",
    !(await page.evaluate(() => document.cookie)).includes("afarin_anon"),
  );

  await page.getByRole("button", { name: "ادامه", exact: true }).click();

  console.log("\n3. brief");
  await page.waitForURL(/\/create\/(product|brief)/, { timeout: 20000 });
  if (page.url().includes("/create/product")) {
    await page.getByLabel("اسم محصول").fill(PRODUCT);
    await page.getByLabel("اسم برند یا کسب‌وکار").fill("زعفران آرین");
    await page.getByRole("button", { name: "ادامه", exact: true }).click();
    await page.waitForURL(/\/create\/objective/, { timeout: 20000 });
    await page.getByRole("button").filter({ hasText: "فروش محصول" }).first().click();
    await page.getByRole("button", { name: "ادامه", exact: true }).click();
    await page.waitForURL(/\/create\/style/, { timeout: 20000 });
    await page.getByRole("button").filter({ hasText: "لوکس" }).first().click();
    await page.getByRole("button", { name: "ادامه", exact: true }).click();
  } else {
    await page.getByRole("button").filter({ hasText: "فروش محصول" }).first().click();
    await page.getByRole("button").filter({ hasText: "لوکس" }).first().click();
    await page.getByRole("button", { name: "ادامه", exact: true }).click();
  }

  console.log("\n4. visual");
  await page.waitForURL(/\/create\/visual/, { timeout: 20000 });
  await page.getByRole("button", { name: /ساخت کمپین/ }).click();

  console.log("\n5. sign-up with an emailed code");
  await page.waitForURL(/\/create\/signup/, { timeout: 20000 });
  await page.getByLabel("ایمیل").fill(EMAIL);
  await page.getByRole("button", { name: /ثبت‌نام و ساخت کمپین/ }).click();

  await page.getByLabel("کد تأیید").waitFor({ timeout: 30000 });
  check("code-entry step shown", true);

  const code = await fetchCode(EMAIL);
  check("code delivered by email", code !== null, code ?? "never arrived");
  if (!code) throw new Error("no verification code");

  await page.getByLabel("کد تأیید").fill(code);
  await page.getByRole("button", { name: /تأیید و ساخت کمپین/ }).click();

  console.log("\n6. adoption, generation, result");
  await page.waitForURL(/\/campaigns\/[0-9a-f-]+/, { timeout: 40000 });
  check("anonymous campaign carried into the account", true, page.url().split("/").pop());

  const progressCopy = page.getByText("داریم کمپینت رو می‌سازیم");
  const feedCopy = page.getByText("پست فید");
  const sawProgress = await progressCopy
    .waitFor({ state: "visible", timeout: 15000 })
    .then(() => true)
    .catch(() => false);
  check(
    "progress screen runs while the job works",
    sawProgress || (await feedCopy.isVisible().catch(() => false)),
  );

  // "پست فید" only exists on the finished result; the progress messages
  // mention captions and stories, so those words would match too early.
  await feedCopy.waitFor({ timeout: 120000 });
  const result = await page.locator("body").innerText();
  check("the product name is in the generated copy", result.includes("زعفران"));
  check(
    "post, story, carousel and reel are all present",
    ["پست فید", "استوری", "کاروسل سه‌اسلایدی", "ایده ریلز", "کپشن‌ها"].every(
      (section) => result.includes(section),
    ),
  );

  const loadedImages = (nodes) =>
    nodes.filter((node) => node.complete && node.naturalWidth > 0).length;

  await page.waitForTimeout(2000);
  const rendered = await page.locator("img").evaluateAll(loadedImages);
  check("ad images actually load", rendered > 0, `${rendered} loaded`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/result.png`, fullPage: true });

  console.log("\n7. dashboard");
  await page.getByRole("link", { name: "داشبورد", exact: true }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 20000 });
  await page.getByRole("button", { name: "کمپین جدید بساز" }).waitFor({ timeout: 20000 });
  await page.waitForFunction(
    (name) => document.body.innerText.includes(name),
    PRODUCT,
    { timeout: 20000 },
  );
  const history = await page.locator("body").innerText();
  check("campaign appears in history", history.includes(PRODUCT));
  await page.waitForTimeout(2000);
  const thumbnails = await page.locator("img").evaluateAll(loadedImages);
  check("history thumbnails render", thumbnails > 0, `${thumbnails} loaded`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/dashboard.png`, fullPage: true });
  check(
    "logged-in header does not offer signup/login",
    !(await page.getByRole("link", { name: "ورود" }).isVisible().catch(() => false)),
  );

  console.log("\n8. second campaign while logged in");
  await page.getByRole("button", { name: "کمپین جدید بساز" }).click();
  await page.waitForURL(/\/create$/, { timeout: 20000 });
  await page.setInputFiles('input[type="file"]', PHOTO);
  await page.getByRole("button", { name: "ادامه", exact: true }).waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: "ادامه", exact: true }).click();

  await page.waitForURL(/\/create\/product/, { timeout: 20000 });
  await page.getByLabel("اسم محصول").fill("صابون زیتون");
  await page.getByLabel("اسم برند یا کسب‌وکار").fill("زیتونک");
  await page.getByRole("button", { name: "ادامه", exact: true }).click();

  await page.waitForURL(/\/create\/objective/, { timeout: 20000 });
  await page.getByRole("button").filter({ hasText: "فروش محصول" }).first().click();
  await page.getByRole("button", { name: "ادامه", exact: true }).click();

  await page.waitForURL(/\/create\/style/, { timeout: 20000 });
  await page.getByRole("button").filter({ hasText: "مینیمال" }).first().click();
  await page.getByRole("button", { name: "ادامه", exact: true }).click();

  await page.waitForURL(/\/create\/concepts/, { timeout: 20000 });
  await pick.first().waitFor({ timeout: 90000 });
  const secondConcepts = await page.locator("body").innerText();
  check(
    "new campaign concepts are for the new product",
    secondConcepts.includes("صابون") && !secondConcepts.includes(PRODUCT),
  );
  await pick.first().click();
  await page.waitForURL(/\/campaigns\/[0-9a-f-]+/, { timeout: 40000 });
  check("logged-in user skipped the signup gate", !page.url().includes("/create/signup"));
  await page.getByText("پست فید").waitFor({ timeout: 120000 });

  console.log("\n9. a different browser, same account");
  const session = await page.evaluate(() =>
    JSON.stringify(
      Object.fromEntries(
        Object.keys(window.localStorage)
          .filter((key) => key.startsWith("sb-"))
          .map((key) => [key, window.localStorage.getItem(key)]),
      ),
    ),
  );
  const second = await browser.newContext();
  const secondPage = await second.newPage();
  await secondPage.goto(APP, { waitUntil: "domcontentloaded" });
  await secondPage.evaluate((raw) => {
    Object.entries(JSON.parse(raw)).forEach(([key, value]) =>
      window.localStorage.setItem(key, value),
    );
  }, session);
  await secondPage.goto(`${APP}/dashboard`, { waitUntil: "domcontentloaded" });
  await secondPage.waitForFunction(
    (name) => document.body.innerText.includes(name),
    PRODUCT,
    { timeout: 20000 },
  );
  const carried = await secondPage
    .getByText(PRODUCT)
    .first()
    .isVisible()
    .catch(() => false);
  check("history follows the account across devices", carried);
  await second.close();

  console.log("\n10. an unrelated visitor");
  const stranger = await browser.newContext();
  const strangerPage = await stranger.newPage();
  await strangerPage.goto(`${APP}/dashboard`, { waitUntil: "domcontentloaded" });
  const strangerText = await strangerPage.locator("body").innerText();
  check("cannot see someone else's campaigns", !strangerText.includes(PRODUCT));
  await stranger.close();

  const noise = consoleErrors.filter(
    (text) => !/favicon|React DevTools|Download the React/.test(text),
  );
  check("no console errors", noise.length === 0, noise.slice(0, 2).join(" | "));
} catch (error) {
  failures.push(`threw: ${error.message}`);
  console.log(`\n  ${error.stack?.split("\n").slice(0, 3).join("\n  ")}`);
  await page.screenshot({ path: "verify-ui-failure.png", fullPage: true }).catch(() => {});
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
