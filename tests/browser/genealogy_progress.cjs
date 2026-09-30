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
      phase: "Calibration des fondateurs · essai 1/4",
      calibration_pass: 1,
      calibration_limit: 4,
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
    document.querySelector("#progressText").textContent.includes("essai 1/4"),
  );
  assert.equal(requests, 1);
  status = {
    ...status,
    year: 1001,
    progress: 0.08,
    calibration_pass: 2,
    phase: "Calibration des fondateurs · essai 2/4",
  };
  await page.evaluate(() => poll());
  assert.ok(
    (await page.locator("#progressText").textContent()).includes("essai 2/4"),
  );
  assert.equal(await page.locator("#progress").evaluate((e) => e.value), 0.08);
  status = {
    ...status,
    calibration_pass: undefined,
    phase: "Calibration · échantillon",
  };
  await page.evaluate(() => poll());
  assert.ok(
    (await page.locator("#progressText").textContent()).includes("4 maximum"),
  );
  assert.equal(requests, 1);
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    "PASS: numbered pilots, compatible legacy status, submission guard; no real generation submitted",
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
