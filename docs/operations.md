# Operations guide

## Configuration

The CLI accepts all state through flags. There are no environment secrets or configuration
files. A simulated device root contains:

```text
device/
├── state.json
├── state.backup.json
└── slots/
    ├── A/image.bin
    └── B/{image.bin,manifest.json}
```

## Inspection

Use `fwlab status --root PATH --json` after every operation or restart. The response exposes
generation, active/confirmed/pending slots, attempt budget, verified slot records, and causal
audit events.

## Recovery

No manual repair command is provided. Loading automatically chooses the newest valid primary
or backup copy. If neither validates, stop: do not fabricate a new confirmed state. Preserve
the directory for analysis and reinitialize a different empty lab root.

## Backup and restore

For a simulator, copy the entire root only while no command is running. Restoring individual
files can combine generations that were never committed together. Real update systems require
platform-specific snapshot and recovery design.

## Troubleshooting

| Symptom | Meaning | Action |
| --- | --- | --- |
| `NoRecoverableState` | Primary and backup absent, malformed, or invariant-invalid | Verify root path; preserve evidence; initialize a new empty root |
| Signature failure | Manifest changed or wrong key | Reject package; rebuild from trusted source |
| Digest mismatch | Image bytes do not match signed metadata | Reject package; inspect transfer/build pipeline |
| Compatibility rejection | Hardware or version policy mismatch | Use the correct release; do not bypass policy |
| Existing-path refusal | Destructive overwrite was prevented | Select a new demo/package directory |

## Release and rollback

Repository releases should include the source archive, `Cargo.lock`, test/campaign evidence,
and changelog. Runtime rollback is automatic only after a candidate exhausts its persisted
attempt budget and reports failure; manual slot forcing is deliberately absent.

