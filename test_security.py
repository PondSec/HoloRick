import base64
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from security.agent_policy import AgentPolicyError, authorize_agent_action
from security.integrity import IntegrityError, build_manifest_payload, sign_manifest_payload, verify_integrity
from security.rollback import build_plan, execute_plan
from security.trust import canonical_json_bytes, key_fingerprint


def make_key(tmp_path: Path):
    key = Ed25519PrivateKey.generate()
    private_path = tmp_path / "key.pem"
    private_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return key, private_path, base64.b64encode(public).decode("ascii"), key_fingerprint(public)


def write_minimal_repo(tmp_path: Path):
    key, private_path, public_key, fingerprint = make_key(tmp_path)
    (tmp_path / "security").mkdir()
    (tmp_path / "scripts/security").mkdir(parents=True)
    (tmp_path / "LICENSE").write_text("license\n", encoding="utf-8")
    (tmp_path / "security/__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "security/integrity.py").write_text("guard\n", encoding="utf-8")
    (tmp_path / "scripts/security/check-integrity.py").write_text("guard\n", encoding="utf-8")
    policy = {
        "version": 1,
        "signers": [
            {
                "id": "test-root",
                "roles": ["root", "integrity_manifest", "agent_policy"],
                "algorithm": "ed25519",
                "public_key": public_key,
                "fingerprint": fingerprint,
                "status": "active",
            }
        ],
        "revoked_signers": [],
        "required_files": [
            "LICENSE",
            "security/__init__.py",
            "security/integrity.py",
            "scripts/security/check-integrity.py",
        ],
        "manifest": {
            "include_files": [
                "LICENSE",
                "security/__init__.py",
                "security/integrity.py",
                "scripts/security/check-integrity.py",
            ],
            "include_globs": [],
            "exclude_globs": [],
        },
    }
    (tmp_path / "security/trust-policy.json").write_text(json.dumps(policy), encoding="utf-8")
    payload = build_manifest_payload(tmp_path, policy, "test")
    manifest = sign_manifest_payload(payload, private_path, "test-root")
    (tmp_path / "security/integrity-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return key, private_path, policy, manifest


def test_valid_manifest_verifies(tmp_path):
    write_minimal_repo(tmp_path)
    report = verify_integrity(tmp_path, mode="block", log=False)
    assert report.ok
    assert report.verified_files == 4


def test_tampered_file_fails_integrity(tmp_path):
    write_minimal_repo(tmp_path)
    (tmp_path / "LICENSE").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(IntegrityError):
        verify_integrity(tmp_path, mode="block", log=False)


def test_missing_security_module_fails_integrity(tmp_path):
    write_minimal_repo(tmp_path)
    (tmp_path / "security/integrity.py").unlink()
    with pytest.raises(IntegrityError):
        verify_integrity(tmp_path, mode="block", log=False)


def test_invalid_manifest_signature_fails(tmp_path):
    write_minimal_repo(tmp_path)
    manifest_path = tmp_path / "security/integrity-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["signatures"][0]["signature"] = base64.b64encode(b"bad").decode("ascii")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IntegrityError):
        verify_integrity(tmp_path, mode="block", log=False)


def test_unknown_signer_fails(tmp_path):
    write_minimal_repo(tmp_path)
    manifest_path = tmp_path / "security/integrity-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["signatures"][0]["signer_id"] = "unknown"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IntegrityError):
        verify_integrity(tmp_path, mode="block", log=False)


def test_agent_without_write_token_is_read_only(tmp_path):
    write_minimal_repo(tmp_path)
    (tmp_path / "security/agent-policy.json").write_text(
        json.dumps(
            {
                "version": 1,
                "default_permissions": {"allow_read": True, "allow_write": False},
                "critical_globs": ["security/**"],
            }
        ),
        encoding="utf-8",
    )
    assert authorize_agent_action(tmp_path, "allow_read")
    with pytest.raises(AgentPolicyError):
        authorize_agent_action(tmp_path, "allow_write", ["app.py"])


def test_agent_with_valid_signature_can_write_non_security_file(tmp_path):
    key, _, _, _ = write_minimal_repo(tmp_path)
    (tmp_path / "security/agent-policy.json").write_text(
        json.dumps(
            {
                "version": 1,
                "default_permissions": {"allow_read": True, "allow_write": False},
                "critical_globs": ["security/**"],
            }
        ),
        encoding="utf-8",
    )
    payload = {
        "permissions": ["allow_write"],
        "paths": ["app.py"],
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "reason": "test",
    }
    token = {
        "signer_id": "test-root",
        "payload": payload,
        "signature": base64.b64encode(key.sign(canonical_json_bytes(payload))).decode("ascii"),
    }
    token_path = tmp_path / "agent-token.json"
    token_path.write_text(json.dumps(token), encoding="utf-8")
    assert authorize_agent_action(tmp_path, "allow_write", ["app.py"], token_path)


def test_rollback_simulation_creates_backup_bundle(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "file.txt").write_text("ok\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True)
    plan = build_plan(tmp_path, target_ref="HEAD", dry_run=True)
    execute_plan(tmp_path, plan)
    assert plan.backup_bundle.exists()
    assert (tmp_path / "logs/security-rollback-report.jsonl").exists()
