/** File: Independent supported input/interchange and safety-bound oracles by Jason Stys.
 * The real Rust and compiled-browser suites separately prove domain execution. Lines: docs/code-index.md. */
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  devices,
  example,
  hex,
  jsonFile,
  object,
  outcomeLabel,
  parse,
  request,
  steps,
} from "../src/model.js";
test("optional examples remain editable complete inputs rather than certified results", () => {
  for (const name of ["healthy", "rollback", "interrupted", "fleet"] as const) {
    const value = request(example(name));
    assert.equal(value.kind, name === "fleet" ? "preflight" : "lifecycle");
    assert.equal("report" in value, false);
    const configuration = object(value[name === "fleet" ? "fleet" : "plan"]);
    assert.equal(
      devices(configuration.devices).length,
      name === "fleet" ? 3 : 1,
    );
    const release = object(configuration.release);
    release.image_hex = "434f53544f4d";
    assert.equal(
      object(request(value)[name === "fleet" ? "fleet" : "plan"]).release,
      release,
    );
  }
});

test("known outcomes are readable while unknown user identifiers remain literal", () => {
  assert.equal(
    outcomeLabel("not_attempted_after_stop"),
    "Not attempted after stop",
  );
  assert.equal(
    outcomeLabel("interrupted_recovered"),
    "Interrupted and recovered",
  );
  assert.equal(
    outcomeLabel("custom_controller_alpha"),
    "custom_controller_alpha",
  );
});
test("unsupported/duplicate identities and overlarge step sets are refused", () => {
  const device = devices(object(example("healthy").plan).devices)[0];
  assert(device);
  assert.throws(() => devices([device, device]), /unique/u);
  assert.throws(() => devices([]), /64/u);
  assert.throws(
    () =>
      steps(
        Array.from({ length: 65 }, () => ({
          device: "alpha",
          action: { kind: "boot" },
        })),
      ),
    /64/u,
  );
  assert.throws(() => steps([{ device: "alpha", action: null }]));
  assert.throws(() => request({ kind: "live-flash", host: "127.0.0.1" }));
});
test("inert binary values preserve exact leading zero/high bytes and enforce bounds", () => {
  assert.equal(hex(new Uint8Array([0, 1, 127, 128, 255])), "00017f80ff");
  assert.throws(() => hex(new Uint8Array(0)));
  assert.throws(() => hex(new Uint8Array(65537)));
});
test("real UTF8 local JSON files retain content and do not parse corrupt or changed bytes", async () => {
  const value = example("rollback");
  const file = new File([JSON.stringify(value)], "fictional.json", {
    type: "application/json",
  });
  assert.deepEqual(await jsonFile(file, 262144), value);
  await assert.rejects(
    jsonFile(new File([new Uint8Array([255])], "corrupt.json"), 256),
    /encoded|encoding|valid/iu,
  );
  await assert.rejects(jsonFile(file, 1), /limit/u);
  Object.defineProperty(file, "arrayBuffer", {
    value: async () => new ArrayBuffer(1),
  });
  await assert.rejects(jsonFile(file, 262144), /changed/u);
  assert.throws(() => parse("{}", 1), /limit/u);
  assert.throws(() => object([]));
});
