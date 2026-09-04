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
if (-not (Test-Path -LiteralPath $Iso)) { throw "ISO not found: $Iso. Run install.bat first." }

$exe = Join-Path $root 'external/ppsspp-bin/portable/PPSSPPWindows64.exe'
$memstick = Join-Path $root 'external/ppsspp-bin/portable/memstick'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Portable PPSSPP is missing. Run install.bat first.' }

$running = Get-Process -Name 'PPSSPPWindows64' -ErrorAction SilentlyContinue
if ($running) {
    $ids = ($running.Id | Sort-Object) -join ', '
    throw "PPSSPP is already running (PID(s): $ids). Close it fully and run launch.bat again."
}

# A previous launcher can leave the hidden host-side hotkey helper alive.
# Stop only helpers started from this checkout so one keypress cannot be sent twice.
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

$ToggleButton = ''
$pluginConfig = Join-Path $root 'plugin/BokuLangToggle.ini'
if (Test-Path -LiteralPath $pluginConfig) {
    $configured = Select-String -LiteralPath $pluginConfig -Pattern '^\s*ToggleButton\s*=\s*(\S+)' |
        Select-Object -First 1
    if ($configured) { $ToggleButton = $configured.Matches[0].Groups[1].Value }
}
if (-not $ToggleButton) { $ToggleButton = 'NOTE' }

$ppssppArgs = [Collections.Generic.List[string]]::new()
if ($Interpreter) { $ppssppArgs.Add('-i') }
$ppssppArgs.Add("`"$Iso`"")
Start-Process -FilePath $exe -ArgumentList $ppssppArgs

Write-Host "PPSSPP started; waiting for debugger port $DebuggerPort..."
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
if (-not $ready) { throw "PPSSPP debugger did not open port $DebuggerPort within 20 seconds." }

$pythonw = Join-Path $root '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Python environment is missing. Run install.bat first.' }
Start-Process -FilePath $pythonw `
    -ArgumentList @("`"$debugClient`"", '--port', $DebuggerPort, 'hotkey', '--key', $Hotkey, '--button', $ToggleButton) `
    -WindowStyle Hidden

Write-Host "Language toggle active on $Hotkey -> guest $ToggleButton." -ForegroundColor Green
Write-Host "Hotkey diagnostics: $(Join-Path $root 'build/logs/hotkey.log')"
