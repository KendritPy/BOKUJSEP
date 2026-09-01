param(
    [string]$JpIso = '',
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $JpIso) { $JpIso = Join-Path $root 'input/jp/Boku_JP.iso' }
if (-not (Test-Path -LiteralPath $JpIso -PathType Leaf)) {
    throw "Clean Japanese ISO not found. Place it at '$JpIso' or pass -JpIso <path>."
}
$JpIso = (Resolve-Path -LiteralPath $JpIso).Path
$localJp = Join-Path $root 'input/jp/Boku_JP.iso'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $localJp) | Out-Null
if ($JpIso -ne $localJp -and -not (Test-Path -LiteralPath $localJp)) {
    Copy-Item -LiteralPath $JpIso -Destination $localJp
}
$jpHash = Get-FileHash -Algorithm MD5 -LiteralPath $localJp
Write-Host "JP ISO MD5: $($jpHash.Hash)"
if ($jpHash.Hash -ne 'B4D363D59CB87E25AB76AFC5384CCA31') {
    Write-Warning 'The JP ISO does not match the known clean retail MD5. It will be identified by PARAM.SFO, but patching may fail.'
}

$esIso = Join-Path $root 'input/es/Boku_ES.iso'
if ((Test-Path -LiteralPath $esIso) -and -not $Force) {
    Write-Host "Spanish ISO already exists: $esIso"
    exit 0
}
$patch = Join-Path $root 'input/es/patch/bokuES-v1.0/patch/bokuES-v1.0.xdelta'
$xdeltaExe = Join-Path $root 'external/boku-korean-tools/release-assets/xdelta.exe'
if (-not (Test-Path -LiteralPath $patch)) { throw 'Spanish xdelta missing; run scripts/bootstrap.ps1' }
if (-not (Test-Path -LiteralPath $xdeltaExe)) { throw 'xdelta.exe missing; run scripts/bootstrap.ps1' }
$temporary = Join-Path $root 'input/es/Boku_ES.building.iso'
if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
& $xdeltaExe -d -s $localJp $patch $temporary
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $temporary)) { throw 'Spanish xdelta application failed' }
if (Test-Path -LiteralPath $esIso) { Remove-Item -LiteralPath $esIso }
Move-Item -LiteralPath $temporary -Destination $esIso
Write-Host "Created Spanish ISO without modifying the JP source: $esIso" -ForegroundColor Green

