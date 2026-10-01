const { chromium } = require("../../tmp/studio_qa/node_modules/playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath:
      process.env.STUDIO_BROWSER ||
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    headless: true,
  });
  const page = await browser.newPage();
  let requests = 0,
    validationStarted = false,
    status = { state: "idle" };
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const fulfill = (route, value) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  // All job writes are intercepted. This test cannot submit or cancel a real run.
  await page.route("**/api/job", (route) => fulfill(route, status));
  await page.route("**/api/generate", (route) => {
    requests++;
    status = {
      id: "progress-test",
      state: "running",
      year: 1001,
      population: 50,
      progress: 0.01,
      phase: "Simulation annuelle · régulation dynamique",
    };
    return fulfill(route, status);
  });
  await page.route("**/api/validate", async (route) => {
    validationStarted = true;
    await new Promise((resolve) => setTimeout(resolve, 300));
    return route.continue();
  });
  await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8765");
  await page.waitForFunction(
    () =>
      document.querySelector("#treeNote").textContent &&
      document.querySelector("#configJson").value &&
      document.querySelector("#seed").value,
  );
  await page.evaluate(() =>
    document.querySelector("#generate").dispatchEvent(new MouseEvent("click")),
  );
  await page.waitForFunction(
    () => document.querySelector("#generate").disabled,
  );
  await new Promise((resolve) => setTimeout(resolve, 50));
  assert.ok(validationStarted);
  // A stale idle response must not re-enable the button during submission.
  await page.evaluate(() => poll());
  assert.equal(await page.locator("#generate").isDisabled(), true);
  await page.evaluate(() =>
    document.querySelector("#generate").dispatchEvent(new MouseEvent("click")),
  );
  await page.waitForFunction(() =>
    document
      .querySelector("#progressText")
      .textContent.includes("Simulation annuelle"),
  );
  assert.equal(requests, 1);
  status = {
    ...status,
    year: 1002,
    progress: 0.08,
    phase: "Simulation annuelle · régulation dynamique",
  };
  await page.evaluate(() => poll());
  assert.ok(
    (await page.locator("#progressText").textContent()).includes("année 1002"),
  );
  assert.equal(await page.locator("#progress").evaluate((e) => e.value), 0.08);
  status = {
    ...status,
    year: 1003,
    progress: 0.12,
    phase: "Simulation annuelle · régulation dynamique",
  };
  await page.evaluate(() => poll());
  assert.ok(
    (await page.locator("#progressText").textContent()).includes("année 1003"),
  );
  assert.equal(requests, 1);
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    "PASS: single-run chronological progress, submission guard; no real generation submitted",
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
