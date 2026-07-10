param(
  [Parameter(Mandatory = $true)][string]$ArtifactPath,
  [string]$EvidenceDir = "release-evidence/clean-windows"
)

$ErrorActionPreference = "Stop"

function Write-Json($Path, $Object) {
  $json = $Object | ConvertTo-Json -Depth 6
  New-Item -ItemType Directory -Force -Path (Split-Path $Path) | Out-Null
  Set-Content -Path $Path -Value $json -Encoding utf8
}

$checks = [ordered]@{
  "clean_windows_preflight" = "not_run"
  "clean_windows_e2e" = "not_run"
}

$pollution = @()
foreach ($cmd in @("node", "python", "uv")) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) {
    $pollution += "found_command:$cmd"
  }
}
if ($env:VITE_DEV_SERVER_URL) { $pollution += "env:VITE_DEV_SERVER_URL" }
if ($env:BOLT_CORE_BEARER) { $pollution += "env:BOLT_CORE_BEARER" }
if (Test-Path "$env:APPDATA\Bolt") { $pollution += "existing_user_data" }

if (-not (Test-Path $ArtifactPath)) {
  $checks["clean_windows_preflight"] = "failed"
  $checks["clean_windows_e2e"] = "failed"
  Write-Json (Join-Path $EvidenceDir "clean-windows-checks.json") @{
    status = "failed"
    reason = "artifact_missing"
    checks = $checks
    pollution = $pollution
  }
  Write-Error "Artifact missing: $ArtifactPath"
  exit 1
}

if ($pollution.Count -gt 0) {
  $checks["clean_windows_preflight"] = "blocked"
  $checks["clean_windows_e2e"] = "blocked"
  Write-Json (Join-Path $EvidenceDir "clean-windows-checks.json") @{
    status = "blocked"
    reason = "clean_windows_e2e_blocked"
    checks = $checks
    pollution = $pollution
    note = "Developer machine is not a clean Windows target. Run this script inside Windows Sandbox/VM/new standard user."
  }
  Write-Host "clean_windows_e2e_blocked"
  Write-Host ($pollution -join ", ")
  exit 2
}

$checks["clean_windows_preflight"] = "passed"
# Launch smoke only on clean hosts. This is NOT full clean_windows_e2e.
$proc = Start-Process -FilePath $ArtifactPath -PassThru
Start-Sleep -Seconds 5
if (-not $proc.HasExited) {
  Stop-Process -Id $proc.Id -Force
  $checks["package.launch_smoke"] = "passed"
  $checks["clean_windows_e2e"] = "not_run"
  $status = "incomplete"
  $reason = "launch_smoke_only_full_e2e_not_run"
} else {
  $checks["package.launch_smoke"] = "failed"
  $checks["clean_windows_e2e"] = "not_run"
  $status = "failed"
  $reason = "process_exited_immediately"
}

Write-Json (Join-Path $EvidenceDir "clean-windows-checks.json") @{
  status = $status
  reason = $reason
  checks = $checks
  pollution = @()
  note = "clean_windows_e2e requires install/start/core/credentials/task/exit/uninstall evidence. Launch smoke alone is insufficient."
}
if ($status -eq "failed") { exit 1 }
Write-Host "clean windows launch smoke completed; clean_windows_e2e remains not_run"
exit 3
