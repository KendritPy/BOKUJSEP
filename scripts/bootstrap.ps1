param([switch]$SkipDownloads)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Ensure-Repo([string]$Url, [string]$Path, [string]$Ref = '', [switch]$Submodules) {
    if (Test-Path -LiteralPath (Join-Path $Path '.git')) { return }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    $arguments = @('clone', '--depth', '1')
    if ($Submodules) { $arguments += '--recurse-submodules' }
    if ($Ref) { $arguments += @('--branch', $Ref, '--single-branch') }
    $arguments += @($Url, $Path)
    & git @arguments
    if ($LASTEXITCODE -ne 0) { throw "Falló git clone: $Url" }
}

function Ensure-RepoAtCommit([string]$Url, [string]$Path, [string]$Commit) {
    if (Test-Path -LiteralPath (Join-Path $Path '.git')) { return }
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
    & git -C $Path init
    & git -C $Path remote add origin $Url
    & git -C $Path fetch --depth 1 origin $Commit
    & git -C $Path checkout --detach FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw "Falló git checkout: $Url en $Commit" }
}

function Warn-IfUnexpectedRevision([string]$Path, [string]$Expected) {
    $actual = (& git -C $Path rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "No se puede leer la revisión del repositorio: $Path" }
    if ($actual -ne $Expected) {
        Write-Warning "$Path está en $actual; la revisión auditada es $Expected. Los checkouts existentes nunca se sobrescriben."
    }
}

$koreanCommit = '97d0b30391ccfd44764863b1873f7d0a68246c96'
$pleonexCommit = 'dae1215b13ca7dbc6fa17971ecd3d58de86b097a'
$ppssppCommit = 'fa50bb1976065c4f8b1b47af227d367fe9771555'

Ensure-Repo 'https://github.com/snake7594/boku-natsu-portable-kr-patch.git' (Join-Path $root 'external/boku-korean-tools') 'v0.1.3-image-kr'
# Los commits útiles de tabla/fuente de GriffithVIII son públicos, pero ninguna rama apunta a ellos.
# Se obtiene directamente el commit auditado para no clonar silenciosamente la rama por defecto de 2015.
Ensure-RepoAtCommit 'https://github.com/pleonex/Boku-no-Natsuyasumi.git' (Join-Path $root 'external/boku-pleonex') $pleonexCommit
Ensure-Repo 'https://github.com/xan1242/PSPModBase.git' (Join-Path $root 'external/pspmodbase') -Submodules
& git -C (Join-Path $root 'external/pspmodbase') submodule update --init --depth 1
if ($LASTEXITCODE -ne 0) { throw 'Falló la preparación del submódulo PSPSDK de PSPModBase.' }

if (-not (Test-Path -LiteralPath (Join-Path $root 'external/ppsspp-source/.git'))) {
    & git clone --depth 1 --filter=blob:none --sparse --branch v1.20.4 --single-branch 'https://github.com/hrydgard/ppsspp.git' (Join-Path $root 'external/ppsspp-source')
    & git -C (Join-Path $root 'external/ppsspp-source') sparse-checkout set Core HLE Windows UI docs scripts
}

Warn-IfUnexpectedRevision (Join-Path $root 'external/boku-korean-tools') $koreanCommit
Warn-IfUnexpectedRevision (Join-Path $root 'external/boku-pleonex') $pleonexCommit
Warn-IfUnexpectedRevision (Join-Path $root 'external/ppsspp-source') $ppssppCommit

if (-not $SkipDownloads) {
    $ppssppZip = Join-Path $root 'external/ppsspp-bin/PPSSPP-v1.20.4-Windows-x64.zip'
    $ppssppExe = Join-Path $root 'external/ppsspp-bin/portable/PPSSPPWindows64.exe'
    if (-not (Test-Path -LiteralPath $ppssppZip)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ppssppZip) | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/hrydgard/ppsspp/releases/download/v1.20.4/PPSSPP-v1.20.4-Windows-x64.zip' -OutFile $ppssppZip
    }
    if (-not (Test-Path -LiteralPath $ppssppExe)) {
        Expand-Archive -Force -LiteralPath $ppssppZip -DestinationPath (Join-Path $root 'external/ppsspp-bin/portable')
    }
}

$venv = Join-Path $root '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts/python.exe'))) {
    & python -m venv $venv
}
& (Join-Path $venv 'Scripts/python.exe') -m pip install --disable-pip-version-check -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias de Python.' }
Write-Host 'Preparación de dependencias completada.' -ForegroundColor Green
