<#
.SYNOPSIS
  Stops rtk from rewriting package.json "lint" scripts to `rtk lint` (rtk-ai/rtk#1489, #2094).
.DESCRIPTION
  Adds a marked [hooks] exclude_commands block to rtk's config.toml. Backs up an existing
  config first, never overwrites existing exclude_commands, then runs verify.ps1.
  Works in Windows PowerShell 5.1 and PowerShell 7.
.PARAMETER ConfigPath
  Use this config.toml instead of the one reported by `rtk config`.
.PARAMETER Rtk
  Path to the rtk executable (default: rtk on PATH).
#>
param(
    [string]$ConfigPath,
    [string]$Rtk = "rtk"
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$begin = "# BEGIN rtk-lint-script-fix (rtk-ai/rtk#1489, #2094)"
$end = "# END rtk-lint-script-fix"
$entries = @(
    '"npm run lint", "npm run-script lint", "npm rum lint", "npm urn lint", "npm lint",',
    '"pnpm lint", "pnpm run lint", "pnpm run-script lint",',
    '"npx lint", "pnpx lint", "lint",'
)
$excludeBlock = @("exclude_commands = [") + ($entries | ForEach-Object { "  $_" }) + @("]")

function Write-Utf8NoBom([string]$Path, [string[]]$Lines) {
    $text = ($Lines -join "`n") + "`n"
    [IO.File]::WriteAllText($Path, $text, (New-Object System.Text.UTF8Encoding($false)))
}

if (-not $ConfigPath) {
    $rtkCmd = Get-Command $Rtk -ErrorAction SilentlyContinue
    if (-not $rtkCmd) { Write-Error "rtk not found. Install rtk or pass -Rtk C:\path\to\rtk.exe"; exit 1 }
    $env:RTK_SUPPRESS_HOOK_WARNING = "1"
    $line = & $Rtk config 2>$null | Where-Object { $_ -like "Config:*" } | Select-Object -First 1
    if ($line) { $ConfigPath = $line.Substring(7).Trim() }
    else { $ConfigPath = Join-Path $env:APPDATA "rtk\config.toml" }
}
Write-Host "rtk config: $ConfigPath"

$dir = Split-Path -Parent $ConfigPath
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Utf8NoBom $ConfigPath (@($begin, "[hooks]") + $excludeBlock + @($end))
    Write-Host "Created config with the fix."
}
else {
    $lines = @(Get-Content -LiteralPath $ConfigPath -Encoding UTF8)
    if ($lines -contains $begin) {
        Write-Host "Fix is already installed. Nothing changed."
    }
    else {
        $hooksIdx = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^\s*\[hooks\]\s*(#.*)?$') { $hooksIdx = $i; break }
        }
        $hasExclude = $false
        if ($hooksIdx -ge 0) {
            for ($j = $hooksIdx + 1; $j -lt $lines.Count; $j++) {
                if ($lines[$j] -match '^\s*\[') { break }
                if ($lines[$j] -match '^\s*exclude_commands\s*=') { $hasExclude = $true; break }
            }
        }
        if (-not $hasExclude -and ($lines | Where-Object { $_ -match '^\s*hooks\.exclude_commands\s*=' })) { $hasExclude = $true }

        if ($hasExclude) {
            Write-Warning "Your config already has [hooks] exclude_commands. Not changing it automatically."
            Write-Host "Add these entries to your existing exclude_commands list in $ConfigPath :"
            $entries | ForEach-Object { Write-Host "  $_" }
            exit 2
        }

        $backup = "$ConfigPath.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
        Copy-Item -LiteralPath $ConfigPath -Destination $backup
        Write-Host "Backup: $backup"

        if ($hooksIdx -ge 0) {
            $before = $lines[0..$hooksIdx]
            $after = if ($hooksIdx + 1 -lt $lines.Count) { $lines[($hooksIdx + 1)..($lines.Count - 1)] } else { @() }
            $new = @($before) + @($begin) + $excludeBlock + @($end) + @($after)
            Write-Host "Added exclude_commands to the existing [hooks] table."
        }
        else {
            $new = @($lines) + @("", $begin, "[hooks]") + $excludeBlock + @($end)
            Write-Host "Appended a [hooks] table with the fix."
        }
        Write-Utf8NoBom $ConfigPath $new
    }
}

# rtk only reads its default config location, so a custom -ConfigPath cannot be verified live.
if (-not $PSBoundParameters.ContainsKey("ConfigPath")) {
    & (Join-Path $here "verify.ps1") -Rtk $Rtk
    exit $LASTEXITCODE
}
exit 0
