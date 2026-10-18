<#
.SYNOPSIS
  Removes the block added by install.ps1 from rtk's config.toml (backs it up first).
  Deletes the file if nothing else is left in it.
#>
param(
    [string]$ConfigPath,
    [string]$Rtk = "rtk"
)
$ErrorActionPreference = "Stop"
$begin = "# BEGIN rtk-lint-script-fix (rtk-ai/rtk#1489, #2094)"
$end = "# END rtk-lint-script-fix"

if (-not $ConfigPath) {
    $env:RTK_SUPPRESS_HOOK_WARNING = "1"
    $line = $null
    if (Get-Command $Rtk -ErrorAction SilentlyContinue) {
        $line = & $Rtk config 2>$null | Where-Object { $_ -like "Config:*" } | Select-Object -First 1
    }
    if ($line) { $ConfigPath = $line.Substring(7).Trim() }
    else { $ConfigPath = Join-Path $env:APPDATA "rtk\config.toml" }
}

if (-not (Test-Path -LiteralPath $ConfigPath)) { Write-Host "No config at $ConfigPath. Nothing to remove."; exit 0 }
$lines = @(Get-Content -LiteralPath $ConfigPath -Encoding UTF8)
if ($lines -notcontains $begin) { Write-Host "Fix is not installed in $ConfigPath. Nothing changed."; exit 0 }

$backup = "$ConfigPath.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
Copy-Item -LiteralPath $ConfigPath -Destination $backup

$keep = New-Object System.Collections.Generic.List[string]
$inside = $false
foreach ($l in $lines) {
    if ($l -eq $begin) { $inside = $true; continue }
    if ($inside -and $l -eq $end) { $inside = $false; continue }
    if (-not $inside) { $keep.Add($l) }
}
while ($keep.Count -gt 0 -and $keep[$keep.Count - 1].Trim() -eq "") { $keep.RemoveAt($keep.Count - 1) }

if ($keep.Count -eq 0) {
    Remove-Item -LiteralPath $ConfigPath
    Write-Host "Removed the fix. The config held nothing else, so it was deleted (backup: $backup)."
}
else {
    $text = ($keep -join "`n") + "`n"
    [IO.File]::WriteAllText($ConfigPath, $text, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Removed the fix from $ConfigPath (backup: $backup)."
}
