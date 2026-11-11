/** File: Remove only this compiler's fixed web/build output by Jason Stys. Lines: docs/code-index.md. */
import { rm } from "node:fs/promises";
import { resolve } from "node:path";
await rm(resolve(import.meta.dirname, "../build"), {
  recursive: true,
  force: true,
});
