/** File: Rehearsal input construction and bounded interchange by Jason Stys.
 * Functions validate only browser shapes; the original Rust engine enforces domain/signature rules.
 * Variables describe editable fictional examples, never device endpoints. Lines: docs/code-index.md.
 */

export type Kind = "lifecycle" | "preflight" | "campaign";
export type JsonObject = Record<string, unknown>;
export interface Device extends JsonObject {
  id: string;
  hardware: string;
  minimum_version: string;
  initial_version: string;
  initial_image_hex: string;
  outcome: "confirm" | "exhaust";
}
export interface Step extends JsonObject {
  device: string;
  action: JsonObject;
  fault: string | null;
}
export interface Evidence extends JsonObject {
  id: string;
  title: string;
  input: JsonObject;
  report: JsonObject;
}

/** Translate only known result codes; user identifiers and unknown values remain literal. */
export function outcomeLabel(value: unknown): string {
  const labels: Record<string, string> = {
    completed: "Completed rehearsal",
    blocked: "Blocked rehearsal",
    reviewed: "Read-only reviewed",
    interrupted_recovered: "Interrupted and recovered",
    applied: "Applied",
    rejected: "Rejected",
    stable: "Stable",
    staged: "Staged",
    awaiting_health: "Awaiting supplied health",
    rolled_back: "Rolled back",
    confirmed: "Confirmed",
    not_attempted_after_stop: "Not attempted after stop",
    confirm: "Confirm (assumed)",
    exhaust: "Exhaust attempts (assumed)",
    compatible: "Compatible",
    lifecycle: "Lifecycle",
    preflight: "Read-only preflight",
    campaign: "Interruption campaign",
  };
  return labels[String(value)] ?? String(value);
}

export function object(value: unknown): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error("Expected a JSON object");
  return value as JsonObject;
}

export function parse(text: string, maximum = 256 * 1024): unknown {
  if (new TextEncoder().encode(text).byteLength > maximum)
    throw new Error("JSON exceeds its byte limit");
  return JSON.parse(text) as unknown;
}

export function devices(value: unknown): Device[] {
  if (!Array.isArray(value) || value.length < 1 || value.length > 64)
    throw new Error("Provide1..64 fictional devices");
  const ids = new Set<string>();
  return value.map((entry: unknown) => {
    const device = object(entry);
    if (
      typeof device.id !== "string" ||
      !device.id.trim() ||
      ids.has(device.id)
    )
      throw new Error("Each device needs a unique ID");
    ids.add(device.id);
    return device as Device;
  });
}

export function steps(value: unknown): Step[] {
  if (!Array.isArray(value) || value.length > 64)
    throw new Error("Use at most64 ordered transitions");
  return value.map((entry: unknown) => {
    const step = object(entry);
    if (
      typeof step.device !== "string" ||
      typeof object(step.action).kind !== "string"
    )
      throw new Error("Each transition needs a device and action");
    return step as Step;
  });
}

export function request(value: unknown): JsonObject {
  const input = object(value);
  if (input.kind === "lifecycle") {
    const plan = object(input.plan);
    devices(plan.devices);
    steps(plan.steps);
    object(plan.release);
  } else if (input.kind === "preflight") {
    const fleet = object(input.fleet);
    devices(fleet.devices);
    object(fleet.release);
  } else if (input.kind !== "campaign")
    throw new Error("Choose a supported rehearsal workflow");
  if (new TextEncoder().encode(JSON.stringify(input)).byteLength > 256 * 1024)
    throw new Error("Rehearsal exceeds256KiB");
  return input;
}

export function example(
  outcome: "healthy" | "rollback" | "interrupted" | "fleet",
): JsonObject {
  const device: Device = {
    id: "alpha",
    hardware: "fictional-controller",
    minimum_version: "1.0.0",
    initial_version: "1.0.0",
    initial_image_hex: "7631",
    outcome: "confirm",
  };
  const release = {
    mode: "build",
    version: "2.0.0",
    release_id: "training-release",
    compatible_hardware: ["fictional-controller"],
    max_boot_attempts: 1,
    image_hex: "7632",
  };
  if (outcome === "fleet")
    return {
      kind: "preflight",
      fleet: {
        devices: [
          device,
          { ...device, id: "beta", outcome: "exhaust" },
          { ...device, id: "gamma" },
        ],
        release,
        cohort_size: 1,
      },
    };
  const kinds = [
    "stage",
    "activate",
    "boot",
    outcome === "rollback" ? "fail" : "confirm",
  ];
  const actions = kinds.map((kind, index) => ({
    device: "alpha",
    action:
      kind === "activate"
        ? { kind, slot: "B", attempts: 1 }
        : kind === "fail"
          ? { kind, reason: "supplied health failure" }
          : { kind },
    fault: outcome === "interrupted" && index === 0 ? "after_temp_write" : null,
  }));
  return {
    kind: "lifecycle",
    plan: { devices: [device], release, steps: actions },
  };
}

export function hex(bytes: Uint8Array): string {
  if (bytes.byteLength === 0 || bytes.byteLength > 65536)
    throw new Error("An inert image uses1..65536 bytes");
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join(
    "",
  );
}

export async function jsonFile(file: File, maximum: number): Promise<unknown> {
  if (file.size > maximum)
    throw new Error("Selected JSON file exceeds its byte limit");
  const buffer = await file.arrayBuffer();
  if (buffer.byteLength !== file.size || buffer.byteLength > maximum)
    throw new Error("Selected file changed while reading");
  return parse(
    new TextDecoder("utf-8", { fatal: true }).decode(buffer),
    maximum,
  );
}
