$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vsmake = Join-Path $root 'external/pspmodbase/external/pspsdk/vsmake.ps1'
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $vsmake)) { throw 'PSP toolchain missing; run scripts/bootstrap.ps1' }
if (-not (Test-Path -LiteralPath $python)) { throw 'Python environment missing; run scripts/bootstrap.ps1' }
New-Item -ItemType Directory -Force -Path (Join-Path $root 'build/plugin'), (Join-Path $root 'dist/BokuLangToggle') | Out-Null
& $python (Join-Path $root 'tools/build_dialogue_blob.py')
if ($LASTEXITCODE -ne 0) { throw 'Dialogue blob build failed' }
& $python (Join-Path $root 'tools/export_runtime_assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Runtime font export failed' }
& $vsmake -C (Join-Path $root 'plugin') clean
& $vsmake -C (Join-Path $root 'plugin')
if ($LASTEXITCODE -ne 0) { throw 'PRX build failed' }
$prx = Join-Path $root 'build/plugin/BokuLangToggle.prx'
if (-not (Test-Path -LiteralPath $prx)) { throw "Build completed without expected PRX: $prx" }
$dist = Join-Path $root 'dist/BokuLangToggle'
Copy-Item -Force -LiteralPath $prx, (Join-Path $root 'plugin/plugin.ini'), (Join-Path $root 'plugin/BokuLangToggle.ini') -Destination $dist
Copy-Item -Force -LiteralPath (Join-Path $root 'build/generated/dialogue_blob.bin'), (Join-Path $root 'build/generated/jp_atlas0.pim'), (Join-Path $root 'build/generated/es_atlas0.pim') -Destination $dist
Get-FileHash -Algorithm SHA256 -LiteralPath $prx
Write-Host "Built $prx" -ForegroundColor Green
