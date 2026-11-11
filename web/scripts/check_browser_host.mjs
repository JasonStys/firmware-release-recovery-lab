/** File: Fail closed on actual locked Chromium host/launch dependencies by Jason Stys.
 * A missing executable must fail; the ordinary launch uses Playwright's default host validation.
 * This probe is separate from the required compiled application journeys. Lines: docs/code-index.md.
 */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const root = fileURLToPath(new URL("../", import.meta.url));
assert.deepEqual(process.argv.slice(2), ["chromium"]);
assert(!process.env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS);
const lock = JSON.parse(
  await fs.readFile(path.join(root, "package-lock.json"), "utf8"),
);
const installed = JSON.parse(
  await fs.readFile(
    path.join(root, "node_modules/playwright-core/package.json"),
    "utf8",
  ),
);
assert.equal(
  installed.version,
  lock.packages["node_modules/playwright-core"].version,
);
const temporary = await fs.mkdtemp(
  path.join(os.tmpdir(), "firmware-browser-host-"),
);
try {
  await assert.rejects(
    chromium.launch({ executablePath: path.join(temporary, "absent-browser") }),
    /executable doesn't exist|Executable doesn't exist/i,
  );
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent(
      '<main><label for="entry">Résumé — 123 bytes</label><input id="entry"></main>',
    );
    await page.locator("#entry").fill("actual host dependency probe");
    assert.equal(
      await page.locator("#entry").inputValue(),
      "actual host dependency probe",
    );
    assert.equal(await page.locator("label").innerText(), "Résumé — 123 bytes");
    console.log(
      JSON.stringify({
        browser: "chromium",
        version: browser.version(),
        launch: "passed",
        missingExecutable: "rejected",
        hostValidationBypass: false,
      }),
    );
  } finally {
    await browser.close();
  }
} finally {
  // This directory was created empty by this process; never recursively remove a browser cache.
  await fs.rmdir(temporary);
}
