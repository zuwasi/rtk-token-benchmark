<#
.SYNOPSIS
  Checks that rtk no longer rewrites package.json "lint" scripts, and still rewrites direct linter calls.
  Exit code 0 = fix active, 1 = bug still present, 3 = rtk not found.
#>
param([string]$Rtk = "rtk")
if (-not (Get-Command $Rtk -ErrorAction SilentlyContinue)) {
    Write-Host "rtk not found. Pass -Rtk C:\path\to\rtk.exe"; exit 3
}
$env:RTK_SUPPRESS_HOOK_WARNING = "1"
$version = (& $Rtk --version 2>$null) -join " "
Write-Host "Checking $version"

function Get-Rewrite([string]$Cmd) {
    $out = (& $Rtk rewrite $Cmd 2>$null) -join " "
    return $out.Trim()
}

$fail = 0
$scripts = @("pnpm lint", "pnpm lint src/a.ts", "pnpm run lint", "npm run lint", "npm run lint -- --fix", "npm run-script lint")
foreach ($c in $scripts) {
    $r = Get-Rewrite $c
    if ($r -match '^rtk lint') {
        Write-Host ("  FAIL  {0,-24} -> {1}   (script body would be dropped)" -f $c, $r) -ForegroundColor Red
        $fail++
    }
    else {
        $shown = if ($r) { $r } else { "(runs unchanged)" }
        Write-Host ("  ok    {0,-24} -> {1}" -f $c, $shown) -ForegroundColor Green
    }
}

$controls = @{ "eslint src" = "rtk lint src"; "git status" = "rtk git status" }
foreach ($c in $controls.Keys) {
    $r = Get-Rewrite $c
    if ($r -eq $controls[$c]) {
        Write-Host ("  ok    {0,-24} -> {1}   (rtk still compresses this)" -f $c, $r) -ForegroundColor Green
    }
    else {
        $shown = if ($r) { $r } else { "(not rewritten)" }
        Write-Host ("  note  {0,-24} -> {1}   (expected {2}; rtk rewrites may be off or behave differently in this version)" -f $c, $shown, $controls[$c]) -ForegroundColor Yellow
    }
}

if ($fail -gt 0) {
    Write-Host "RESULT: bug still present ($fail command(s) rewritten to rtk lint). Run install.ps1, or upgrade rtk." -ForegroundColor Red
    exit 1
}
Write-Host "RESULT: fix active. package.json lint scripts run as written." -ForegroundColor Green
exit 0
