$ErrorActionPreference = 'Stop'

Write-Host '==> Preparando dependencias' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'bootstrap.ps1')

Write-Host '==> Verificando las ISOs japonesa y española aportadas por el usuario' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'setup.ps1')

Write-Host '==> Extrayendo y generando los datos de runtime' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'pipeline.ps1')

Write-Host '==> Compilando BokuLangToggle' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'build.ps1')

Write-Host 'Instalación completada. Ejecuta launch.bat para jugar.' -ForegroundColor Green
