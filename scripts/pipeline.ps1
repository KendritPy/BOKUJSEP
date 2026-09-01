param([switch]$Force)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run scripts/bootstrap.ps1 first.' }
$jp = Join-Path $root 'input/jp/Boku_JP.iso'
$es = Join-Path $root 'input/es/Boku_ES.iso'
if (-not (Test-Path -LiteralPath $jp) -or -not (Test-Path -LiteralPath $es)) { throw 'Run scripts/setup.ps1 with a clean JP ISO first.' }
$forceArg = @()
if ($Force) { $forceArg += '--force' }
& $python (Join-Path $root 'tools/extract_game.py') --iso $jp --edition jp @forceArg
if ($LASTEXITCODE -ne 0) { throw 'JP extraction failed' }
& $python (Join-Path $root 'tools/extract_game.py') --iso $es --edition es @forceArg
if ($LASTEXITCODE -ne 0) { throw 'ES extraction failed' }
& $python (Join-Path $root 'tools/compare_files.py')
& $python (Join-Path $root 'tools/extract_dialogue.py') --edition jp
& $python (Join-Path $root 'tools/extract_dialogue.py') --edition es
& $python (Join-Path $root 'tools/compare_scripts.py')
& $python (Join-Path $root 'tools/font_coverage.py')
if ($LASTEXITCODE -ne 0) { throw 'Analysis pipeline failed' }
Write-Host 'Extraction and structural analysis complete.' -ForegroundColor Green

