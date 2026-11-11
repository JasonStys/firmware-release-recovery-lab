"""File: Explicitly exercise the source application with the same actual GUI/domain oracles.

This is a source-only harness, never a native packaging fallback or installer claim.
The native consumer separately requires RELEASE.json/notices and executes only its binary.
Locations and arguments: docs/code-index.md.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from smoke_app import ROOT, close_owned, launch_command, require


def main():
    """Run one fresh synthetic source owner; preserve normal exit and real browser evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    require(not output.exists(), "Choose a new source acceptance folder")
    output.mkdir(parents=True)
    workspace = tempfile.TemporaryDirectory(prefix="firmware-source-workspace-", delete=False)
    with workspace as directory:
        profile = Path(directory).resolve(strict=True) / "workspace"
        process, ready, token = launch_command([sys.executable, str(ROOT / "launcher.py")], profile)
        try:
            require(
                ready["engine"]["sourceCommit"] == "development",
                "Source fixture is not a development build",
            )
            subprocess.run(
                [
                    "node",
                    str(ROOT / "tools/native_feature_smoke.mjs"),
                    ready["url"] + "/#native=" + token,
                    str(output),
                    "development",
                ],
                cwd=directory,
                check=True,
                timeout=90,
            )
            require(process.wait(timeout=20) == 0, "Actual source owner did not exit normally")
            (output / "source-acceptance.json").write_text(
                json.dumps(
                    {
                        "passed": True,
                        "mode": "explicit source-only application harness",
                        "normalExit": 0,
                        "version": "0.2.0",
                        "browser": "actual Chromium",
                        "limits": "No compiled package, installer or release acceptance is claimed",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        finally:
            close_owned(process, ready, token)
            process.stdout.close()
            process.stderr.close()
            if process.poll() is not None:
                workspace.cleanup()


if __name__ == "__main__":
    main()
