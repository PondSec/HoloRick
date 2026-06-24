from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .trust import TrustError, canonical_json_bytes, load_json, load_trust_policy, parse_time, verify_signature


class AgentPolicyError(RuntimeError):
    pass


def is_security_path(path: str, policy: dict[str, Any]) -> bool:
    protected = policy.get("critical_globs", [])
    from fnmatch import fnmatch

    return any(fnmatch(path, pattern) for pattern in protected)


def load_agent_token(path: Path) -> dict[str, Any]:
    token = load_json(path)
    if "payload" not in token or "signature" not in token or "signer_id" not in token:
        raise AgentPolicyError("agent token must contain payload, signature and signer_id")
    return token


def verify_agent_token(root: Path, token: dict[str, Any]) -> dict[str, Any]:
    trust = load_trust_policy(root / "security/trust-policy.json")
    payload = token["payload"]
    verify_signature(
        trust,
        signer_id=token["signer_id"],
        signature_b64=token["signature"],
        payload=canonical_json_bytes(payload),
        purpose="agent_policy",
    )
    expires_at = parse_time(payload.get("expires_at"))
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise AgentPolicyError("agent token expired")
    return payload


def authorize_agent_action(
    root: Path,
    action: str,
    paths: list[str] | None = None,
    token_path: Path | None = None,
) -> bool:
    policy = load_json(root / "security/agent-policy.json")
    paths = paths or []
    if action == "allow_read":
        return bool(policy.get("default_permissions", {}).get("allow_read", True))
    if not token_path:
        raise AgentPolicyError(f"{action} requires a signed agent token")
    token_payload = verify_agent_token(root, load_agent_token(token_path))
    if action not in token_payload.get("permissions", []):
        raise AgentPolicyError(f"token does not grant {action}")
    if any(is_security_path(path, policy) for path in paths) and "allow_modify_security_files" not in token_payload.get("permissions", []):
        raise AgentPolicyError("security file modification requires allow_modify_security_files")
    return True


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify signed Holo Rick agent permissions.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--action", required=True)
    parser.add_argument("--token")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(list(argv) if argv is not None else None)
    authorize_agent_action(Path(args.root).resolve(), args.action, args.paths, Path(args.token) if args.token else None)
    print(f"Agent action authorized: {args.action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
