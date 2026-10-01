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
  await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8771");
  await page.waitForFunction(
    () =>
      document.querySelector("#treeNote").textContent &&
      document.querySelector("#configJson").value,
  );
  // Compact rubric navigation and structured activity editing.
  await page.click('[data-config="places"]');
  assert.equal(await page.locator("#config-start").isVisible(), false);
  const editor = page.locator(".weightEditor").first();
  await editor.locator("summary").click();
  const old = await editor.locator(".weightRow").count();
  await editor.locator(".addWeight").click();
  assert.equal(await editor.locator(".weightRow").count(), old + 1);
  await editor
    .locator(".weightRow")
    .last()
    .locator("input")
    .first()
    .fill("navigation");
  await editor
    .locator(".weightRow")
    .last()
    .locator("input")
    .first()
    .press("Tab");
  assert.ok(
    JSON.parse(await page.locator("#configJson").inputValue())
      .settlement_types[0].activities.navigation,
  );
  await editor.locator(".weightRow").last().locator("button").click();
  await page.click('[data-config="races"]');
  const before = await page.locator("#raceProfiles tr").count();
  await page.click("#addRace");
  assert.equal(await page.locator("#raceProfiles tr").count(), before + 1);
  await page.locator("#raceProfiles tr").last().locator("button").click();
  await page.click('[data-config="society"]');
  assert.ok(
    (await page.locator("#mortalityHint").textContent()).includes(
      "avant 15 ans",
    ),
  );
  assert.ok(
    await page.locator("#demography_female_infertility_rate").isVisible(),
  );
  await page.click('[data-config="start"]');
  await page.selectOption("#preset", "blank");
  await page.fill("#seed", "5123");
  await page.fill("#founders", "3000");
  await page.fill("#exactYears", "80");
  await page.fill("#places", "60");
  await page.click("#generate");
  await page.waitForFunction(
    () =>
      document.querySelector("#configView").hidden &&
      document.querySelector("#worldEyebrow").textContent.includes("5123"),
    { timeout: 30000 },
  );
  await page.waitForFunction(() =>
    document
      .querySelector("#mortalityMetrics")
      .textContent.includes("Enfants morts"),
  );
  assert.ok(
    !(await page.locator("#mortalityMetrics").textContent()).includes(
      "Non simulé",
    ),
  );
  await page.screenshot({
    path: "output/genealogy/screenshots/world-workspace.png",
    fullPage: true,
  });
  // Linked chart hover/click, range exploration and timeline.
  await page.selectOption("#chartMode", "movement");
  const checkpoints = page.locator('#chart rect[role="button"]');
  await checkpoints.nth(1).hover();
  assert.ok(
    (await page.locator("#chartReadout").textContent()).includes("1010"),
  );
  await checkpoints.nth(1).click();
  await page.waitForFunction(
    () => document.querySelector("#map").dataset.year === "1010",
  );
  await page.selectOption("#chartFrom", "2");
  await page.selectOption("#chartTo", "4");
  assert.equal(await page.locator('#chart rect[role="button"]').count(), 3);
  await page.click("#resetChart");
  assert.equal(await page.locator('#chart rect[role="button"]').count(), 9);
  await page.click("#nextYear");
  await page.waitForFunction(
    () => document.querySelector("#map").dataset.year === "1020",
  );
  const mapState = await page.locator("#map").getAttribute("data-year");
  await page.click("#openVillage");
  assert.equal(await page.locator("#globalView").isVisible(), false);
  assert.equal(await page.locator("#map").getAttribute("data-year"), mapState);
  assert.equal(await page.locator("#localMapDock #map").count(), 1);
  await page.selectOption("#residentSex", "1");
  assert.equal(await page.locator('#residents [data-sex="0"]').count(), 0);
  assert.ok((await page.locator('#residents [data-sex="1"]').count()) > 0);
  await page.selectOption("#residentSex", "");
  const chip = page.locator("#residents [data-person]").first();
  const id = await chip.getAttribute("data-person");
  await chip.click();
  await page.waitForFunction(
    (id) => document.querySelector("#identity").value === id,
    id,
  );
  assert.ok(
    (await page.locator("#personFacts").textContent()).includes(
      "Fertilité biologique",
    ),
  );
  await page.click("#locatePerson");
  const parentId = await page.evaluate(async () => {
    for (let id = 0; id < 100; id++) {
      const p = await fetch("/api/person?id=" + id).then((r) => r.json());
      if (p.children.length >= 3) return id;
    }
    throw Error("No recorded parent found in test fixture");
  });
  await page.fill("#identity", String(parentId));
  await page.locator("#search button.primary").click();
  await page.waitForFunction(
    (id) => document.querySelector("#identity").value === String(id),
    parentId,
  );
  await page.selectOption("#direction", "descendants");
  await page.selectOption("#depth", "6");
  await page.waitForFunction(
    () => document.querySelectorAll(".treeNode").length > 1,
  );
  const vb = await page.locator("#tree").getAttribute("viewBox");
  await page.click("#treeZoomIn");
  const zoomed = await page.locator("#tree").getAttribute("viewBox");
  assert.notEqual(vb, zoomed);
  await page.locator("#treeViewport").focus();
  await page.keyboard.press("ArrowRight");
  assert.notEqual(await page.locator("#tree").getAttribute("viewBox"), zoomed);
  const box = await page.locator("#tree").boundingBox();
  const prior = await page.locator("#tree").getAttribute("viewBox");
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.7);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width * 0.7 + 50,
    box.y + box.height * 0.7 + 30,
    { steps: 5 },
  );
  await page.mouse.up();
  assert.notEqual(await page.locator("#tree").getAttribute("viewBox"), prior);
  await page.click("#treeFit");
  const nodes = await page
    .locator(".treeNode")
    .evaluateAll((nodes) =>
      nodes.map((n) => ({
        id: n.dataset.person,
        t: n.getAttribute("transform"),
      })),
    );
  assert.equal(new Set(nodes.map((n) => n.id)).size, nodes.length);
  const coords = nodes.map((n) =>
    n.t
      .match(/translate\(([^,]+),([^\)]+)\)/)
      .slice(1)
      .map(Number),
  );
  for (let i = 0; i < coords.length; i++)
    for (let j = i + 1; j < coords.length; j++)
      if (coords[i][1] === coords[j][1])
        assert.ok(Math.abs(coords[i][0] - coords[j][0]) >= 183);
  await page.screenshot({
    path: "output/genealogy/screenshots/individual-workspace.png",
    fullPage: true,
  });
  // Keyboard-select a family node and return to the global view without losing state.
  const familyNode = page.locator(".treeNode").last(),
    familyId = await familyNode.getAttribute("data-person");
  await familyNode.focus();
  await page.keyboard.press("Enter");
  await page.waitForFunction(
    (id) => document.querySelector("#identity").value === id,
    familyId,
  );
  await page.click("#tabExplore");
  assert.equal(await page.locator("#globalMapDock #map").count(), 1);
  await page.click("#tabIndividual");
  assert.equal(await page.locator("#identity").inputValue(), familyId);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "output/genealogy/screenshots/individual-mobile.png",
    fullPage: true,
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  await page.click("#tabExplore");
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  await page.click("#tabConfig");
  await page.click('[data-config="places"]');
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  console.log(
    JSON.stringify({
      errors,
      checks: [
        "rubric navigation",
        "structured activity CRUD",
        "people CRUD",
        "lifetime rate controls",
        "mortality hint and observed rates",
        "chart hover/date click/range",
        "shared dated map",
        "sex filter and person selection",
        "parental states",
        "tree zoom/keyboard/pan/fit",
        "pedigree deduplication and no overlap",
        "mobile overflow",
      ],
    }),
  );
  assert.deepEqual(errors, []);
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
