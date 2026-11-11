/** File: Enforce closed asset identity, no remote UI resources and a fixed size budget.
 * Source UI acceptance does not replace real compiled native journeys. Lines: docs/code-index.md. */
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "../dist");
const names = [
  "index.html",
  "assets/app.js",
  "assets/model.js",
  "assets/styles.css",
];
assert.deepEqual((await readdir(root)).sort(), ["assets", "index.html"]);
assert.deepEqual((await readdir(resolve(root, "assets"))).sort(), [
  "app.js",
  "model.js",
  "styles.css",
]);
let total = 0;
for (const name of names) {
  const raw = await readFile(resolve(root, name));
  total += raw.byteLength;
  assert(raw.byteLength > 0);
  if (name.endsWith(".html"))
    assert(
      !/\b(?:src|href)=["'](?:https?:)?\/\//iu.test(
        raw.toString().replace(/<a\b[^>]*>/giu, ""),
      ),
    );
}
assert(total <= 90000, `Offline UI exceeds90KB: ${total}`);
console.log(
  `Actual production UI: ${names.length} assets, ${total}/90000 bytes`,
);
