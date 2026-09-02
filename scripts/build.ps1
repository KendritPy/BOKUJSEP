$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vsmake = Join-Path $root 'external/pspmodbase/external/pspsdk/vsmake.ps1'
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $vsmake)) { throw 'Falta el toolchain de PSP; ejecuta scripts/bootstrap.ps1.' }
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta el entorno de Python; ejecuta scripts/bootstrap.ps1.' }
New-Item -ItemType Directory -Force -Path (Join-Path $root 'build/plugin'), (Join-Path $root 'dist/BokuLangToggle') | Out-Null
& $python (Join-Path $root 'tools/build_dialogue_blob.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la generación del blob de diálogos.' }
& $python (Join-Path $root 'tools/export_runtime_assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la exportación de los recursos de fuente.' }
& $vsmake -C (Join-Path $root 'plugin') clean
& $vsmake -C (Join-Path $root 'plugin')
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación del PRX.' }
$prx = Join-Path $root 'build/plugin/BokuLangToggle.prx'
if (-not (Test-Path -LiteralPath $prx)) { throw "La compilación terminó sin generar el PRX esperado: $prx" }
$dist = Join-Path $root 'dist/BokuLangToggle'
Copy-Item -Force -LiteralPath $prx, (Join-Path $root 'plugin/plugin.ini'), (Join-Path $root 'plugin/BokuLangToggle.ini') -Destination $dist
Copy-Item -Force -LiteralPath (Join-Path $root 'build/generated/dialogue_blob.bin'), (Join-Path $root 'build/generated/jp_atlas0.pim'), (Join-Path $root 'build/generated/es_atlas0.pim') -Destination $dist
Get-FileHash -Algorithm SHA256 -LiteralPath $prx
Write-Host "Compilado: $prx" -ForegroundColor Green
