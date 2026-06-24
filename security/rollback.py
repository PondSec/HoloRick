from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class RollbackError(RuntimeError):
    pass


@dataclass(frozen=True)
class RollbackPlan:
    target_ref: str
    backup_ref: str
    backup_bundle: Path
    dry_run: bool


def run_git(root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=check)


def latest_verified_tag(root: Path) -> str:
    tags = run_git(root, ["tag", "--sort=-creatordate"]).stdout.splitlines()
    for tag in tags:
        if run_git(root, ["tag", "-v", tag], check=False).returncode == 0:
            return tag
    raise RollbackError("no verified signed tag found")


def create_backup_bundle(root: Path) -> Path:
    backup_dir = root / "logs" / "security-rollbacks"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle = backup_dir / f"pre-rollback-{stamp}.bundle"
    run_git(root, ["bundle", "create", str(bundle), "--all"])
    return bundle


def build_plan(root: Path, target_ref: str | None = None, dry_run: bool = True) -> RollbackPlan:
    current = run_git(root, ["rev-parse", "HEAD"]).stdout.strip()
    target = target_ref or latest_verified_tag(root)
    bundle = create_backup_bundle(root)
    return RollbackPlan(target_ref=target, backup_ref=current, backup_bundle=bundle, dry_run=dry_run)


def execute_plan(root: Path, plan: RollbackPlan) -> None:
    record = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "target_ref": plan.target_ref,
        "backup_ref": plan.backup_ref,
        "backup_bundle": str(plan.backup_bundle),
        "dry_run": plan.dry_run,
    }
    log_path = root / "logs" / "security-rollback-report.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    if plan.dry_run:
        return
    if os.environ.get("HOLO_RICK_ALLOW_ROLLBACK") != "1":
        raise RollbackError("refusing rollback without HOLO_RICK_ALLOW_ROLLBACK=1")
    run_git(root, ["reset", "--hard", plan.target_ref])


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rollback Holo Rick to a trusted signed ref.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--target-ref")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve()
    plan = build_plan(root, args.target_ref, dry_run=not args.execute)
    execute_plan(root, plan)
    print(json.dumps(plan.__dict__ | {"backup_bundle": str(plan.backup_bundle)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
