# Holo Rick Security Policy

## Integrity Modes

- Local development defaults to `HOLO_RICK_INTEGRITY_MODE=warn`.
- Official build, deployment, and release contexts must set
  `HOLO_RICK_INTEGRITY_MODE=block`.
- A failed block-mode check aborts startup/build and writes
  `logs/security-integrity.log`.

## Required CI Secrets

Private keys must never be committed. Store signing material only in trusted
secret stores:

- `HOLO_RICK_MANIFEST_SIGNING_KEY`: Ed25519 private key PEM for updating
  `security/integrity-manifest.json`.
- `HOLO_RICK_RELEASE_SIGNING_KEY`: release signing key, preferably hardware or
  CI-protected.
- `HOLO_RICK_AGENT_SIGNING_KEY`: optional key for signed agent change tokens.

## Required Repository Settings

Enable these settings manually on GitHub:

- protect `main`;
- require pull requests before merge;
- require CODEOWNERS review;
- require status checks from `.github/workflows/security-integrity.yml`;
- require signed commits and signed tags where practical;
- disallow force pushes to protected branches;
- restrict release publishing to trusted maintainers/CI;
- keep secrets available only to trusted workflows and protected branches.

## Official Release Checklist

1. Rotate or confirm active signer status in `security/trust-policy.json`.
2. Regenerate `security/integrity-manifest.json` with the release signing key.
3. Run `python scripts/security/check-integrity.py --mode block`.
4. Run `python scripts/security/verify-signatures.py`.
5. Run the full test suite.
6. Create a signed Git tag.
7. Build release artifacts only from that signed tag.

Set `HOLO_RICK_REQUIRE_SIGNED_COMMITS=1` in release-only workflows if unsigned
or unverifiable Git commits must fail CI. The default CI keeps commit signature
status informational because GitHub merge refs can report `E` when local trust
material is unavailable.

## Reporting Vulnerabilities

Report security issues privately to PondSec before public disclosure.
