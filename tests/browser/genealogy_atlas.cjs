const { chromium } = require("../../tmp/studio_qa/node_modules/playwright");
const assert = require("node:assert/strict");
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
  await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8772");
  await page.waitForFunction(
    () => document.querySelector("#treeNote").textContent,
  );
  await page.click("#tabIndividual");
  await page.waitForFunction(
    () => document.querySelector("#residentCanvas").dataset.points > 0,
  );
  assert.equal(await page.locator("#more").count(), 0);
  const box = await page.locator("#residentCanvas").boundingBox();
  assert.ok(box.width > 800);
  assert.equal(
    await page.evaluate(() => atlas.groups.reduce((n, g) => n + g.count, 0)),
    Number(await page.locator("#residentCanvas").getAttribute("data-matched")),
  );
  const point = await page.evaluate(() => {
    const h = atlasHits.find((h) => h.group);
    return {
      x: h.x * atlasView.scale + atlasView.x,
      y: h.y * atlasView.scale + atlasView.y,
    };
  });
  await page.mouse.move(box.x + point.x, box.y + point.y);
  await page.waitForFunction(
    () => !document.querySelector("#residentTooltip").hidden,
  );
  await page.mouse.click(box.x + point.x, box.y + point.y);
  await page.waitForFunction(
    () =>
      document.querySelector("#residentCanvas").dataset.mode === "individuals",
  );
  const individual = await page.evaluate(() => {
    const h = atlasHits.find((h) => h.person);
    return {
      id: h.person.id,
      x: h.x * atlasView.scale + atlasView.x,
      y: h.y * atlasView.scale + atlasView.y,
    };
  });
  await page.mouse.click(box.x + individual.x, box.y + individual.y);
  await page.waitForFunction(
    (id) =>
      document
        .querySelector("#personTitle")
        .textContent.includes("#" + id + " ·"),
    individual.id,
  );
  await page.locator("#residentCanvas").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "output/genealogy/screenshots/resident-atlas.png",
    fullPage: true,
  });
  const scale = await page.evaluate(() => atlasView.scale);
  await page.click("#atlasZoomIn");
  assert.ok((await page.evaluate(() => atlasView.scale)) > scale);
  await page.click("#atlasReset");
  await page.selectOption("#residentSex", "1");
  await page.waitForFunction(
    () => atlas.groups.length && atlas.groups.every((g) => g.sex === 1),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  assert.deepEqual(errors, []);
  console.log(
    "PASS: exact cohort counts, full-width canvas, hover, cohort drill-down, individual selection, zoom, full-population sex filter, mobile; no simulation submitted.",
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
