from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class TrustError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrustedSigner:
    signer_id: str
    roles: set[str]
    public_key: bytes
    fingerprint: str
    status: str


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def key_fingerprint(public_key: bytes) -> str:
    return "sha256:" + sha256_hex(public_key)


def b64decode_field(value: str, label: str) -> bytes:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:
        raise TrustError(f"{label} is not valid base64") from exc


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_trust_policy(path: Path) -> dict[str, Any]:
    policy = load_json(path)
    if policy.get("version") != 1:
        raise TrustError("unsupported trust policy version")
    return policy


def trusted_signers(policy: dict[str, Any]) -> dict[str, TrustedSigner]:
    signers: dict[str, TrustedSigner] = {}
    for item in policy.get("signers", []):
        signer_id = item.get("id")
        if not signer_id:
            raise TrustError("signer without id in trust policy")
        public_key = b64decode_field(item.get("public_key", ""), f"public key for {signer_id}")
        expected = item.get("fingerprint")
        actual = key_fingerprint(public_key)
        if expected != actual:
            raise TrustError(f"fingerprint mismatch for signer {signer_id}: expected {expected}, got {actual}")
        signers[signer_id] = TrustedSigner(
            signer_id=signer_id,
            roles=set(item.get("roles", [])),
            public_key=public_key,
            fingerprint=actual,
            status=item.get("status", "active"),
        )
    return signers


def verify_signature(
    policy: dict[str, Any],
    signer_id: str,
    signature_b64: str,
    payload: bytes,
    purpose: str,
    *,
    at_time: datetime | None = None,
) -> None:
    signers = trusted_signers(policy)
    signer = signers.get(signer_id)
    if signer is None:
        raise TrustError(f"unknown signer: {signer_id}")
    if signer.status != "active":
        raise TrustError(f"signer {signer_id} is not active")
    if purpose not in signer.roles and "root" not in signer.roles:
        raise TrustError(f"signer {signer_id} is not allowed for {purpose}")

    for revoked in policy.get("revoked_signers", []):
        if revoked.get("id") == signer_id:
            raise TrustError(f"signer {signer_id} is revoked")

    expires_at = parse_time(next((s.get("expires_at") for s in policy.get("signers", []) if s.get("id") == signer_id), None))
    if expires_at and (at_time or utc_now()) > expires_at:
        raise TrustError(f"signer {signer_id} is expired")

    public_key = Ed25519PublicKey.from_public_bytes(signer.public_key)
    signature = b64decode_field(signature_b64, "signature")
    try:
        public_key.verify(signature, payload)
    except InvalidSignature as exc:
        raise TrustError(f"invalid signature from {signer_id}") from exc
