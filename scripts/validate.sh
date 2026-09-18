#!/usr/bin/env bash
# File: validate.sh
# Purpose: Runs the same formatting, lint, test, documentation, and campaign gates as CI.
# Variables: ROOT_DIR is the repository root; CARGO_TERM_COLOR keeps logs readable.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CARGO_TERM_COLOR=always
cd "$ROOT_DIR"

cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-targets --all-features --locked
cargo doc --no-deps --document-private-items --locked
cargo run --release --locked -- fault-campaign --iterations 100 --output artifacts/fault-campaign.json
python scripts/generate_code_index.py
python scripts/verify_repo.py
