param(
    [string]$Iso = '',
    [int]$DebuggerPort = 8765,
    [ValidateSet('F5', 'F6', 'F7')]
    [string]$Hotkey = 'F7',
    [switch]$Interpreter
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not $Iso) { $Iso = Join-Path $root 'input/es/Boku_ES.iso' }
if (-not (Test-Path -LiteralPath $Iso)) { throw "No se encontró la ISO: $Iso. Ejecuta install.bat primero." }

$exe = Join-Path $root 'external/ppsspp-bin/portable/PPSSPPWindows64.exe'
$memstick = Join-Path $root 'external/ppsspp-bin/portable/memstick'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Falta la instalación portátil de PPSSPP. Ejecuta install.bat primero.' }

$running = Get-Process -Name 'PPSSPPWindows64' -ErrorAction SilentlyContinue
if ($running) {
    $ids = ($running.Id | Sort-Object) -join ', '
    throw "PPSSPP ya está ejecutándose (PID: $ids). Ciérralo por completo y vuelve a ejecutar launch.bat."
}

# Un arranque anterior puede dejar activo el helper oculto de la tecla de cambio.
# Detenemos únicamente los helpers iniciados desde este checkout para evitar duplicar pulsaciones.
$debugClient = Join-Path $root 'tools/ppsspp_debug.py'
$staleHotkeys = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine.Contains($debugClient) -and
        $_.CommandLine -match '\bhotkey\b'
    }
foreach ($helper in $staleHotkeys) {
    Stop-Process -Id $helper.ProcessId -Force -ErrorAction SilentlyContinue
}

& (Join-Path $PSScriptRoot 'deploy.ps1') -Memstick $memstick
& (Join-Path $PSScriptRoot 'configure-ppsspp.ps1') -Memstick $memstick -DebuggerPort $DebuggerPort

$ppssppArgs = [Collections.Generic.List[string]]::new()
if ($Interpreter) { $ppssppArgs.Add('-i') }
$ppssppArgs.Add("`"$Iso`"")
Start-Process -FilePath $exe -ArgumentList $ppssppArgs

Write-Host "PPSSPP iniciado; esperando el puerto de depuración $DebuggerPort..."
$deadline = [DateTime]::UtcNow.AddSeconds(20)
$ready = $false
do {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $client.Connect('127.0.0.1', $DebuggerPort)
        $ready = $true
    } catch {
        Start-Sleep -Milliseconds 250
    } finally {
        $client.Dispose()
    }
} while (-not $ready -and [DateTime]::UtcNow -lt $deadline)
if (-not $ready) { throw "El depurador de PPSSPP no abrió el puerto $DebuggerPort en 20 segundos." }

$pythonw = Join-Path $root '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Falta el entorno de Python. Ejecuta install.bat primero.' }
Start-Process -FilePath $pythonw `
    -ArgumentList @("`"$debugClient`"", '--port', $DebuggerPort, 'hotkey', '--key', $Hotkey) `
    -WindowStyle Hidden

Write-Host "Cambio de idioma activo en $Hotkey." -ForegroundColor Green
