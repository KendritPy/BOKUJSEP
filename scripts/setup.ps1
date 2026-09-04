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
    throw "No se encontró la ISO japonesa limpia. Colócala en '$JpIso' o usa -JpIso <ruta>."
}
if (-not (Test-Path -LiteralPath $EsIso -PathType Leaf)) {
    throw "No se encontró la ISO española v1.0. Aplica el parche oficial a una copia de tu ISO limpia, colócala en '$EsIso' o usa -EsIso <ruta>."
}

function Import-Iso([string]$Source, [string]$Destination, [string]$Label) {
    $sourcePath = (Resolve-Path -LiteralPath $Source).Path
    $destinationPath = [IO.Path]::GetFullPath($Destination)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationPath) | Out-Null
    if ($sourcePath.Equals($destinationPath, [StringComparison]::OrdinalIgnoreCase)) {
        return $destinationPath
    }
    if ((Test-Path -LiteralPath $destinationPath) -and -not $Force) {
        throw "La ISO $Label ya existe en '$destinationPath'. Usa -Force para reemplazarla desde '$sourcePath'."
    }
    Copy-Item -Force -LiteralPath $sourcePath -Destination $destinationPath
    return $destinationPath
}

$localJp = Import-Iso $JpIso (Join-Path $root 'input/jp/Boku_JP.iso') 'japonesa'
$localEs = Import-Iso $EsIso (Join-Path $root 'input/es/Boku_ES.iso') 'española'

$jpHash = Get-FileHash -Algorithm MD5 -LiteralPath $localJp
Write-Host "MD5 de la ISO JP: $($jpHash.Hash)"
if ($jpHash.Hash -ne 'B4D363D59CB87E25AB76AFC5384CCA31') {
    throw 'La ISO japonesa no coincide con el MD5 de la versión limpia soportada.'
}

$esHash = Get-FileHash -Algorithm SHA256 -LiteralPath $localEs
Write-Host "SHA256 de la ISO ES v1.0: $($esHash.Hash)"
if ($esHash.Hash -ne '3F3ED57C390684F774432B689EA94DF9C0EA5641D2ED907A3EE03BF1F69EE9C8') {
    throw 'La ISO española no coincide con la imagen v1.0 de GriffithVIII/TraduSquare soportada.'
}

Write-Host 'Ambas ISOs están presentes y coinciden con las versiones soportadas.' -ForegroundColor Green
