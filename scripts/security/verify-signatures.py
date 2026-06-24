#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from security.integrity import verify_integrity


def main() -> int:
    report = verify_integrity(ROOT, mode="block")
    head = subprocess.run(["git", "log", "-1", "--format=%G?"], cwd=ROOT, text=True, capture_output=True)
    status = head.stdout.strip()
    if status not in {"G", "U", "N", ""}:
        raise SystemExit(f"unexpected git signature status: {status}")
    print(f"Signature checks OK: manifest signed by {report.signer_id}; git HEAD status {status or 'unknown'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
