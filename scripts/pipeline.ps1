param([switch]$Force)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Ejecuta scripts/bootstrap.ps1 primero.' }
$jp = Join-Path $root 'input/jp/Boku_JP.iso'
$es = Join-Path $root 'input/es/Boku_ES.iso'
if (-not (Test-Path -LiteralPath $jp) -or -not (Test-Path -LiteralPath $es)) { throw 'Ejecuta scripts/setup.ps1 primero con las ISOs compatibles.' }
$forceArg = @()
if ($Force) { $forceArg += '--force' }

function Invoke-PythonStage([string]$Name, [string]$Script, [string[]]$Arguments = @()) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $python (Join-Path $root $Script) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name falló con código de salida $LASTEXITCODE"
    }
}

Invoke-PythonStage 'Extrayendo ISO/CDIMG japonesa' 'tools/extract_game.py' (@('--iso', $jp, '--edition', 'jp') + $forceArg)
Invoke-PythonStage 'Extrayendo ISO/CDIMG española' 'tools/extract_game.py' (@('--iso', $es, '--edition', 'es') + $forceArg)
Invoke-PythonStage 'Comparando archivos extraídos' 'tools/compare_files.py'
Invoke-PythonStage 'Comparando ejecutables ELF JP/ES' 'tools/compare_eboot.py'
Invoke-PythonStage 'Extrayendo diálogos JP' 'tools/extract_dialogue.py' @('--edition', 'jp')
Invoke-PythonStage 'Extrayendo diálogos ES' 'tools/extract_dialogue.py' @('--edition', 'es')
Invoke-PythonStage 'Mapeando diálogos JP/ES' 'tools/compare_scripts.py'
Invoke-PythonStage 'Generando el blob bilingüe inmutable' 'tools/build_dialogue_blob.py'
Invoke-PythonStage 'Auditando cobertura de fuentes' 'tools/font_coverage.py'
Write-Host 'Extracción y análisis estructural completados.' -ForegroundColor Green
