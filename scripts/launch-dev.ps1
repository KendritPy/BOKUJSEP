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
if (-not (Test-Path -LiteralPath $Iso)) { throw "ISO not found: $Iso" }
$exe = Join-Path $root 'external/ppsspp-bin/portable/PPSSPPWindows64.exe'
$memstick = Join-Path $root 'external/ppsspp-bin/portable/memstick'
& (Join-Path $PSScriptRoot 'deploy.ps1') -Memstick $memstick
& (Join-Path $PSScriptRoot 'configure-ppsspp.ps1') -Memstick $memstick -DebuggerPort $DebuggerPort

$ppssppArgs = [Collections.Generic.List[string]]::new()
if ($Interpreter) {
    # PPSSPP's interpreter is far slower than JIT, but memory breakpoints and
    # register state are substantially more reliable for reverse engineering.
    # PPSSPP 1.20.4's desktop command-line parser uses the short -i flag.
    $ppssppArgs.Add('-i')
}
$ppssppArgs.Add("`"$Iso`"")
Start-Process -FilePath $exe -ArgumentList $ppssppArgs
Write-Host "PPSSPP started; waiting for debugger port $DebuggerPort..."
if ($Interpreter) {
    Write-Host 'CPU backend forced to interpreter for reliable memchecks/register state.'
}
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
$debugClient = Join-Path $root 'tools/ppsspp_debug.py'
Start-Process -FilePath $pythonw `
    -ArgumentList @("`"$debugClient`"", '--port', $DebuggerPort, 'hotkey', '--key', $Hotkey) `
    -WindowStyle Hidden
Write-Host "Language hotkey active on $Hotkey (PPSSPP has no default binding for it)."
