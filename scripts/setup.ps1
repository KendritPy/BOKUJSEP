param(
    [string]$JpIso = '',
    [string]$EsIso = '',
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $JpIso) { $JpIso = Join-Path $root 'input/jp/Boku_JP.iso' }
if (-not $EsIso) { $EsIso = Join-Path $root 'input/es/Boku_ES.iso' }
if (-not (Test-Path -LiteralPath $JpIso -PathType Leaf)) {
    throw "Clean Japanese ISO not found. Place it at '$JpIso' or pass -JpIso <path>."
}
if (-not (Test-Path -LiteralPath $EsIso -PathType Leaf)) {
    throw "Spanish v1.0 ISO not found. Patch your own clean dump, place it at '$EsIso', or pass -EsIso <path>."
}

function Import-Iso([string]$Source, [string]$Destination, [string]$Label) {
    $sourcePath = (Resolve-Path -LiteralPath $Source).Path
    $destinationPath = [IO.Path]::GetFullPath($Destination)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationPath) | Out-Null
    if ($sourcePath.Equals($destinationPath, [StringComparison]::OrdinalIgnoreCase)) {
        return $destinationPath
    }
    if ((Test-Path -LiteralPath $destinationPath) -and -not $Force) {
        throw "$Label ISO already exists at '$destinationPath'. Pass -Force to replace it from '$sourcePath'."
    }
    Copy-Item -Force -LiteralPath $sourcePath -Destination $destinationPath
    return $destinationPath
}

$localJp = Import-Iso $JpIso (Join-Path $root 'input/jp/Boku_JP.iso') 'Japanese'
$localEs = Import-Iso $EsIso (Join-Path $root 'input/es/Boku_ES.iso') 'Spanish'

$jpHash = Get-FileHash -Algorithm MD5 -LiteralPath $localJp
Write-Host "JP ISO MD5: $($jpHash.Hash)"
if ($jpHash.Hash -ne 'B4D363D59CB87E25AB76AFC5384CCA31') {
    throw 'The Japanese ISO does not match the supported clean retail MD5.'
}

$esHash = Get-FileHash -Algorithm SHA256 -LiteralPath $localEs
Write-Host "ES v1.0 ISO SHA256: $($esHash.Hash)"
if ($esHash.Hash -ne '3F3ED57C390684F774432B689EA94DF9C0EA5641D2ED907A3EE03BF1F69EE9C8') {
    throw 'The Spanish ISO does not match the supported GriffithVIII/TraduSquare v1.0 image.'
}

Write-Host 'Both user-supplied ISOs are present and match the supported builds.' -ForegroundColor Green
