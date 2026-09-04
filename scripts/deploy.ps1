param([string]$Memstick = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Memstick) { $Memstick = Join-Path $root 'external/ppsspp-bin/portable/memstick' }
$source = Join-Path $root 'dist/BokuLangToggle'
if (-not (Test-Path -LiteralPath (Join-Path $source 'BokuLangToggle.prx'))) { & (Join-Path $PSScriptRoot 'build.ps1') }
$target = Join-Path $Memstick 'PSP/PLUGINS/BokuLangToggle'
New-Item -ItemType Directory -Force -Path $target | Out-Null
foreach ($name in @('BokuLangToggle.prx', 'plugin.ini', 'BokuLangToggle.ini', 'dialogue_blob.bin', 'jp_atlas0.pim', 'es_atlas0.pim')) {
    $destination = Join-Path $target $name
    if (Test-Path -LiteralPath $destination) { Copy-Item -Force -LiteralPath $destination -Destination "$destination.bak" }
    $sourceFile = if ($name -eq 'BokuLangToggle.ini') {
        Join-Path $root 'plugin/BokuLangToggle.ini'
    } else {
        Join-Path $source $name
    }
    Copy-Item -Force -LiteralPath $sourceFile -Destination $destination
}
Write-Host "Deployed plugin to $target" -ForegroundColor Green
Write-Host 'Toggle key: F7 (launch.bat starts the bridge automatically; the guest button follows BokuLangToggle.ini).'
