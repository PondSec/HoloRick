#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from security.agent_policy import main


if __name__ == "__main__":
    raise SystemExit(main(["--root", str(ROOT), *sys.argv[1:]]))
