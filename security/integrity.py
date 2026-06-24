from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .trust import TrustError, canonical_json_bytes, load_json, load_trust_policy, verify_signature

DEFAULT_TRUST_POLICY = Path("security/trust-policy.json")
DEFAULT_MANIFEST = Path("security/integrity-manifest.json")


class IntegrityError(RuntimeError):
    pass


@dataclass
class IntegrityReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    verified_files: int = 0
    signer_id: str | None = None

    def raise_for_errors(self) -> None:
        if not self.ok:
            raise IntegrityError("; ".join(self.errors))


def repo_path(root: Path, path: str) -> Path:
    if path.startswith("/") or ".." in Path(path).parts:
        raise IntegrityError(f"unsafe manifest path: {path}")
    return root / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("signatures", None)
    return payload


def signature_payload_bytes(manifest: dict[str, Any]) -> bytes:
    return canonical_json_bytes(manifest_payload(manifest))


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    if manifest.get("schema") != "holo-rick.integrity-manifest.v1":
        raise IntegrityError("unsupported integrity manifest schema")
    return manifest


def iter_policy_files(root: Path, policy: dict[str, Any]) -> list[str]:
    files: set[str] = set(policy.get("manifest", {}).get("include_files", []))
    for pattern in policy.get("manifest", {}).get("include_globs", []):
        for path in root.glob(pattern):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                if not any(fnmatch.fnmatch(rel, ignored) for ignored in policy.get("manifest", {}).get("exclude_globs", [])):
                    files.add(rel)
    return sorted(files)


def build_manifest_payload(root: Path, policy: dict[str, Any], version: str) -> dict[str, Any]:
    files = []
    for rel in iter_policy_files(root, policy):
        path = repo_path(root, rel)
        if not path.exists():
            raise IntegrityError(f"manifest input missing: {rel}")
        files.append(
            {
                "path": rel,
                "sha256": sha256_file(path),
                "critical": rel in set(policy.get("required_files", [])) or rel.startswith(("security/", "scripts/security/", ".github/")),
            }
        )
    return {
        "schema": "holo-rick.integrity-manifest.v1",
        "project": "Holo Rick",
        "version": version,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "hash_algorithm": "sha256",
        "signature_algorithm": "ed25519",
        "files": files,
    }


def sign_manifest_payload(payload: dict[str, Any], private_key_path: Path, signer_id: str) -> dict[str, Any]:
    key_data = private_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(key_data, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise IntegrityError("manifest signing key must be an Ed25519 private key")
    signature = private_key.sign(canonical_json_bytes(payload))
    manifest = dict(payload)
    manifest["signatures"] = [
        {
            "signer_id": signer_id,
            "purpose": "integrity_manifest",
            "algorithm": "ed25519",
            "signature": base64.b64encode(signature).decode("ascii"),
        }
    ]
    return manifest


def verify_integrity(
    root: Path,
    *,
    trust_policy_path: Path | None = None,
    manifest_path: Path | None = None,
    mode: str = "block",
    log: bool = True,
) -> IntegrityReport:
    root = root.resolve()
    trust_path = root / (trust_policy_path or DEFAULT_TRUST_POLICY)
    manifest_file = root / (manifest_path or DEFAULT_MANIFEST)
    errors: list[str] = []
    warnings: list[str] = []
    signer_id: str | None = None
    verified_files = 0

    try:
        if not trust_path.exists():
            raise IntegrityError(f"missing trust policy: {trust_path.relative_to(root)}")
        if not manifest_file.exists():
            raise IntegrityError(f"missing integrity manifest: {manifest_file.relative_to(root)}")
        policy = load_trust_policy(trust_path)
        manifest = load_manifest(manifest_file)

        for required in policy.get("required_files", []):
            if not repo_path(root, required).exists():
                errors.append(f"required security file missing: {required}")

        signatures = manifest.get("signatures") or []
        if not signatures:
            errors.append("integrity manifest has no signatures")
        else:
            sig_errors = []
            payload = signature_payload_bytes(manifest)
            for signature in signatures:
                try:
                    signer_id = signature.get("signer_id")
                    verify_signature(
                        policy,
                        signer_id=signer_id,
                        signature_b64=signature.get("signature", ""),
                        payload=payload,
                        purpose=signature.get("purpose", "integrity_manifest"),
                    )
                    sig_errors = []
                    break
                except TrustError as exc:
                    sig_errors.append(str(exc))
            errors.extend(sig_errors)

        manifest_paths = {item.get("path") for item in manifest.get("files", [])}
        for required in policy.get("required_files", []):
            if required != DEFAULT_MANIFEST.as_posix() and required not in manifest_paths:
                errors.append(f"required security file not covered by manifest: {required}")

        for item in manifest.get("files", []):
            rel = item.get("path")
            expected = item.get("sha256")
            if not rel or not expected:
                errors.append("manifest file entry missing path or hash")
                continue
            path = repo_path(root, rel)
            if not path.exists():
                errors.append(f"manifest file missing: {rel}")
                continue
            actual = sha256_file(path)
            if actual != expected:
                errors.append(f"hash mismatch: {rel}")
            verified_files += 1
    except Exception as exc:
        errors.append(str(exc))

    report = IntegrityReport(ok=not errors, errors=errors, warnings=warnings, verified_files=verified_files, signer_id=signer_id)
    if log:
        write_security_log(root, report)
    if errors and mode == "block":
        report.raise_for_errors()
    return report


def write_security_log(root: Path, report: IntegrityReport) -> None:
    try:
        log_dir = root / "logs"
        log_dir.mkdir(exist_ok=True)
        line = json.dumps(
            {
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "event": "integrity_check",
                "ok": report.ok,
                "verified_files": report.verified_files,
                "signer_id": report.signer_id,
                "errors": report.errors,
                "warnings": report.warnings,
            },
            ensure_ascii=False,
        )
        with (log_dir / "security-integrity.log").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def run_startup_integrity_check(root: Path) -> IntegrityReport | None:
    mode = os.environ.get("HOLO_RICK_INTEGRITY_MODE", "warn").strip().lower()
    if mode in {"off", "disabled", "0", "false"}:
        return None
    effective = "block" if mode in {"block", "strict", "enforce"} else "warn"
    report = verify_integrity(root, mode=effective)
    if not report.ok and effective == "warn":
        print("SECURITY WARNING: Holo Rick integrity check failed:", "; ".join(report.errors), file=sys.stderr)
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify or generate Holo Rick integrity manifests.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--root", default=".")
    check.add_argument("--mode", choices=["block", "warn"], default="block")
    check.add_argument("--json", action="store_true")

    create = sub.add_parser("create")
    create.add_argument("--root", default=".")
    create.add_argument("--trust-policy", default=DEFAULT_TRUST_POLICY.as_posix())
    create.add_argument("--out", default=DEFAULT_MANIFEST.as_posix())
    create.add_argument("--private-key", required=True)
    create.add_argument("--signer-id", required=True)
    create.add_argument("--version", default="1")

    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve()
    if args.command == "check":
        report = verify_integrity(root, mode=args.mode)
        if args.json:
            print(json.dumps(report.__dict__, indent=2, ensure_ascii=False))
        else:
            print(f"Integrity OK: {report.verified_files} files verified by {report.signer_id}")
        return 0 if report.ok else 1

    policy = load_trust_policy(root / args.trust_policy)
    payload = build_manifest_payload(root, policy, args.version)
    manifest = sign_manifest_payload(payload, Path(args.private_key), args.signer_id)
    out = root / args.out
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
