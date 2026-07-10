# Clean Windows E2E Runbook

## Purpose

Prove that a packaged Bolt build runs on a Windows machine without Node, Python, uv, project source, developer env vars, or old Bolt configuration.

## Preconditions

1. Use Windows Sandbox, a clean VM, or a newly created standard (non-admin) Windows user.
2. Transfer only the release artifact (portable exe or NSIS installer) and its SHA-256.
3. Confirm the machine has no:
   - Node.js
   - Python
   - uv
   - Bolt source checkout
   - `CSC_*` or developer Bolt env vars
   - previous Bolt install / `%APPDATA%\Bolt`
4. Do not paste real API keys into evidence files. Enter keys only inside the app UI.

## One-command helper (on a prepared package host)

From the repo machine that already built `win-unpacked` / installer:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/clean-windows-e2e.ps1 -ArtifactPath apps/desktop/release/win-unpacked/Bolt.exe -EvidenceDir release-evidence/clean-windows
```

The script:

- records whether the current machine is clean or polluted;
- if polluted, writes `clean_windows_e2e_blocked` and exits 2;
- if clean enough for packaged launch smoke, starts `Bolt.exe` briefly, then requests process exit evidence;
- never uploads packages or creates public releases.

## Manual clean-machine steps

1. Verify SHA-256 of the installer/portable file.
2. Install (NSIS) or run portable under a standard user.
3. Confirm first launch starts Agent Core and shows local/offline status without Core URL inputs.
4. Select/create a disposable workspace path containing Chinese and spaces if possible.
5. Save a provider key in-app; confirm it is not written as plaintext under the workspace.
6. Exit Bolt; confirm no leftover python child process for Agent Core.
7. Relaunch; confirm credential continuity without re-entering the key if policy expects retention.
8. Uninstall or delete portable dir; confirm workspace files remain; confirm userData keep/delete matches design.
9. Record results into Release Evidence checks:
   - `clean_windows_e2e`
   - `install.nsis` or `package.portable`
   - `startup.core`
   - `exit.no-child-process`

## Blocked outcome

If this environment cannot provide a clean Windows target, keep:

```text
clean_windows_e2e_blocked
player_beta = No
```

Do not invent GUI E2E results from the developer machine.


## Important

`package.launch_smoke` only proves the process starts. It must never mark `clean_windows_e2e=passed`.
