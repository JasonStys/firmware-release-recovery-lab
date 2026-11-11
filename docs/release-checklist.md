# Release checklist

- [ ] All changes are represented in `CHANGELOG.md`.
- [ ] `cargo fmt --all -- --check` passes.
- [ ] Clippy passes with warnings denied.
- [ ] Unit, integration, property, and fault tests pass with `--locked`.
- [ ] Rustdoc builds without dependency docs.
- [ ] RustSec reports no applicable unmitigated advisory.
- [ ] The 1,200-scenario campaign preserves every safety invariant.
- [ ] Demo key warnings and safe-use boundaries remain prominent.
- [ ] Generated code index is current.
- [ ] Source archive includes `Cargo.lock`, docs, and validation evidence.
- [ ] Tag and release notes match the intended semantic version.
- [ ] Exact Cargo/Python/npm/UI product versions agree; the patched final Python runtime is verified.
- [ ] Whole application coverage meets90% with real owner/Tk/HTTP tests, plus the 13 isolated notice cases.
- [ ] TypeScript unit/build/asset/advisory and actual browser editable-file/review/export workflows pass.
- [ ] Three-OS packages safely extract and pass actual compiled executable journeys and normal restart.
- [ ] Rust standard-library copyright/license files and native-target Cargo.lock-bound crate terms
      match independently source-collected manifests after extraction; actual runtime notices are present.
- [ ] Exact-main required workflows and processed Rust/Python/JavaScript-TypeScript/Actions CodeQL
      analyses are inspected separately from PR and local results; unavailable analysis is not a pass.
- [ ] Existing released assets, user workspaces and historical evidence are preserved. No default CI
      binary upload or automatic publication is added by this application candidate.

