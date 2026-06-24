# Release Signing

## Generate Keys

Generate Ed25519 keys outside the repository:

```bash
python - <<'PY'
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
key = Ed25519PrivateKey.generate()
print(key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode())
PY
```

Store private keys in a password manager, hardware token, or protected CI secret.
Commit only public keys and fingerprints in `security/trust-policy.json`.

## Regenerate Integrity Manifest

```bash
python scripts/security/generate-integrity-manifest.py \
  --private-key /secure/path/manifest-signing-key.pem \
  --signer-id pondsec-root-2026-06-bootstrap \
  --version "$(git rev-parse --short HEAD)"
```

Then verify:

```bash
python scripts/security/check-integrity.py --mode block
```

## Signed Tags

Official releases should use signed Git tags:

```bash
git tag -s v1.2.3 -m "Holo Rick v1.2.3"
git push origin v1.2.3
```

Only artifacts built from signed tags and passing the integrity workflow should
be described as official PondSec releases.

## Rotation and Revocation

To rotate a key:

1. add the new public key and fingerprint to `security/trust-policy.json`;
2. sign and commit a new manifest;
3. publish the change through protected CI;
4. move the old signer to `revoked_signers` or set `status` to `retired`;
5. create a signed release after verification passes.

