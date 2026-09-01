param(
    [string]$Memstick,
    [int]$DebuggerPort = 8765
)
$ErrorActionPreference = 'Stop'
if (-not $Memstick) { throw '-Memstick is required' }
$system = Join-Path $Memstick 'PSP/SYSTEM'
$config = Join-Path $system 'ppsspp.ini'
New-Item -ItemType Directory -Force -Path $system | Out-Null
if (Test-Path -LiteralPath $config) {
    Copy-Item -Force -LiteralPath $config -Destination "$config.boku-backup"
    $lines = [Collections.Generic.List[string]](Get-Content -LiteralPath $config)
} else {
    $lines = [Collections.Generic.List[string]]@('[General]')
}

function Set-GeneralValue([string]$Name, [string]$Value) {
    $section = -1
    $next = $lines.Count
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -eq '[General]') { $section = $i; continue }
        if ($section -ge 0 -and $lines[$i] -match '^\[') { $next = $i; break }
    }
    if ($section -lt 0) {
        $lines.Insert(0, '[General]')
        $section = 0
        $next = $lines.Count
    }
    for ($i = $section + 1; $i -lt $next; $i++) {
        if ($lines[$i] -match "^\s*$([Regex]::Escape($Name))\s*=") {
            $lines[$i] = "$Name = $Value"
            return
        }
    }
    $lines.Insert($next, "$Name=$Value")
}

Set-GeneralValue 'FirstRun' 'False'
Set-GeneralValue 'EnablePlugins' 'True'
Set-GeneralValue 'RemoteISOPort' ([string]$DebuggerPort)
Set-GeneralValue 'RemoteDebuggerOnStartup' 'True'
Set-GeneralValue 'RemoteDebuggerLocal' 'True'
[IO.File]::WriteAllLines($config, $lines, [Text.UTF8Encoding]::new($false))
Write-Host "Configured PPSSPP debugger and plugins in $config"
