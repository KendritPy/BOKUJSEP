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
    if ($LASTEXITCODE -ne 0) { throw "git clone failed: $Url" }
}

function Ensure-RepoAtCommit([string]$Url, [string]$Path, [string]$Commit) {
    if (Test-Path -LiteralPath (Join-Path $Path '.git')) { return }
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
    & git -C $Path init
    & git -C $Path remote add origin $Url
    & git -C $Path fetch --depth 1 origin $Commit
    & git -C $Path checkout --detach FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed: $Url at $Commit" }
}

function Warn-IfUnexpectedRevision([string]$Path, [string]$Expected) {
    $actual = (& git -C $Path rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "cannot read repository revision: $Path" }
    if ($actual -ne $Expected) {
        Write-Warning "$Path is at $actual; audited revision is $Expected. Existing checkouts are never overwritten."
    }
}

$spanishCommit = 'c0e3d2d5417013e4f4b34e416b58743f7efd86ad'
$koreanCommit = '97d0b30391ccfd44764863b1873f7d0a68246c96'
$pleonexCommit = 'dae1215b13ca7dbc6fa17971ecd3d58de86b097a'
$ppssppCommit = 'fa50bb1976065c4f8b1b47af227d367fe9771555'

Ensure-Repo 'https://github.com/GriffithVIII/Boku-no-Natsuyasumi-ESP.git' (Join-Path $root 'external/boku-spanish') 'v1.0'
Ensure-Repo 'https://github.com/snake7594/boku-natsu-portable-kr-patch.git' (Join-Path $root 'external/boku-korean-tools') 'v0.1.3-image-kr'
# The useful GriffithVIII table/font commits are public but no branch points to
# them. Fetch the audited commit directly instead of silently cloning the 2015
# default branch.
Ensure-RepoAtCommit 'https://github.com/pleonex/Boku-no-Natsuyasumi.git' (Join-Path $root 'external/boku-pleonex') $pleonexCommit
Ensure-Repo 'https://github.com/xan1242/PSPModBase.git' (Join-Path $root 'external/pspmodbase') -Submodules
& git -C (Join-Path $root 'external/pspmodbase') submodule update --init --depth 1
if ($LASTEXITCODE -ne 0) { throw 'PSPModBase PSPSDK submodule setup failed' }

if (-not (Test-Path -LiteralPath (Join-Path $root 'external/ppsspp-source/.git'))) {
    & git clone --depth 1 --filter=blob:none --sparse --branch v1.20.4 --single-branch 'https://github.com/hrydgard/ppsspp.git' (Join-Path $root 'external/ppsspp-source')
    & git -C (Join-Path $root 'external/ppsspp-source') sparse-checkout set Core HLE Windows UI docs scripts
}

Warn-IfUnexpectedRevision (Join-Path $root 'external/boku-spanish') $spanishCommit
Warn-IfUnexpectedRevision (Join-Path $root 'external/boku-korean-tools') $koreanCommit
Warn-IfUnexpectedRevision (Join-Path $root 'external/boku-pleonex') $pleonexCommit
Warn-IfUnexpectedRevision (Join-Path $root 'external/ppsspp-source') $ppssppCommit

if (-not $SkipDownloads) {
    $patchArchive = Join-Path $root 'input/es/patch/bokuES-v1.0.rar'
    if (-not (Test-Path -LiteralPath $patchArchive)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $patchArchive) | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/GriffithVIII/Boku-no-Natsuyasumi-ESP/releases/download/v1.0/bokuES-v1.0.rar' -OutFile $patchArchive
    }
    $xdelta = Join-Path $root 'input/es/patch/bokuES-v1.0/patch/bokuES-v1.0.xdelta'
    if (-not (Test-Path -LiteralPath $xdelta)) {
        tar -xf $patchArchive -C (Split-Path -Parent $patchArchive)
        if ($LASTEXITCODE -ne 0) { throw 'Spanish patch archive extraction failed' }
    }

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
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
Write-Host 'Bootstrap complete.' -ForegroundColor Green
