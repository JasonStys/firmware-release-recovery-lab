/** File: Compile and copy only the fixed offline application asset inventory by Jason Stys.
 * build output is owned; no runtime dependency or remote resource is included. Lines: docs/code-index.md. */
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "..");
const destination = resolve(root, "dist");
await rm(destination, { recursive: true, force: true });
await mkdir(resolve(destination, "assets"), { recursive: true });
for (const [source, target] of [
  ["public/index.html", "index.html"],
  ["build/src/app.js", "assets/app.js"],
  ["build/src/model.js", "assets/model.js"],
  ["src/styles.css", "assets/styles.css"],
]) {
  await writeFile(
    resolve(destination, target),
    await readFile(resolve(root, source)),
  );
}
console.log("Built four actual offline UI assets");
