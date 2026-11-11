/** File: Actual editable release/recovery, evidence selection and durable history UI by Jason Stys.
 * Async operations preserve selected evidence on refusal and ignore stale edit/search responses.
 * Variables are current selection, revision, pagination and one owner capability. Lines: docs/code-index.md.
 */
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
  type Evidence,
  type JsonObject,
  type Kind,
} from "./model.js";

function element<T extends HTMLElement>(id: string, kind: { new (): T }): T {
  const value = document.getElementById(id);
  if (!(value instanceof kind))
    throw new Error(`Missing interface control ${id}`);
  return value;
}
const input = (id: string): HTMLInputElement => element(id, HTMLInputElement);
const area = (id: string): HTMLTextAreaElement =>
  element(id, HTMLTextAreaElement);
const select = (id: string): HTMLSelectElement =>
  element(id, HTMLSelectElement);
const button = (id: string): HTMLButtonElement =>
  element(id, HTMLButtonElement);
const text = (id: string, value: string): void => {
  element(id, HTMLElement).textContent = value;
};
const encoded = (value: unknown): string => JSON.stringify(value, null, 2);
const workflow = select("workflow");
let revision = 0;
let searchRevision = 0;
let busy = false;
let selected: Evidence | null = null;
let page = 0;
let total = 0;
const fragment = new URLSearchParams(location.hash.slice(1));
const received = fragment.get("native");
if (received !== null) {
  sessionStorage.setItem("firmware-owner-capability", received);
  history.replaceState(null, "", location.pathname + location.search);
}
const capability = sessionStorage.getItem("firmware-owner-capability") ?? "";

function status(message: string, failed = false): void {
  text("status", message);
  element("status", HTMLElement).classList.toggle("error", failed);
}
function failure(error: unknown): void {
  status(
    error instanceof Error ? error.message : "The operation could not complete",
    true,
  );
}

async function api(path: string, body?: JsonObject): Promise<JsonObject> {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined
        ? { "X-Firmware-Capability": capability }
        : {
            "X-Firmware-Capability": capability,
            "Content-Type": "application/json",
          },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
  });
  const result = object(await response.json());
  if (!response.ok)
    throw new Error(
      typeof result.error === "string"
        ? result.error
        : "The rehearsal was refused; prior evidence is unchanged",
    );
  return result;
}

function currentInput(): JsonObject {
  const kind = workflow.value as Kind;
  if (kind === "campaign")
    return request({ kind, iterations: Number(input("iterations").value) });
  const release =
    select("package-mode").value === "import"
      ? {
          mode: "import",
          manifest: parse(area("manifest").value, 65536),
          image_hex: area("image").value.replace(/\s+/gu, ""),
        }
      : {
          mode: "build",
          version: input("release-version").value,
          release_id: input("release-id").value,
          compatible_hardware: input("hardware")
            .value.split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          max_boot_attempts: Number(input("attempts").value),
          image_hex: area("image").value.replace(/\s+/gu, ""),
        };
  const configured = devices(parse(area("devices").value));
  return request(
    kind === "lifecycle"
      ? {
          kind,
          plan: {
            devices: configured,
            release,
            steps: steps(parse(area("steps").value)),
          },
        }
      : {
          kind,
          fleet: {
            devices: configured,
            release,
            cohort_size: Number(input("cohort").value),
          },
        },
  );
}

function fill(value: unknown): void {
  const incoming = request(value);
  const kind = incoming.kind as Kind;
  workflow.value = kind;
  if (kind === "campaign")
    input("iterations").value = String(incoming.iterations);
  else {
    const configuration = object(
      incoming[kind === "lifecycle" ? "plan" : "fleet"],
    );
    area("devices").value = encoded(configuration.devices);
    const release = object(configuration.release);
    select("package-mode").value = String(release.mode);
    area("image").value = String(release.image_hex);
    if (release.mode === "import")
      area("manifest").value = encoded(release.manifest);
    else {
      input("release-version").value = String(release.version);
      input("release-id").value = String(release.release_id);
      input("hardware").value = (release.compatible_hardware as unknown[])
        .map(String)
        .join(", ");
      input("attempts").value = String(release.max_boot_attempts);
    }
    if (kind === "lifecycle")
      area("steps").value = encoded(configuration.steps);
    else input("cohort").value = String(configuration.cohort_size);
  }
  revision += 1;
}

function saveFile(name: string, value: unknown): void {
  const url = URL.createObjectURL(
    new Blob([encoded(value) + "\n"], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function table(headers: string[], rows: unknown[][], caption: string): void {
  const head = element("table-head", HTMLTableSectionElement);
  const body = element("table-body", HTMLTableSectionElement);
  head.replaceChildren();
  body.replaceChildren();
  text("table-caption", caption);
  const row = document.createElement("tr");
  headers.forEach((value) => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = value;
    row.append(cell);
  });
  head.append(row);
  rows.forEach((values) => {
    const entry = document.createElement("tr");
    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = typeof value === "string" ? value : encoded(value);
      entry.append(cell);
    });
    body.append(entry);
  });
}

function show(value: JsonObject): void {
  if (typeof value.id !== "string" || typeof value.title !== "string")
    throw new Error("History returned an invalid record");
  const report = object(value.report);
  selected = value as Evidence;
  fill(value.input);
  text(
    "selected",
    `${value.title} | ${outcomeLabel(report.status)} | ${value.id}`,
  );
  text("evidence", encoded(value));
  const summary = element("summary", HTMLElement);
  summary.replaceChildren();
  const notice = document.createElement("p");
  notice.textContent = String(report.notice);
  summary.append(notice);
  if (report.kind === "lifecycle") {
    const final = object(report.final);
    const states = document.createElement("p");
    states.textContent = Object.entries(final)
      .map(([id, raw]) => {
        const state = object(raw);
        return `${id}: ${outcomeLabel(state.phase)}, active ${String(state.active)}, confirmed ${String(state.confirmed)}, generation ${String(state.generation)}`;
      })
      .join("; ");
    summary.append(states);
    const timeline = report.timeline as JsonObject[];
    table(
      [
        "Step",
        "Device",
        "Outcome",
        "Recovered phase",
        "Generation",
        "Selected slot",
        "Fault reached",
        "Reason",
      ],
      timeline.map((row) => {
        const after = object(row.after);
        return [
          row.step,
          row.device,
          outcomeLabel(row.status),
          outcomeLabel(after.phase),
          after.generation,
          row.selected_slot ?? "not a boot",
          row.fault_triggered,
          row.reason ?? "none",
        ];
      }),
      `${timeline.length} attempted / ${String(report.requested_steps)} requested; ${String(report.unattempted_steps)} unattempted`,
    );
  } else if (report.kind === "preflight") {
    const measured = object(report.report);
    const rows = measured.devices as JsonObject[];
    table(
      ["Device", "Eligible", "Reason", "Cohort", "Assumed health", "Rehearsal"],
      rows.map((row) => [
        row.id,
        row.eligible === true ? "Yes" : "No",
        outcomeLabel(row.reason),
        row.cohort,
        outcomeLabel(row.assumed_outcome),
        outcomeLabel(row.rehearsal),
      ]),
      `Read-only review of ${rows.length} devices; stopped after cohort ${String(measured.stopped_after_cohort ?? "none")}`,
    );
  } else {
    const measured = object(report.report);
    table(
      ["Measure", "Observed"],
      Object.entries(measured).map(([key, entry]) => [key, entry]),
      "Original interruption campaign evidence",
    );
  }
  button("export-evidence").disabled = false;
  button("export-package").disabled = report.package === undefined;
  button("delete").disabled = busy;
}

async function refresh(): Promise<void> {
  const captured = ++searchRevision;
  const query = new URLSearchParams({
    q: input("search").value,
    kind: select("history-kind").value,
    page: String(page),
  });
  const result = await api("/api/history?" + query.toString());
  if (captured !== searchRevision) return;
  total = Number(result.total);
  text(
    "history-total",
    `${total} matching saved rehearsals | page ${page + 1}`,
  );
  const list = element("history", HTMLUListElement);
  list.replaceChildren();
  for (const raw of result.items as unknown[]) {
    const record = object(raw);
    const item = document.createElement("li");
    const open = document.createElement("button");
    open.textContent = `${String(record.title)} | ${outcomeLabel(record.kind)} | ${outcomeLabel(record.status)} | ${String(record.created)}`;
    open.addEventListener("click", () => {
      const expected = ++revision;
      void api("/api/history/" + encodeURIComponent(String(record.id)))
        .then((value) => {
          if (expected === revision) {
            show(value);
            status(
              "Selected the exact saved rehearsal; complete provenance is below.",
            );
          }
        })
        .catch(failure);
    });
    item.append(open);
    list.append(item);
  }
  button("previous").disabled = page === 0;
  button("next").disabled = (page + 1) * 25 >= total;
}

function setBusy(value: boolean): void {
  busy = value;
  for (const control of document.querySelectorAll<
    | HTMLInputElement
    | HTMLSelectElement
    | HTMLTextAreaElement
    | HTMLButtonElement
  >("[data-edit]"))
    control.disabled = value;
  button("delete").disabled = value || selected === null;
}

async function run(value: JsonObject = currentInput()): Promise<void> {
  if (busy)
    throw new Error(
      "Another rehearsal is already running; this loaded input has not been run. Wait for completion, then Run.",
    );
  const captured = revision;
  setBusy(true);
  status("Running the original Rust engines in a fresh owned fictional lab…");
  try {
    const result = await api("/api/run", {
      title: input("title").value,
      input: value,
    });
    if (captured === revision) {
      show(result);
      status(
        "Saved actual rehearsal evidence. Inspect its outcome; blocked/recovered states are not successful deployments.",
      );
    } else
      status(
        "Rehearsal saved, but the edited/selected context changed. Select it explicitly in history.",
      );
    await refresh();
  } finally {
    setBusy(false);
  }
}

for (const control of document.querySelectorAll("[data-edit]"))
  control.addEventListener("input", () => {
    revision += 1;
  });
button("run").addEventListener("click", () => {
  try {
    void run().catch(failure);
  } catch (error) {
    failure(error);
  }
});
button("load-example").addEventListener("click", () => {
  fill(
    example(
      select("example").value as
        "healthy" | "rollback" | "interrupted" | "fleet",
    ),
  );
  status("Loaded an editable input. Change it before running if needed.");
});
button("append-step").addEventListener("click", () => {
  try {
    const current = steps(parse(area("steps").value));
    const kind = select("step-action").value;
    const action =
      kind === "activate"
        ? {
            kind,
            slot: select("step-slot").value,
            attempts: Number(input("step-attempts").value),
          }
        : kind === "fail"
          ? { kind, reason: input("step-reason").value }
          : { kind };
    area("steps").value = encoded(
      steps([
        ...current,
        {
          device: input("step-device").value,
          action,
          fault: select("step-fault").value || null,
        },
      ]),
    );
    revision += 1;
  } catch (error) {
    failure(error);
  }
});
button("export-input").addEventListener("click", () => {
  try {
    saveFile("firmware-rehearsal-input.json", currentInput());
    status("Exported the current editable input.");
  } catch (error) {
    failure(error);
  }
});
button("export-evidence").addEventListener("click", () => {
  if (selected) saveFile(`firmware-evidence-${selected.id}.json`, selected);
});
button("export-package").addEventListener("click", () => {
  if (selected)
    saveFile(
      `firmware-demo-package-${selected.id}.json`,
      selected.report.package,
    );
});
button("delete").addEventListener("click", () => {
  if (
    !selected ||
    busy ||
    !confirm(
      "Delete only this selected saved rehearsal? Export it first if needed.",
    )
  )
    return;
  const id = selected.id;
  void api("/api/delete", { id })
    .then(async () => {
      if (selected?.id === id) {
        selected = null;
        text(
          "selected",
          "Selected history entry deleted. Exported files were not changed.",
        );
        button("delete").disabled = true;
        button("export-evidence").disabled = true;
        button("export-package").disabled = true;
      }
      await refresh();
      status("Deleted only the explicitly selected record.");
    })
    .catch(failure);
});
for (const id of [
  "input-file",
  "evidence-file",
  "package-file",
  "image-file",
]) {
  input(id).addEventListener("change", () => {
    const file = input(id).files?.[0];
    if (!file) return;
    const captured = ++revision;
    void (async () => {
      if (id === "image-file") {
        if (file.size === 0 || file.size > 65536)
          throw new Error("An inert image uses1..65536 bytes");
        const data = await file.arrayBuffer();
        if (data.byteLength !== file.size)
          throw new Error("Image changed while reading");
        if (captured === revision)
          area("image").value = hex(new Uint8Array(data));
      } else {
        const parsed = object(
          await jsonFile(
            file,
            id === "evidence-file" ? 8 * 1024 * 1024 : 256 * 1024,
          ),
        );
        if (captured !== revision) return;
        if (id === "package-file") {
          if (
            Object.keys(parsed).sort().join(",") !== "image_hex,manifest" ||
            typeof parsed.image_hex !== "string"
          )
            throw new Error("A package contains only manifest and image_hex");
          area("manifest").value = encoded(object(parsed.manifest));
          area("image").value = parsed.image_hex;
          select("package-mode").value = "import";
        } else if (id === "evidence-file") {
          if (
            parsed.product !== "firmware-release-recovery-lab" ||
            parsed.schemaVersion !== 1
          )
            throw new Error("Choose this application's exported evidence");
          const value = request(parsed.input);
          fill(value);
          await run(value);
        } else fill(parsed);
      }
      status(
        id === "evidence-file"
          ? "Imported input was rerun with the actual engine; supplied result claims were ignored."
          : "Loaded supported local input. Review it before running.",
      );
    })()
      .catch(failure)
      .finally(() => {
        input(id).value = "";
      });
  });
}
button("refresh").addEventListener("click", () => {
  page = 0;
  void refresh().catch(failure);
});
for (const id of ["search", "history-kind"])
  inputOrSelect(id).addEventListener("input", () => {
    searchRevision += 1;
  });
function inputOrSelect(id: string): HTMLInputElement | HTMLSelectElement {
  const value = document.getElementById(id);
  if (!(
    value instanceof HTMLInputElement || value instanceof HTMLSelectElement
  ))
    throw new Error("Missing history filter");
  return value;
}
button("previous").addEventListener("click", () => {
  page = Math.max(0, page - 1);
  void refresh().catch(failure);
});
button("next").addEventListener("click", () => {
  if ((page + 1) * 25 < total) {
    page += 1;
    void refresh().catch(failure);
  }
});
button("quit").addEventListener("click", () => {
  void api("/api/quit", { quit: true })
    .then(() => {
      setBusy(true);
      button("quit").disabled = true;
      status(
        "Closing the actual owned application after pending work drains. Saved history is retained.",
      );
    })
    .catch(failure);
});
fill(example("healthy"));
if (capability)
  void api("/health")
    .then((value) => {
      text(
        "identity",
        `Version ${String(value.version)} | Rust source ${String(object(value.engine).sourceCommit)}`,
      );
      status(
        "Owned application ready. Edit a plan or import your supported file.",
      );
      return refresh();
    })
    .catch(failure);
else {
  setBusy(true);
  button("quit").disabled = true;
  status(
    "Open this actual app through its native owner window to create a private session.",
    true,
  );
}
