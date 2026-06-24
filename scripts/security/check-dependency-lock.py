#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    requirements = ROOT / "requirements.txt"
    lock = ROOT / "requirements.lock"
    if not requirements.exists():
        raise SystemExit("requirements.txt missing")
    if not lock.exists():
        raise SystemExit("requirements.lock missing")
    locked = lock.read_text(encoding="utf-8")
    required_names = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = stripped.split("[", 1)[0].split(">", 1)[0].split("=", 1)[0].split("<", 1)[0].lower()
        required_names.append(name)
    missing = [name for name in required_names if f"{name}==" not in locked.lower()]
    if missing:
        raise SystemExit(f"requirements.lock is missing pinned packages: {', '.join(missing)}")
    print("Dependency lock check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
