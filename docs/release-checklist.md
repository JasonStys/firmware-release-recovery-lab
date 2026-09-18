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

