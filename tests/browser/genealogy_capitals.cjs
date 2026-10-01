const { chromium } = require("../../tmp/studio_qa/node_modules/playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath:
      process.env.STUDIO_BROWSER ||
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    headless: true,
  });
  const page = await browser.newPage(),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8772");
  await page.waitForFunction(() => document.querySelector("#configJson").value);
  await page.selectOption("#preset", "civilization");
  await page.fill("#places", "16");
  await page.locator("#places").press("Tab");
  let draft = JSON.parse(await page.locator("#configJson").inputValue());
  assert.deepEqual(
    draft.nations.map((n) => n.capital),
    [null, null, null],
  );
  assert.ok(
    (await page.locator("#mapAdjustmentNotice").textContent()).includes(
      "Valdorie",
    ),
  );
  let result = await page.evaluate(async (scenario) => {
    const r = await fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    return { ok: r.ok, value: await r.json() };
  }, draft);
  assert.equal(result.ok, true);
  await page.waitForFunction(
    () => document.querySelector("#previewMap").dataset.places === "16",
  );
  await page.selectOption("#preset", "civilization");
  await page.fill("#places", "400");
  await page.locator("#places").press("Tab");
  draft = JSON.parse(await page.locator("#configJson").inputValue());
  assert.deepEqual(
    draft.nations.map((n) => n.capital),
    [25, 310, null],
  );
  await page.click('[data-config="nations"]');
  const capital = page
    .locator("#nationProfiles tr")
    .first()
    .locator("input")
    .nth(3);
  assert.equal(await capital.getAttribute("max"), "399");
  await capital.fill("500");
  await capital.press("Tab");
  assert.equal(await capital.evaluate((e) => e.checkValidity()), false);
  await capital.fill("");
  await capital.press("Tab");
  assert.equal(await capital.evaluate((e) => e.checkValidity()), true);
  assert.equal(
    JSON.parse(await page.locator("#configJson").inputValue()).nations[0]
      .capital,
    null,
  );
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    "PASS: 500→16 and 500→400 maps validate; preserved valid capitals, visible auto-placement, live preview, invalid manual IDs blocked. No generation submitted.",
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
