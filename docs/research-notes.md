# Research notes

The implementation was checked against current primary documentation on 2026-09-17.

- Rust uses `Result<T, E>` for recoverable errors, which supports explicit propagation at I/O,
  parsing, and policy boundaries: [The Rust Programming Language — Error Handling](https://doc.rust-lang.org/stable/book/ch09-00-error-handling.html).
- Unit tests can exercise private details while integration tests exercise the public API:
  [The Rust Programming Language — Test Organization](https://doc.rust-lang.org/book/ch11-03-test-organization.html).
- `File::sync_all` is used when close-time errors must not be silently ignored:
  [Rust standard library — `File`](https://doc.rust-lang.org/std/fs/struct.File.html).
- The standard filesystem documentation warns about check-then-act races and recommends
  atomic operations where possible: [Rust standard library — `std::fs`](https://doc.rust-lang.org/std/fs/).
- GitHub recommends least-privilege workflow permissions and pinning third-party actions to a
  full commit SHA: [GitHub Docs — Protecting against security threats](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats).
- Uploaded workflow artifacts are immutable in current action versions and can carry a digest:
  [GitHub `upload-artifact` documentation](https://github.com/actions/upload-artifact).

These sources guide error handling, test separation, durable-write ordering, and CI supply
chain controls. They do not establish production firmware safety or platform durability.

