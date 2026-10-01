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
  await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8771");
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
  await page.click('[data-config="start"]');
  await page.selectOption("#preset", "blank");
  await page.fill("#seed", "9876");
  await page.fill("#founders", "10000");
  await page.fill("#generations", "1");
  await page.fill("#generationYears", "10");
  await page.fill("#places", "500");
  await page.click("#generate");
  await page.waitForFunction(
    () => !document.querySelector("#openResult").hidden,
    { timeout: 30000 },
  );
  await page.waitForFunction(
    () => document.querySelector("#map").dataset.places === "500",
  );
  await page.waitForFunction(
    () => document.querySelector("#configView").hidden,
  );
  assert.equal(await page.locator("#exploreView").isVisible(), true);
  assert.equal(await page.locator("#placePicker option").count(), 500);
  await page.waitForFunction(() =>
    document.querySelector("#worldEyebrow").textContent.includes("9876"),
  );
  await page.selectOption("#chartMode", "vital");
  await page.click("#zoomIn");
  await page.click("#tabIndividual");
  await page.selectOption("#direction", "descendants");
  await page.click("#reuseConfig");
  await page.selectOption("#preset", "current");
  assert.equal(await page.locator("#seed").inputValue(), "9876");
  await page.click('[data-config="events"]');
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
  await page.click('[data-config="start"]');
  await page.selectOption("#preset", "blank");
  await page.click('[data-config="advanced"]');
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
  await page.click('[data-config="races"]');
  const race = page.locator("#raceProfiles tr").first().locator("input").nth(2);
  await race.fill("120");
  await race.press("Tab");
  await race.fill("");
  await race.press("Tab");
  assert.equal(
    JSON.parse(await page.locator("#configJson").inputValue()).races[0]
      .demography.max_age,
    undefined,
  );
  // Real 500-site, dated political world with sparse checkpoints.
  const political = JSON.parse(await page.locator("#configJson").inputValue());
  Object.assign(political, {
    seed: 4242,
    initial_population: 10000,
    virtual_settlements: 500,
    years: 23,
    snapshot_interval: 10,
    target_population: null,
  });
  political.nations = [
    { name: "Ouest", founded: 1000, capital: 0 },
    { name: "Est", founded: 1000, capital: 499 },
    { name: "Sel", founded: 1015, capital: 250 },
  ];
  political.nation_contacts = [
    {
      nations: ["Ouest", "Est"],
      start_year: 1000,
      marriage_factor: 0.3,
      migration_factor: 0.5,
    },
    {
      nations: ["Est", "Sel"],
      start_year: 1015,
      marriage_factor: 0.2,
      migration_factor: 0.5,
    },
  ];
  await page.click('[data-config="advanced"]');
  await page.fill("#configJson", JSON.stringify(political));
  await page.click("#applyJson");
  await page.waitForFunction(
    () =>
      document.querySelector("#previewMap").dataset.places === "500" &&
      document.querySelector("#previewStatus").textContent.includes("4242"),
  );
  await page.click("#generate");
  await page.waitForFunction(
    () =>
      document.querySelector("#worldEyebrow").textContent.includes("4242") &&
      document.querySelector("#configView").hidden,
  );
  await page.selectOption("#mapLayer", "nations");
  assert.equal(await page.locator("#year").getAttribute("max"), "3");
  await page.evaluate(() => {
    const slider = document.querySelector("#year");
    slider.value = 0;
    slider.dispatchEvent(new Event("input"));
  });
  await page.waitForFunction(
    () => document.querySelector("#map").dataset.year === "1000",
  );
  assert.ok(!(await page.locator("#mapLegend").textContent()).includes("Sel"));
  await page.evaluate(() => {
    const slider = document.querySelector("#year");
    slider.value = 3;
    slider.dispatchEvent(new Event("input"));
  });
  await page.waitForFunction(
    () => document.querySelector("#map").dataset.year === "1023",
  );
  assert.ok((await page.locator("#mapLegend").textContent()).includes("Sel"));
  assert.equal(await page.locator("#placePicker option").count(), 500);
  await page.screenshot({
    path: "output/genealogy/screenshots/nations-final.png",
    fullPage: true,
  });
  await page.click("#tabConfig");
  await page.click('[data-config="start"]');
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
        "completion auto-opens submitted world",
        "500 places in canvas and navigation",
        "open result",
        "current preset",
        "invalid input blocks generation",
        "JSON dirty protection",
        "race inheritance",
        "dated nation creation",
        "decadal checkpoints and final year",
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
