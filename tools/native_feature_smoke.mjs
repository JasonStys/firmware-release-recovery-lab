/** File: Use the actual application UI, original Rust engines and real downloads by Jason Stys.
 * Native callers bind a full source SHA; the explicit source harness uses development identity.
 * No mock API, preset executable, user profile or external service is used. Lines: docs/code-index.md.
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "../web/node_modules/playwright-core/index.mjs";

const [url, output, expectedSource] = process.argv.slice(2);
if (
  !url ||
  !output ||
  !(
    expectedSource === "development" ||
    /^[a-f0-9]{40}$/u.test(expectedSource ?? "")
  )
)
  throw new Error(
    "Expected owned URL, fresh output and explicit source identity",
  );
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1280, height: 950 },
  acceptDownloads: true,
});
const errors = [];
const created = [];
page.on("pageerror", (error) => errors.push(error.message));

async function check(selector, phrase) {
  await page
    .locator(selector)
    .filter({ hasText: phrase })
    .waitFor({ timeout: 15000 });
}
async function downloaded(id) {
  const waiting = page.waitForEvent("download", { timeout: 10000 });
  await page.locator(id).click();
  const download = await waiting;
  const stream = await download.createReadStream();
  assert(stream);
  let count = 0;
  const blocks = [];
  for await (const block of stream) {
    count += block.length;
    assert(count <= 8 * 1024 * 1024);
    blocks.push(block);
  }
  return JSON.parse(Buffer.concat(blocks).toString("utf8"));
}
async function run() {
  const waiting = page.waitForResponse(
    (response) => response.url().endsWith("/api/run"),
    { timeout: 20000 },
  );
  await page.locator("#run").click();
  const response = await waiting;
  assert.equal(response.status(), 201);
  const evidence = await response.json();
  await check("#selected", evidence.id);
  assert.deepEqual(await downloaded("#export-evidence"), evidence);
  assert.equal(evidence.engine.sourceCommit, expectedSource);
  assert.equal(evidence.version, "0.2.0");
  created.push({
    id: evidence.id,
    kind: evidence.input.kind,
    status: evidence.report.status,
  });
  return evidence;
}
async function loadExample(name, title) {
  await page.locator("#example").selectOption(name);
  await page.locator("#load-example").click();
  await page.locator("#title").fill(title);
}
async function api(path) {
  return page.evaluate(async (target) => {
    const response = await fetch(target, {
      headers: {
        "X-Firmware-Capability":
          sessionStorage.getItem("firmware-owner-capability") ?? "",
      },
    });
    if (!response.ok) throw new Error("Owned evidence request failed");
    return response.json();
  }, path);
}
try {
  await page.goto(url, { waitUntil: "networkidle", timeout: 20000 });
  await check("#status", "Owned application ready");
  await check("#identity", expectedSource);
  await page.locator("#title").fill("Cold-chain%_ specimen");
  const device = [
    {
      id: "custom-alpha",
      hardware: "custom-fictional-family",
      minimum_version: "1.0.0",
      initial_version: "1.0.0",
      initial_image_hex: "7631",
      outcome: "confirm",
    },
  ];
  await page.locator("#devices").fill(JSON.stringify(device));
  await page.locator("#release-version").fill("2.1.0");
  await page.locator("#release-id").fill("custom-training-release");
  await page.locator("#hardware").fill("custom-fictional-family");
  const bytes = Buffer.from([0, 1, 127, 128, 255]);
  await page.locator("#image-file").setInputFiles({
    name: "inert-image.bin",
    mimeType: "application/octet-stream",
    buffer: bytes,
  });
  await check("#status", "Loaded supported local input");
  assert.equal(await page.locator("#image").inputValue(), "00017f80ff");
  const steps = ["stage", "activate", "boot", "confirm"].map((kind) => ({
    device: "custom-alpha",
    action: kind === "activate" ? { kind, slot: "B", attempts: 1 } : { kind },
    fault: null,
  }));
  await page.locator("#steps").fill(JSON.stringify(steps));
  const healthy = await run();
  assert.equal(healthy.report.status, "completed");
  assert.equal(healthy.report.final["custom-alpha"].confirmed, "B");
  assert.equal(healthy.report.final["custom-alpha"].generation, 4);
  assert.deepEqual(healthy.report.final["custom-alpha"].slots.B.version, {
    major: 2,
    minor: 1,
    patch: 0,
  });
  assert.equal(
    healthy.report.final["custom-alpha"].slots.B.image_sha256,
    createHash("sha256").update(bytes).digest("hex"),
  );
  assert.deepEqual(
    healthy.report.timeline.map((row) => row.after.generation),
    [1, 2, 3, 4],
  );
  assert.equal(healthy.report.timeline[2].selected_slot, "B");
  const exportedPackage = await downloaded("#export-package");
  assert.deepEqual(exportedPackage, healthy.report.package);
  assert.deepEqual(await downloaded("#export-input"), healthy.input);
  await page
    .locator("#results-section")
    .screenshot({ path: resolve(output, "01-custom-promotion.png") });

  const unsupported = structuredClone(exportedPackage);
  unsupported.manifest.payload.unsigned_notes = "not accepted";
  await page.locator("#package-file").setInputFiles({
    name: "unknown-unsigned-field.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(unsupported)),
  });
  await check("#status", "Loaded supported local input");
  const refused = page.waitForResponse(
    (response) => response.url().endsWith("/api/run"),
    { timeout: 15000 },
  );
  await page.locator("#run").click();
  assert.equal((await refused).status(), 400);
  await check("#status", "unknown field");
  assert.deepEqual(await downloaded("#export-evidence"), healthy);
  assert.equal((await api("/api/history")).total, 1);

  const corrupted = { ...exportedPackage, image_hex: "0000" };
  await page.locator("#title").fill("Rejected mismatched image");
  await page.locator("#package-file").setInputFiles({
    name: "wrong-image.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(corrupted)),
  });
  await check("#status", "Loaded supported local input");
  const blocked = await run();
  assert.equal(blocked.report.status, "blocked");
  assert.equal(blocked.report.final["custom-alpha"].confirmed, "A");
  assert.equal(blocked.report.final["custom-alpha"].generation, 0);
  assert.equal(blocked.report.unattempted_steps, 3);
  assert.match(blocked.report.timeline[0].reason, /digest mismatch/u);

  await loadExample("rollback", "Expected unconfirmed rollback");
  const rollback = await run();
  assert.equal(rollback.report.final.alpha.phase, "rolled_back");
  assert.equal(rollback.report.final.alpha.confirmed, "A");
  assert.equal(rollback.report.final.alpha.generation, 4);
  await loadExample("fleet", "Read-only second-cohort stop");
  const fleet = await run();
  assert.equal(fleet.report.status, "blocked");
  assert.equal(fleet.report.report.stopped_after_cohort, 2);
  assert.deepEqual(fleet.report.before, fleet.report.after);
  assert.deepEqual(
    fleet.report.report.devices.map((row) => row.rehearsal),
    ["confirmed", "rolled_back", "not_attempted_after_stop"],
  );
  await check("#table-body", "Not attempted after stop");
  await page
    .locator("#results-section")
    .screenshot({ path: resolve(output, "02-cohort-evidence.png") });

  await page.locator("#workflow").selectOption("campaign");
  await page.locator("#title").fill("Original all-boundary campaign");
  const campaign = await run();
  assert.equal(campaign.report.report.scenarios, 12);
  assert.equal(campaign.report.report.recovered, 12);
  assert.equal(campaign.report.report.safety_invariants_preserved, 12);
  assert.equal(campaign.report.report.stable_recoveries, 4);
  assert.equal(campaign.report.report.forward_progress_recoveries, 8);
  assert(Number.isInteger(campaign.report.report.elapsed_milliseconds));
  await page.locator("#iterations").fill("6");
  const badBudget = page.waitForResponse(
    (response) => response.url().endsWith("/api/run"),
    { timeout: 15000 },
  );
  await page.locator("#run").click();
  assert.equal((await badBudget).status(), 400);
  await check("#status", "1..5");
  assert.deepEqual(await downloaded("#export-evidence"), campaign);

  await loadExample("interrupted", "Named interrupted metadata write");
  const interrupted = await run();
  assert.equal(interrupted.report.status, "interrupted_recovered");
  assert.equal(interrupted.report.final.alpha.generation, 0);
  assert.equal(interrupted.report.timeline[0].fault_triggered, true);
  assert.equal(interrupted.report.unattempted_steps, 3);

  const forged = structuredClone(healthy);
  forged.report.final["custom-alpha"].confirmed = "invented";
  await page.locator("#title").fill("Rerun imported claims");
  const rerunResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/run"),
    { timeout: 20000 },
  );
  await page.locator("#evidence-file").setInputFiles({
    name: "forged-report.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(forged)),
  });
  const response = await rerunResponse;
  assert.equal(response.status(), 201);
  const rerun = await response.json();
  await check("#selected", rerun.id);
  assert.notEqual(rerun.id, healthy.id);
  assert.deepEqual(rerun.report.final, healthy.report.final);
  assert.equal(rerun.engine.sourceCommit, expectedSource);
  created.push({
    id: rerun.id,
    kind: rerun.input.kind,
    status: rerun.report.status,
  });

  await page.locator("#search").fill("%_");
  await page.locator("#refresh").click();
  await check("#history-total", "1 matching saved rehearsals");
  await page.locator("#history button").click();
  await check("#selected", healthy.id);
  assert.deepEqual(await downloaded("#export-evidence"), healthy);
  assert.equal((await api("/api/history")).total, 7);
  await check("#identity", expectedSource);
  const mobileLayouts = [];
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    const layout = await page.evaluate(() => {
      const identity = document.getElementById("identity");
      if (!identity) throw new Error("Actual source identity is absent");
      return {
        viewport: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        overflow: document.documentElement.scrollWidth > innerWidth,
        identityWidth: identity.getBoundingClientRect().width,
        identityScrollWidth: identity.scrollWidth,
        identityOverflowX: getComputedStyle(identity).overflowX,
      };
    });
    mobileLayouts.push(layout);
    console.log(JSON.stringify({ mobileLayout: layout }));
    assert.equal(
      layout.overflow,
      false,
      `Actual mobile application overflows: ${JSON.stringify(layout)}`,
    );
    assert(
      !["hidden", "clip"].includes(layout.identityOverflowX),
      "Source identity was clipped instead of wrapped",
    );
  }
  await page.locator("#export-input").focus();
  assert.equal(
    await page
      .locator("#export-input")
      .evaluate((node) => node === document.activeElement),
    true,
  );
  assert.deepEqual(errors, []);
  await writeFile(
    resolve(output, "browser-acceptance.json"),
    JSON.stringify(
      {
        passed: true,
        source: expectedSource,
        mode:
          expectedSource === "development"
            ? "explicit source harness"
            : "actual compiled owned application",
        records: created,
        retainedRecords: 7,
        independent: {
          promotionGeneration: 4,
          rollbackGeneration: 4,
          blockedGeneration: 0,
          cohortStop: 2,
          campaignScenarios: 12,
          stableRecoveries: 4,
          forwardRecoveries: 8,
          interruptedGeneration: 0,
        },
        negativeInputsPreserved: true,
        importedClaimsRerun: true,
        mobileOverflow: false,
        mobileLayouts,
        pageErrors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  await page.locator("#quit").click();
  await check("#status", "Closing the actual owned application");
} finally {
  await browser.close();
}
