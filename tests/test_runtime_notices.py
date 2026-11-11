"""File: Jason Stys: mandatory isolated actual Tcl notice contracts with exact-case
receipt. Lines: docs/code-index.md.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from defusedxml import ElementTree as ET


def test_all_thirteen_actual_notice_contracts_in_one_fresh_owned_interpreter():
    """No retries/skips: preserve every real case, propagate failures and retain its
    source-bound JUnit identity.
    """
    root = Path(__file__).resolve().parents[1]
    cases = root / "tests/runtime_notice_cases.py"
    with tempfile.TemporaryDirectory(prefix="notice-contract-results-") as temporary:
        result_path = Path(temporary) / "results.xml"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(cases),
                "--capture=sys",
                "-q",
                "--junitxml=" + str(result_path),
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        records = list(ET.parse(result_path).getroot().iter("testcase"))
        assert len(records) == 13
        assert len({item.attrib["name"] for item in records}) == 13
        assert not any(list(item) for item in records), result.stdout + result.stderr
        receipt = {
            "passed": True,
            "actual_cases": [item.attrib["name"] for item in records],
            "case_count": len(records),
            "interpreter": sys.version.split()[0],
            "capture": "sys; stable native descriptors",
            "retries": 0,
            "skipped": 0,
            "case_source_sha256": hashlib.sha256(cases.read_bytes()).hexdigest(),
            "reader_source_sha256": hashlib.sha256(
                (root / "tools/runtime_notices.py").read_bytes()
            ).hexdigest(),
        }
        target = root / ".runtime/notices-contract.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print("All13 actual isolated Tcl/Tk notice cases passed; no retries or skips.")
