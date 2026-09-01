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

function Invoke-PythonStage([string]$Name, [string]$Script, [string[]]$Arguments = @()) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $python (Join-Path $root $Script) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-PythonStage 'Extract JP ISO/CDIMG' 'tools/extract_game.py' (@('--iso', $jp, '--edition', 'jp') + $forceArg)
Invoke-PythonStage 'Extract ES ISO/CDIMG' 'tools/extract_game.py' (@('--iso', $es, '--edition', 'es') + $forceArg)
Invoke-PythonStage 'Compare extracted files' 'tools/compare_files.py'
Invoke-PythonStage 'Extract JP dialogue' 'tools/extract_dialogue.py' @('--edition', 'jp')
Invoke-PythonStage 'Extract ES dialogue' 'tools/extract_dialogue.py' @('--edition', 'es')
Invoke-PythonStage 'Map JP/ES dialogue' 'tools/compare_scripts.py'
Invoke-PythonStage 'Audit font coverage' 'tools/font_coverage.py'
Write-Host 'Extraction and structural analysis complete.' -ForegroundColor Green
