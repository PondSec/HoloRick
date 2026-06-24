# Threat Model

## Public Copy Removes Checks

- Risk: anyone can copy public code and delete the protection system locally.
- Technical countermeasure: official releases require signed manifests, CI, and
  release checks.
- Residual risk: local unofficial copies cannot be technically prevented.
- Organizational measure: license enforcement and clear official-release
  provenance.

## Security Files Modified

- Risk: attacker edits CI, trust policy, license, scripts, or entry points.
- Technical countermeasure: those files are required and covered by the signed
  integrity manifest.
- Residual risk: attacker with signing key can authorize malicious changes.
- Organizational measure: protect private keys, require CODEOWNERS review.

## CI Modified

- Risk: attacker weakens CI so bad changes pass.
- Technical countermeasure: `.github/**` is protected by manifest and CODEOWNERS.
- Residual risk: admins can still change repository settings.
- Organizational measure: protected branch rules and audit logs.

## Build Output Modified

- Risk: artifact is altered after source verification.
- Technical countermeasure: build only from verified signed source; sign release
  artifacts.
- Residual risk: compromised build runner can alter output.
- Organizational measure: trusted runners, reproducible build review where
  practical.

## Fake Official Release

- Risk: attacker publishes a fork or artifact as official.
- Technical countermeasure: official builds are tied to PondSec signatures.
- Residual risk: users may trust the wrong source.
- Organizational measure: publish fingerprints and official URLs.

## Replay of Old Valid State

- Risk: attacker rolls back to an old signed vulnerable version.
- Technical countermeasure: key revocation, release policy, branch protection.
- Residual risk: old artifacts can be mirrored.
- Organizational measure: publish deprecation notices and rotate keys.

## Private Key Compromise

- Risk: attacker signs malicious manifests/releases.
- Technical countermeasure: revocation list and signer rotation.
- Residual risk: malicious signed releases before revocation may exist.
- Organizational measure: hardware-backed keys, least privilege, incident
  response.

