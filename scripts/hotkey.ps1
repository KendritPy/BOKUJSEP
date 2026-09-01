param(
    [int]$DebuggerPort = 8765,
    [ValidateSet('F5', 'F6', 'F7')]
    [string]$Key = 'F7'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv/Scripts/python.exe'
& $python (Join-Path $root 'tools/ppsspp_debug.py') --port $DebuggerPort hotkey --key $Key
