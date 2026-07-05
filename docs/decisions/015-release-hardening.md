# 015 Release Hardening

## Context

M12 made Windows packaging possible, but packaging can fail when Electron Builder needs external GitHub release assets. Bolt needs a release path that separates build validation, packaging attempts, signing policy, and artifact upload without enabling automatic publishing.

## Decision

M15 hardens the Windows release path:

- Desktop packaging scripts are split by target and always pass `--publish never`.
- Release packaging runs a network preflight for `release-assets.githubusercontent.com`.
- Electron Builder is launched through a local wrapper with no-output and total timeouts.
- The Release workflow is manual-only through `workflow_dispatch`.
- Release channels are `dev`, `beta`, and `stable`.
- Unsigned builds are supported; signed builds read `CSC_LINK` and `CSC_KEY_PASSWORD` from environment or GitHub Secrets.
- Auto-update stays disabled until signing and channel policy are ready.

## Consequences

Developers can distinguish application build failures from external packaging network failures. CI can produce artifacts manually without publishing releases or storing secrets in the repository. Packaging stalls now terminate with a documented error instead of hanging indefinitely.

Future auto-update work must add an explicit opt-in gate and must not run by default.
