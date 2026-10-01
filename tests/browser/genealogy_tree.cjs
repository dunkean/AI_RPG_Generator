// Focused regression against a running studio; does not generate a new world.
const { chromium } = require("../../tmp/studio_qa/node_modules/playwright");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({
    executablePath:
      process.env.STUDIO_BROWSER ||
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    headless: true,
  });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(process.env.STUDIO_URL || "http://127.0.0.1:8772");
    await page.waitForFunction(() =>
      document.querySelector("#treeNote").textContent.includes("affichées"),
    );
    await page.click("#tabIndividual");
    for (const depth of ["2", "6", "12", "2"]) {
      const response = page.waitForResponse(
        (r) =>
          r.url().includes("/api/lineage?") &&
          new URL(r.url()).searchParams.get("depth") === depth,
      );
      await page.selectOption("#depth", depth);
      const result = await (await response).json();
      const actual = Math.max(0, ...result.people.map((p) => p.generation));
      await page.waitForFunction(
        ({ depth, actual }) =>
          document
            .querySelector("#treeNote")
            .textContent.startsWith(
              `${actual} / ${depth} générations affichées`,
            ),
        { depth, actual },
      );
      assert.equal(
        await page.locator("#tree .treeNode").count(),
        result.people.length + 1,
      );
      assert.equal(
        (await page.locator("#treeNote").textContent()).includes(
          "dernière génération potentiellement incomplète",
        ),
        result.truncated,
      );
    }
    await page.route("**/api/lineage?**", async (route) => {
      if (new URL(route.request().url()).searchParams.get("depth") === "6")
        await new Promise((resolve) => setTimeout(resolve, 350));
      await route.continue();
    });
    const finished = page.waitForResponse(
      (r) =>
        r.url().includes("/api/lineage?") &&
        new URL(r.url()).searchParams.get("depth") === "2",
    );
    await page.selectOption("#depth", "6");
    await page.selectOption("#depth", "2");
    const latest = await (await finished).json();
    const actual = Math.max(0, ...latest.people.map((p) => p.generation));
    await page.waitForTimeout(500);
    assert.ok(
      (await page.locator("#treeNote").textContent()).startsWith(
        `${actual} / 2 générations affichées`,
      ),
    );
    assert.deepEqual(errors, []);
    console.log("Tree depth changes, truncation and stale responses: OK");
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
