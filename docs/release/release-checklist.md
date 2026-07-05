# Release Checklist

Use this checklist for Windows release candidates.

## Channel

- Choose `dev` for internal smoke builds.
- Choose `beta` for wider validation.
- Choose `stable` only after beta validation.

## Local Verification

- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
- `cd services/agent-core && .venv/Scripts/python -I -m pytest`
- `pnpm --filter @bolt/desktop package:win:portable`

If packaging cannot reach GitHub release assets, record the failure as external network failure and retry from a network that can resolve `release-assets.githubusercontent.com`.

If Electron Builder prints packaging output and then stalls, the wrapper should fail with `Electron Builder packaging stalled` and point to the failure pattern. Do not leave a packaging job running indefinitely.

## Manual Workflow

1. Open the Release workflow.
2. Select a channel: `dev`, `beta`, or `stable`.
3. Select a package target: `none`, `dir`, `portable`, `nsis`, or `all`.
4. Confirm the workflow completed quality, desktop build, and Python tests.
5. Download the uploaded artifact.

The workflow does not create GitHub releases, push tags, or publish artifacts.

## Signing

- Unsigned builds are acceptable for `dev` and early `beta`.
- Signed builds require `CSC_LINK` and `CSC_KEY_PASSWORD` as environment variables or GitHub Secrets.
- Never commit `.pfx`, `.p12`, `.pem`, `.key`, passwords, or certificate URLs.

## Auto Update

Auto-update remains disabled. Do not enable update checks until signing and release channel policy are complete.
