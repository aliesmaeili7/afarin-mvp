/**
 * Locale, direction, theme, and ad isolation — no full campaign walk.
 *
 *   node scripts/verify-i18n-theme.mjs
 *
 * Expects a frontend on :3000 (mock or http). Override with VERIFY_APP_URL.
 * `verify-ui.mjs` stays Persian-default and should keep using those selectors.
 */
import { chromium } from "playwright";

const APP = process.env.VERIFY_APP_URL ?? "http://localhost:3000";

const failures = [];

function check(label, ok, detail = "") {
  console.log(`  [${ok ? "ok  " : "FAIL"}] ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures.push(label);
}

async function launchBrowser() {
  try {
    return await chromium.launch({ channel: "chrome" });
  } catch {
    return await chromium.launch();
  }
}

function cookie(name, value) {
  return { name, value, url: APP };
}

const browser = await launchBrowser();

try {
  console.log("\n1. default cookie-less visit stays Persian RTL");
  const defaultContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const defaultPage = await defaultContext.newPage();
  const hydration = [];
  defaultPage.on("console", (message) => {
    const text = message.text();
    if (/hydrat/i.test(text) || /did not match/i.test(text)) hydration.push(text);
  });
  await defaultPage.goto(APP, { waitUntil: "networkidle" });
  check("lang=fa", (await defaultPage.locator("html").getAttribute("lang")) === "fa");
  check("dir=rtl", (await defaultPage.locator("html").getAttribute("dir")) === "rtl");
  check(
    "Persian landing chrome",
    await defaultPage.getByText("اولین کمپینت رو رایگان بساز").first().isVisible(),
  );
  check("no hydration mismatch on default", hydration.length === 0, hydration[0]);
  await defaultContext.close();

  console.log("\n2. English locale cookie");
  const enContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  await enContext.addCookies([cookie("afarin_locale", "en")]);
  const enPage = await enContext.newPage();
  const enHydration = [];
  enPage.on("console", (message) => {
    const text = message.text();
    if (/hydrat/i.test(text) || /did not match/i.test(text)) enHydration.push(text);
  });
  await enPage.goto(APP, { waitUntil: "networkidle" });
  check("lang=en", (await enPage.locator("html").getAttribute("lang")) === "en");
  check("dir=ltr", (await enPage.locator("html").getAttribute("dir")) === "ltr");
  check(
    "English landing chrome",
    await enPage.getByText("Create your first campaign free").first().isVisible(),
  );
  check(
    "campaign ad copy stays Persian",
    await enPage.getByText("هدیه‌ای با عطر ایران").first().isVisible(),
  );
  const canvasDir = await enPage.locator("[data-ad-canvas]").first().getAttribute("dir");
  check("AdCanvas stays dir=rtl", canvasDir === "rtl");
  const canvasScheme = await enPage
    .locator("[data-ad-canvas]")
    .first()
    .evaluate((el) => getComputedStyle(el).colorScheme);
  check("AdCanvas color-scheme stays light", /only light|light/.test(canvasScheme));
  check("no hydration mismatch in English", enHydration.length === 0, enHydration[0]);

  console.log("\n3. dark theme cookie");
  await enContext.addCookies([cookie("afarin_theme", "dark")]);
  await enPage.reload({ waitUntil: "networkidle" });
  const htmlClass = await enPage.locator("html").getAttribute("class");
  check("html.dark after dark cookie", (htmlClass ?? "").split(/\s+/).includes("dark"));
  const dataTheme = await enPage.locator("html").getAttribute("data-theme");
  check("data-theme=dark", dataTheme === "dark");
  const canvasFill = await enPage
    .locator("[data-ad-canvas]")
    .first()
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  check(
    "ad fill is not the app surface",
    canvasFill === "rgb(15, 11, 22)",
    canvasFill,
  );

  console.log("\n4. settings sheet in LTR (desktop) and RTL (mobile)");
  await enPage.getByRole("button", { name: "Settings" }).click();
  const enSheet = enPage.getByRole("dialog", { name: "Settings" });
  check("English settings sheet opens", await enSheet.isVisible());
  check("language group", await enSheet.getByRole("group", { name: "Language" }).isVisible());
  check("appearance group", await enSheet.getByRole("group", { name: "Appearance" }).isVisible());
  await enPage.keyboard.press("Escape");
  await enContext.close();

  const faMobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const faPage = await faMobile.newPage();
  await faPage.goto(APP, { waitUntil: "networkidle" });
  await faPage.getByRole("button", { name: "تنظیمات" }).click();
  const faSheet = faPage.getByRole("dialog", { name: "تنظیمات" });
  check("Persian mobile settings sheet opens", await faSheet.isVisible());
  check(
    "فارسی option is pressed by default",
    (await faSheet.getByRole("button", { name: "فارسی" }).getAttribute("aria-pressed")) === "true",
  );
  await faMobile.close();

  console.log("\n5. system preference follows prefers-color-scheme");
  const systemContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: "dark",
  });
  await systemContext.addCookies([cookie("afarin_theme", "system")]);
  const systemPage = await systemContext.newPage();
  await systemPage.goto(APP, { waitUntil: "networkidle" });
  const systemClass = await systemPage.locator("html").getAttribute("class");
  check(
    "system + prefers-dark → html.dark",
    (systemClass ?? "").split(/\s+/).includes("dark"),
  );
  const systemTheme = await systemPage.locator("html").getAttribute("data-theme");
  check("data-theme stays system", systemTheme === "system");
  await systemContext.close();
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
