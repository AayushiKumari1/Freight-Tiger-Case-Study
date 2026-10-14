Set-Location (Join-Path $PSScriptRoot "..")
Remove-Item runs -Recurse -Force -ErrorAction SilentlyContinue
1..3 | ForEach-Object {
    $env:PYTHONHASHSEED = $_ * 1234
    python -m freight_watch --out "runs/run$_" | Out-Null
}
$report = @("Reproducibility check: 3 untouched runs (PYTHONHASHSEED = 1234, 2468, 3702)")
$ok = $true
foreach ($f in "output.csv", "weekly_metrics.csv", "run_log.json") {
    $h = 1..3 | ForEach-Object { (Get-FileHash "runs/run$_/$f" -Algorithm SHA256).Hash }
    $same = ($h | Select-Object -Unique).Count -eq 1
    if (-not $same) { $ok = $false }
    $report += "  $f : " + $(if ($same) { "IDENTICAL across all 3 runs ($($h[0]))" } else { "DIFFERENT" })
}
$report += $(if ($ok) { "RESULT: PASS" } else { "RESULT: FAIL" })
$report | Tee-Object -FilePath outputs/repro_check.txt
