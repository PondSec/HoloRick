#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from security.integrity import main


if __name__ == "__main__":
    raise SystemExit(main(["check", "--root", str(ROOT), *sys.argv[1:]]))
