/**
 * Manual end-to-end verification of the Phase 1 flow in a real browser.
 * Not part of the test suite; run with `node scripts/verify-flow.mjs` while a
 * server is listening on BASE_URL. Screenshots land in /tmp/afarin-shots.
 */
import { chromium } from "playwright";
import { mkdirSync, existsSync, statSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://localhost:3100";
const SHOTS = "/tmp/afarin-shots";
const DOWNLOADS = "/tmp/afarin-downloads";
mkdirSync(SHOTS, { recursive: true });
mkdirSync(DOWNLOADS, { recursive: true });

const problems = [];
const log = (message) => console.log(`  ${message}`);

const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  locale: "fa-IR",
  acceptDownloads: true,
});
const page = await context.newPage();

page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") problems.push(`console: ${message.text()}`);
});

async function shot(name) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

console.log("\n1. landing");
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(500);
await shot("01-landing");
log(`title: ${await page.title()}`);
log(`dir: ${await page.evaluate(() => document.documentElement.dir)}`);
log(
  `font: ${await page.evaluate(() =>
    getComputedStyle(document.body).fontFamily.split(",")[0],
  )}`,
);

console.log("\n2. wizard step 1 — sample product");
await page.getByRole("link", { name: /اولین کمپینت رو رایگان بساز/ }).click();
await page.waitForURL("**/create");
await page.getByText("عکس ندارم، با نمونه امتحان می‌کنم").click();
await page.getByRole("button", { name: "ادامه" }).waitFor({ state: "visible" });
await page.waitForTimeout(1200);
await shot("02-upload");

console.log("\n3. wizard step 2 — product on the same page");
await page.getByLabel("اسم محصول").waitFor({ state: "visible" });
await page.waitForTimeout(800);
await shot("03-product");
log(`prefilled name: ${await page.getByLabel("اسم محصول").inputValue()}`);

console.log("\n4. wizard step 2 — campaign brief");
await page.getByRole("button", { name: "ادامه" }).click();
await page.waitForURL("**/create/brief");
await page.waitForTimeout(600);
await page.getByRole("button", { name: /فروش محصول/ }).click();
await page.getByText("مطمئن نیستم — خودت پیشنهاد بده").click();
await page.getByRole("button", { name: /لوکس/ }).click();
await shot("04-brief");

console.log("\n5. wizard step 3 — directions");
await page.getByRole("button", { name: "ادامه" }).click();
await page.waitForURL("**/create/directions");
await page
  .getByRole("button", { name: /واقعی و واضح|هدیه لوکس|ایده/ })
  .first()
  .waitFor({ timeout: 15000 });
await page.waitForTimeout(600);
await shot("05-directions");
const conceptTitles = await page.locator("h3, [class*='font-bold']").allInnerTexts();
log(`directions: ${conceptTitles.slice(0, 6).join(" | ")}`);

console.log("\n6. regenerate directions");
await page.getByRole("button", { name: "سه پیشنهاد جدید بده" }).click();
await page.waitForTimeout(3000);

console.log("\n7. pick a direction and accurate mode");
await page.getByRole("button", { pressed: false }).nth(0).click();
await page.waitForTimeout(400);
await page.getByRole("button", { name: /دقیق/ }).click();
await page.waitForTimeout(400);
await page.getByRole("button", { name: "ساخت کمپین" }).click();

console.log("\n8. signup gate");
await page.waitForURL("**/create/signup");
await page.waitForTimeout(800);
await shot("07-signup");
await page.getByLabel("ایمیل").fill("test@example.com");
await page.getByLabel("رمز عبور").fill("testpass1");
await page.getByLabel("تکرار رمز").fill("testpass1");
await page.getByRole("button", { name: "ثبت‌نام و ساخت کمپین" }).click();

console.log("\n10. generation progress");
await page.waitForURL(/\/campaigns\//, { timeout: 15000 });
await page.waitForTimeout(2500);
await shot("08-generating");
const progressText = await page
  .locator("body")
  .innerText()
  .then((text) => text.split("\n").slice(0, 6).join(" / "));
log(`progress screen: ${progressText}`);

console.log("\n11. refresh mid-generation (resume check)");
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(1500);
const resumed = await page.locator("body").innerText();
log(`resumed on progress screen: ${resumed.includes("داریم کمپینت رو می‌سازیم")}`);
if (!resumed.includes("داریم کمپینت رو می‌سازیم")) {
  problems.push("generation did not resume after refresh");
}

console.log("\n12. result page");
await page.getByText("کمپینت آماده‌ست").waitFor({ timeout: 30000 });
await page.waitForTimeout(1500);
await shot("09-result");
const bodyText = await page.locator("body").innerText();
for (const section of [
  "پست فید",
  "استوری",
  "کاروسل سه‌اسلایدی",
  "کپشن‌ها",
  "ایده‌های استوری",
  "ایده ریلز",
]) {
  if (!bodyText.includes(section)) problems.push(`missing section: ${section}`);
}
log(`sections present: ${bodyText.includes("ایده ریلز")}`);

console.log("\n13. PNG export (Persian font check)");
const downloadPromise = page.waitForEvent("download", { timeout: 30000 });
await page.getByRole("button", { name: "دانلود" }).first().click();
const download = await downloadPromise;
const target = `${DOWNLOADS}/${download.suggestedFilename()}`;
await download.saveAs(target);
if (existsSync(target)) {
  const size = statSync(target).size;
  log(`downloaded ${download.suggestedFilename()} (${size} bytes)`);
  if (size < 20000) problems.push(`exported PNG suspiciously small: ${size} bytes`);
} else {
  problems.push("download did not produce a file");
}

console.log("\n14. copy caption + edit text");
await page.getByRole("button", { name: "کپی", exact: true }).first().click();
await page.waitForTimeout(600);
await page.getByRole("button", { name: "ویرایش متن" }).first().click();
await page.waitForTimeout(600);
await shot("10-edit-sheet");
await page.getByLabel("تیتر اصلی").fill("تیتر آزمایشی نیم‌فاصله‌دار");
await page.getByRole("button", { name: "ذخیره", exact: true }).click();
await page.waitForTimeout(1500);
const afterEdit = await page.locator("body").innerText();
if (!afterEdit.includes("تیتر آزمایشی")) {
  problems.push("edited headline did not appear on the canvas");
}
await shot("11-after-edit");

console.log("\n15. dashboard");
await page.goto(`${BASE}/dashboard`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await shot("12-dashboard");
const dash = await page.locator("body").innerText();
log(`dashboard shows campaigns: ${dash.includes("کمپین‌های اخیر")}`);

console.log("\n16. desktop landing");
const desktop = await context.newPage();
await desktop.setViewportSize({ width: 1280, height: 900 });
await desktop.goto(BASE, { waitUntil: "networkidle" });
await desktop.waitForTimeout(800);
await desktop.screenshot({ path: `${SHOTS}/13-desktop-landing.png`, fullPage: true });

await browser.close();

console.log("\n=== problems ===");
if (problems.length === 0) console.log("none");
else problems.forEach((problem) => console.log(`- ${problem}`));
