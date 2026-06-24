# Security Architecture

Holo Rick is source-available: the public can inspect the code, but official
changes, builds, and releases must be cryptographically authorized.

## What This Protects

- official build inputs;
- release and deployment pipelines;
- license, notice, CI, security, build, deployment, and entry point files;
- local developer workflows through hooks;
- runtime startup in strict deployment mode;
- agent-assisted code changes through signed permission tokens.

## What It Cannot Protect

Public code can be copied locally and modified. No repository-level mechanism
can make local removal of checks impossible. The goal is to make official
releases verifiable, block unsigned changes in trusted pipelines, detect
tampering, and restore controlled deployments to a known-good signed state.

## Trust Model

`security/trust-policy.json` lists Ed25519 public keys and allowed roles:

- `root`: can update trust policy and sign emergency rotations;
- `integrity_manifest`: can sign `security/integrity-manifest.json`;
- `release`: can sign release artifacts/tags;
- `agent_policy`: can sign agent write tokens.

Private keys must remain outside the repository.

## Integrity Manifest

`security/integrity-manifest.json` contains hashes of critical repository files
and an Ed25519 signature over the canonical manifest payload. The signature
covers metadata and file hashes. The manifest is not self-hashed; instead, the
signature and required-file policy protect the manifest itself.

## Checkpoints

- Git hooks: `security/hooks/pre-commit`, `security/hooks/pre-push`.
- CI: `.github/workflows/security-integrity.yml`.
- Build/release: `scripts/security/check-integrity.py --mode block`.
- Runtime: `HOLO_RICK_INTEGRITY_MODE=block` blocks startup on tampering.
- Rollback: `scripts/security/rollback-to-trusted.py`.

## Runtime Behavior

Local development defaults to warn mode. Official deployment must set:

```bash
HOLO_RICK_INTEGRITY_MODE=block
```

If verification fails in block mode, app startup aborts and a security log is
written.

