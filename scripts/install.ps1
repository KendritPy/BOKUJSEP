$ErrorActionPreference = 'Stop'

Write-Host '==> Bootstrap dependencies' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'bootstrap.ps1')

Write-Host '==> Create local Spanish runtime ISO' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'setup.ps1')

Write-Host '==> Extract and build runtime data' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'pipeline.ps1')

Write-Host '==> Build BokuLangToggle' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'build.ps1')

Write-Host 'Installation complete. Run launch.bat to play.' -ForegroundColor Green
