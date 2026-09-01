param([string]$Output = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Output) { $Output = Join-Path $root 'analysis/debugger/ppsspp-window.png' }
Add-Type -AssemblyName System.Drawing
if (-not ('BokuWindowCapture' -as [type])) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class BokuWindowCapture {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr window, out RECT rect);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr window, IntPtr dc, uint flags);
}
'@
}
$process = Get-Process PPSSPPWindows64,PPSSPPWindows -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $process) { throw 'A visible PPSSPP window was not found.' }
$rect = New-Object BokuWindowCapture+RECT
[BokuWindowCapture]::GetWindowRect($process.MainWindowHandle, [ref]$rect) | Out-Null
$bitmap = New-Object Drawing.Bitmap ($rect.Right - $rect.Left), ($rect.Bottom - $rect.Top)
$graphics = [Drawing.Graphics]::FromImage($bitmap)
$dc = $graphics.GetHdc()
[BokuWindowCapture]::PrintWindow($process.MainWindowHandle, $dc, 2) | Out-Null
$graphics.ReleaseHdc($dc)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null
$bitmap.Save($Output, [Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output $Output
