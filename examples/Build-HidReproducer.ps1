param([string]$SimHubDir = 'C:\Program Files (x86)\SimHub')
$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$hidSharp = Join-Path $SimHubDir 'HidSharp.dll'
if (-not (Test-Path -LiteralPath $compiler)) { throw '64-bit .NET Framework C# compiler not found.' }
if (-not (Test-Path -LiteralPath $hidSharp)) { throw 'HidSharp.dll not found; provide the installed SimHub directory.' }
$source = Join-Path $PSScriptRoot 'HidReproducer.cs'
$output = Join-Path $PSScriptRoot 'HidReproducer.exe'
& $compiler /nologo /target:exe /optimize+ ('/out:' + $output) ('/reference:' + $hidSharp) $source
if ($LASTEXITCODE -ne 0) { throw 'C# build failed.' }
Copy-Item -LiteralPath $hidSharp -Destination (Join-Path $PSScriptRoot 'HidSharp.dll') -Force
Write-Output "Built $output with a local runtime dependency. No HID device was opened."
