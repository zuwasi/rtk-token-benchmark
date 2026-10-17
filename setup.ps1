# Prepares everything bench.py needs. Run from the repository root on Windows (PowerShell 7).
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$rtkVersion = 'v1.0.1'

Write-Host "Downloading rtk $rtkVersion"
Invoke-WebRequest "https://github.com/rtk-ai/rtk/releases/download/$rtkVersion/rtk-x86_64-pc-windows-msvc.zip" -OutFile "$root\rtk.zip"
Expand-Archive "$root\rtk.zip" -DestinationPath "$root\rtk-bin" -Force

Write-Host "Cloning rtk-ai/rtk at the benchmarked commit"
git clone --filter=blob:none https://github.com/rtk-ai/rtk.git "$root\repo"
git -C "$root\repo" checkout -q f16becacd2f40616839333b3e0e281e40a0bc823

# Dirty the working tree so git status has something to report.
$mds = Get-ChildItem "$root\repo\docs" -Recurse -Filter *.md -File | Select-Object -First 12
foreach ($f in $mds) { Add-Content -Path $f.FullName -Value "`n<!-- benchmark scratch note -->" }
1..8 | ForEach-Object { Set-Content "$root\repo\bench_untracked_$_.txt" "scratch file $_" }
New-Item -ItemType Directory -Force "$root\repo\bench_scratch" | Out-Null
1..3 | ForEach-Object { Set-Content "$root\repo\bench_scratch\note_$_.md" 'scratch' }
git -C "$root\repo" add $mds[0].FullName $mds[1].FullName

Write-Host "Python environment"
python -m venv "$root\.venv"
& "$root\.venv\Scripts\python.exe" -m pip install --quiet tiktoken tokenizers pytest pillow

Write-Host "Tokenizers"
New-Item -ItemType Directory -Force "$root\tokenizers" | Out-Null
Invoke-WebRequest 'https://huggingface.co/NousResearch/Meta-Llama-3.1-8B/resolve/main/tokenizer.json' -OutFile "$root\tokenizers\llama31.json"
Invoke-WebRequest 'https://huggingface.co/Qwen/Qwen3-8B/resolve/main/tokenizer.json' -OutFile "$root\tokenizers\qwen3.json"
Invoke-WebRequest 'https://huggingface.co/unsloth/gemma-3-4b-it/resolve/main/tokenizer.json' -OutFile "$root\tokenizers\gemma3.json"
Push-Location "$root\claude-tok"; npm install --no-fund --no-audit; Pop-Location

Write-Host "Test suites"
& "$root\.venv\Scripts\python.exe" "$root\make_projects.py"
Push-Location "$root\work\jsproj"; npm install --no-fund --no-audit; Pop-Location

Write-Host "Done. Next: .venv\Scripts\python.exe bench.py"
