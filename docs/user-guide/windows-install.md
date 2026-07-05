# Windows Install

Bolt Windows artifacts are produced by the manual Release workflow or by local packaging commands.

## Artifact Types

- Portable: a single executable for smoke testing and lightweight distribution.
- NSIS installer: an install wizard that can choose the installation directory.
- Win unpacked directory: a packaging dry-run useful for release checks.

## Install

1. Download the release artifact from the manually triggered Release workflow.
2. Extract the artifact if GitHub Actions packaged it as a zip.
3. Run the portable executable or the NSIS installer.
4. Open Bolt and choose a workspace.

The desktop app starts Agent Core automatically. Packaged builds look for Agent Core resources under Electron's `resources/agent-core` directory. If the runtime cannot find those resources, Bolt reports a startup failure instead of silently continuing.

## Trust and Signing

Unsigned builds are allowed for development and beta validation. Windows may show SmartScreen warnings for unsigned artifacts.

Signed builds require certificate material supplied outside the repository through `CSC_LINK` and `CSC_KEY_PASSWORD`. Do not store certificates or passwords in the repo.

## Network Requirements

Packaging may need access to GitHub release asset hosts used by Electron Builder. If packaging fails with `release-assets.githubusercontent.com`, see `docs/failure-patterns/electron-builder-package-win-network-failure.md`.

`package:win:dir` also runs a packaged runtime smoke check after Electron Builder completes. That check verifies the packaged `resources/agent-core` layout before the artifact is considered usable.

## Auto Update

Auto-update is disabled by policy. Install newer builds manually until signing and release channels are fully established.
