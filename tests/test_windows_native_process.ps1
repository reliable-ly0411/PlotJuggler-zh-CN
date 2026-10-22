# SPDX-License-Identifier: MPL-2.0
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../scripts/windows/native_process.ps1')
$directory = Join-Path ([IO.Path]::GetTempPath()) ('pj native gui ' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($directory)
try {
  $source = Join-Path $directory 'probe.cs'
  $exe = Join-Path $directory ('gui ' + [char]0x4e2d + [char]0x6587 + '.exe')
  [IO.File]::WriteAllText($source, @'
using System;
using System.Text;
using System.Threading;
class Probe {
  static int Main(string[] args) {
    Console.OutputEncoding = new UTF8Encoding(false);
    string[] expected = {"space value", "\u4e2d\u6587", "trailing\\", "quote\"inside", "", "\\\"mixed"};
    if (args.Length != expected.Length + 1) return 91;
    for (int i=0; i<expected.Length; ++i) if(args[i+1] != expected[i]) return 92;
    if(args[0] == "23") {
      Console.Out.WriteLine("INHERITED-START"); Console.Out.Flush();
      Thread.Sleep(900);
      Console.Error.WriteLine("INHERITED-STDERR");
      Console.Out.WriteLine("INHERITED-END");
      return 23;
    }
    Thread.Sleep(700);
    Console.Out.Write(new string('O', 131072));
    Console.Error.Write(new string('E', 131072));
    Console.Out.Write("OUT-DONE-\u4e2d\u6587");
    Console.Error.Write("ERR-DONE-\u4e2d\u6587");
    return Int32.Parse(args[0]);
  }
}
'@, (New-Object Text.UTF8Encoding($false)))
  $compiler = Join-Path $env:SystemRoot 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
  if (!(Test-Path -LiteralPath $compiler)) { throw 'Official .NET Framework C# compiler unavailable' }
  & $compiler /nologo /target:winexe "/out:$exe" $source
  if ($LASTEXITCODE -ne 0) { throw 'Delayed GUI fixture compilation failed' }
  $bytes = [IO.File]::ReadAllBytes($exe)
  $pe = [BitConverter]::ToInt32($bytes, 0x3c)
  if ([BitConverter]::ToUInt16($bytes, $pe + 24 + 68) -ne 2) { throw 'Fixture is not GUI subsystem' }
  $savedExitCode = $global:LASTEXITCODE
  foreach ($code in @(0, 37)) {
    $global:LASTEXITCODE = 71 # Deliberately stale; helper must never use it.
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-PjNativeProcess -FilePath $exe -ArgumentValues @([string]$code, 'space value',
      ([string][char]0x4e2d + [char]0x6587), 'trailing\', 'quote"inside', '', '\"mixed')
    if ($result.ExitCode -ne $code) { throw "Wrong process exit: $($result.ExitCode), expected $code" }
    if ($watch.ElapsedMilliseconds -lt 600) { throw 'GUI process was not awaited' }
    $unicode = [string][char]0x4e2d + [char]0x6587
    if ($result.StandardOutput -ne (('O' * 131072) + 'OUT-DONE-' + $unicode)) { throw 'stdout truncated or corrupted' }
    if ($result.StandardError -ne (('E' * 131072) + 'ERR-DONE-' + $unicode)) { throw 'stderr truncated or corrupted' }
  }
  $result = Invoke-PjNativeProcess -FilePath $exe -ArgumentValues @('23', 'space value',
      ([string][char]0x4e2d + [char]0x6587), 'trailing\', 'quote"inside', '', '\"mixed') -InheritOutput
  if ($result.ExitCode -ne 23 -or $null -ne $result.StandardOutput -or $null -ne $result.StandardError) {
    throw 'Inherited-output mode failed or buffered the session'
  }
  $global:LASTEXITCODE = $savedExitCode
  Write-Output 'PASS: genuine delayed GUI executable, exact argv, both output streams, exit 0 and 37'
} finally { Remove-Item -LiteralPath $directory -Recurse -Force }
