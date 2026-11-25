# SPDX-License-Identifier: MPL-2.0
# Fetch the official, pinned IFW tools. No installer wizard or elevation runs.
param(
  [string]$Destination = (Join-Path $PSScriptRoot '../../.qt/Tools/QtInstallerFramework/4.10.0-pinned')
)
$ErrorActionPreference = 'Stop'
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path $destinationPath) {
  throw "Refusing to replace existing IFW directory: $destinationPath. Choose an empty destination."
}
$parent = Split-Path $destinationPath -Parent
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$scratch = Join-Path $parent ('.ifw-download-' + [Guid]::NewGuid().ToString('N'))
$archive = Join-Path $scratch 'ifw-4.10.0-win-x64.7z'
$payload = Join-Path $scratch 'payload'
$url = 'https://download.qt.io/online/qtsdkrepository/windows_x86/ifw/tools_ifw_410/qt.tools.ifw.410/4.10.0-0-202506090530ifw-win-x64.7z'
$expected = 'bf460f2f60b858d9bfb6c709fc4687fd6967856984bd730711df2c4df9dd49f2'
try {
  $extractor = Get-Command '7z' -ErrorAction Stop
  New-Item -ItemType Directory -Path $scratch, $payload | Out-Null
  Invoke-WebRequest -Uri $url -OutFile $archive -ErrorAction Stop
  if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'Qt IFW archive SHA-256 mismatch. The tools were not extracted or executed.'
  }
  & $extractor.Source x $archive "-o$payload" -y | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Qt IFW extraction failed: $LASTEXITCODE" }
  foreach ($tool in @('binarycreator.exe', 'installerbase.exe', 'repogen.exe')) {
    if (-not (Test-Path (Join-Path $payload "bin/$tool"))) { throw "Missing IFW tool: $tool" }
  }
  $installerbase = Join-Path $payload 'bin/installerbase.exe'
  $runtime = (& $installerbase --version 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0 -or $runtime -notmatch 'IFW Version: 4\.10\.0, built with Qt ') {
    throw "Unexpected Qt IFW runtime: $runtime"
  }
  Move-Item -LiteralPath $payload -Destination $destinationPath
  Write-Output (Join-Path $destinationPath 'bin')
} finally {
  if (Test-Path $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
}
