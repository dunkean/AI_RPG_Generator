const { chromium } = require("../../tmp/studio_qa/node_modules/playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
fs.mkdirSync("output/genealogy/screenshots", { recursive: true });
(async () => {
  const browser = await chromium.launch({
    executablePath:
      process.env.STUDIO_BROWSER ||
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    headless: true,
  });
  const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    }),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8765");
  await page.waitForFunction(
    () => document.querySelector("#treeNote").textContent,
  );
  await page.screenshot({
    path: "output/genealogy/screenshots/config-final.png",
    fullPage: true,
  });
  await page.click("#tabExplore");
  await page.screenshot({
    path: "output/genealogy/screenshots/explore-final.png",
    fullPage: true,
  });
  await page.click("#tabConfig");
  await page.selectOption("#preset", "blank");
  await page.fill("#seed", "9876");
  await page.fill("#founders", "120");
  await page.fill("#generations", "1");
  await page.fill("#generationYears", "10");
  await page.fill("#places", "8");
  await page.click("#generate");
  await page.waitForFunction(
    () => !document.querySelector("#openResult").hidden,
    { timeout: 30000 },
  );
  assert.equal(await page.locator("#configView").isVisible(), true);
  await page.click("#openResult");
  await page.waitForFunction(() =>
    document.querySelector("#worldEyebrow").textContent.includes("9876"),
  );
  await page.selectOption("#chartMode", "vital");
  await page.click("#zoomIn");
  await page.selectOption("#direction", "descendants");
  await page.click("#reuseConfig");
  await page.selectOption("#preset", "current");
  assert.equal(await page.locator("#seed").inputValue(), "9876");
  await page.click("#addEvent");
  const idInput = page
    .locator("#eventProfiles tr")
    .first()
    .locator("input")
    .nth(6);
  await idInput.fill("bad IDs");
  await idInput.press("Tab");
  const before = await page.evaluate(() =>
    fetch("/api/job").then((r) => r.json()),
  );
  await page.click("#generate");
  const after = await page.evaluate(() =>
    fetch("/api/job").then((r) => r.json()),
  );
  assert.equal(before.id, after.id);
  await page.selectOption("#preset", "blank");
  await page.locator("#advanced summary").click();
  const json = JSON.parse(await page.locator("#configJson").inputValue());
  json.seed = 123456;
  await page.fill("#configJson", JSON.stringify(json, null, 2));
  assert.equal(await page.locator("#seed").isDisabled(), true);
  await page.click("#applyJson");
  await page.waitForFunction(
    () => document.querySelector("#seed").value === "123456",
  );
  assert.equal(await page.locator("#seed").inputValue(), "123456");
  assert.equal(await page.locator("#seed").isDisabled(), false);
  const race = page.locator("#raceProfiles tr").first().locator("input").nth(1);
  await race.fill("120");
  await race.press("Tab");
  await race.fill("");
  await race.press("Tab");
  assert.equal(
    JSON.parse(await page.locator("#configJson").inputValue()).races[0]
      .demography.max_age,
    undefined,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "output/genealogy/screenshots/config-mobile-final.png",
    fullPage: true,
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
    false,
  );
  console.log(
    JSON.stringify({
      errors,
      checks: [
        "generate by seed",
        "completion preserves view",
        "open result",
        "current preset",
        "invalid input blocks generation",
        "JSON dirty protection",
        "race inheritance",
        "responsive width",
      ],
    }),
  );
  await browser.close();
  assert.deepEqual(errors, []);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
