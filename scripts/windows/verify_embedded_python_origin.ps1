# SPDX-License-Identifier: MPL-2.0
<#
  Independently authenticate the staged embedded Python before it is started.
  This runs from the trusted checkout on a disposable GitHub-hosted Windows
  runner, after the system bootstrap and before any executable from the kit.
  The official ZIP is not put into the kit or transferred to the user's VM.
#>
[CmdletBinding()]
param(
  [string]$KitRoot = '', [string]$SourceSha = '', [string]$SourceTree = '',
  [string]$ManifestSha256 = '', [string]$ArchiveSha256 = '',
  [string]$TrustedTemp = '', [string]$Output = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

function Assert-PlainDirectory([string]$Path) {
  $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw "Expected a real directory: $Path"
  }
  $streams = @(Get-Item -LiteralPath $Path -Stream '*' -ErrorAction Stop |
    Where-Object { $_.Stream -ne ':$DATA' -and $_.Stream -ne '::$DATA' })
  if ($streams.Count) { throw "Unexpected directory data stream: $Path" }
}

function Assert-PlainFile([string]$Path) {
  $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw "Expected a real file: $Path"
  }
  $streams = @(Get-Item -LiteralPath $Path -Stream '*' -ErrorAction Stop |
    Where-Object { $_.Stream -ne ':$DATA' -and $_.Stream -ne '::$DATA' })
  if ($streams.Count) { throw "Unexpected file data stream: $Path" }
  return $item
}

function Convert-HashBytes([byte[]]$Bytes) {
  return ([BitConverter]::ToString($Bytes) -replace '-', '').ToLowerInvariant()
}

function Get-StreamSha256([IO.Stream]$Stream) {
  $hash = [Security.Cryptography.SHA256]::Create()
  try { return Convert-HashBytes ($hash.ComputeHash($Stream)) } finally { $hash.Dispose() }
}

function Compare-EmbeddedPythonDistribution([string]$ZipPath, [string]$PythonDirectory) {
  # This helper is also exercised with a self-owned synthetic ZIP in CI. The
  # caller authenticates the real ZIP's fixed official SHA before invoking it.
  Assert-PlainDirectory $PythonDirectory
  $archive = [IO.Compression.ZipFile]::OpenRead($ZipPath)
  try {
    $required = @('python.exe', 'python3.dll', 'python312.dll', 'python312.zip', 'LICENSE.txt')
    $expected = @($archive.Entries | Where-Object {
      $_.FullName -in $required -or $_.FullName -cmatch '^[^/\\]+\.pyd$' -or
      $_.FullName -cmatch '^[^/\\]+\.dll$'
    })
    $entryNames = @($expected | ForEach-Object { $_.FullName.ToLowerInvariant() })
    if (@($entryNames | Select-Object -Unique).Count -ne $entryNames.Count) { throw 'Duplicate Python ZIP member' }
    foreach ($name in $required) {
      if (@($expected | Where-Object { $_.FullName -ceq $name }).Count -ne 1) { throw "Missing official Python member: $name" }
    }
    $files = @(Get-ChildItem -LiteralPath $PythonDirectory -Force)
    $normal = @($files | Where-Object { $_.Name -cne 'python312._pth' })
    if ($normal.Count -ne $expected.Count -or
        @($files | Where-Object { $_.Name -ceq 'python312._pth' }).Count -ne 1) {
      throw 'Staged Python member set differs from the official archive'
    }
    $records = @()
    foreach ($item in $files) {
      [void](Assert-PlainFile $item.FullName)
      if ($item.Name -ceq 'python312._pth') { continue } # strict content already verified by system bootstrap
      $matches = @($expected | Where-Object { $_.FullName -ceq $item.Name })
      if ($matches.Count -ne 1 -or $matches[0].Length -ne $item.Length) { throw "Unknown Python file: $($item.Name)" }
      $stream = $matches[0].Open()
      try { $official = Get-StreamSha256 $stream } finally { $stream.Dispose() }
      $actual = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
      if ($actual -cne $official) { throw "Python file differs from official ZIP: $($item.Name)" }
      $records += @{ path = 't/python/' + $item.Name; bytes = [long]$item.Length; sha256 = $actual }
    }
    return @($records | Sort-Object -Property path)
  } finally { $archive.Dispose() }
}

function Save-BoundedOfficialZip([string]$Url, [string]$Destination, [string]$ExpectedSha256) {
  if ($Url -cne 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -or
      $ExpectedSha256 -cne '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3') {
    throw 'Python origin is not the reviewed official version and digest'
  }
  Add-Type -AssemblyName System.Net.Http
  $handler = [Net.Http.HttpClientHandler]::new()
  $handler.UseDefaultCredentials = $false
  $client = [Net.Http.HttpClient]::new($handler)
  $client.Timeout = [TimeSpan]::FromMinutes(3)
  $response = $null; $reader = $null; $writer = $null
  try {
    $response = $client.GetAsync($Url, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    [void]$response.EnsureSuccessStatusCode()
    if ($response.RequestMessage.RequestUri.Scheme -cne 'https') { throw 'Python download ended on a non-HTTPS URL' }
    if ($null -ne $response.Content.Headers.ContentLength -and $response.Content.Headers.ContentLength -gt 64MB) {
      throw 'Python download exceeds the size limit'
    }
    $reader = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $writer = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $buffer = [byte[]]::new(1048576); [long]$size = 0
    while (($count = $reader.Read($buffer, 0, $buffer.Length)) -gt 0) {
      $size += $count
      if ($size -gt 64MB) { throw 'Python download exceeds the size limit' }
      $writer.Write($buffer, 0, $count)
    }
    $writer.Flush(); $writer.Dispose(); $writer = $null
    if ($size -le 0 -or (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256) {
      throw 'Python official ZIP bytes differ from the reviewed digest'
    }
    return $size
  } finally {
    if ($null -ne $writer) { $writer.Dispose() }
    if ($null -ne $reader) { $reader.Dispose() }
    if ($null -ne $response) { $response.Dispose() }
    $client.Dispose(); $handler.Dispose()
  }
}

# Dot-sourcing defines the comparison helper for synthetic Windows tests only.
if ($MyInvocation.InvocationName -eq '.') { return }
try {
  if ($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or
      $env:RUNNER_OS -cne 'Windows' -or $SourceSha -cnotmatch '^[0-9a-f]{40}$' -or
      $SourceTree -cnotmatch '^[0-9a-f]{40}$' -or $env:GITHUB_SHA -cne $SourceSha -or
      $ManifestSha256 -cnotmatch '^[0-9a-f]{64}$' -or $ArchiveSha256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'An exact source identity on disposable GitHub-hosted Windows is required'
  }
  $base = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a'
  $expectedRoot = Join-Path (Join-Path $base 'n') $SourceSha.Substring(0, 12)
  $expectedTemp = Join-Path (Join-Path $base 'bootstrap-temp') $SourceSha.Substring(0, 12)
  $expectedOutput = Join-Path (Join-Path (Join-Path $base 'receipts') $SourceSha.Substring(0, 12)) 'python-origin.json'
  if ($KitRoot -cne $expectedRoot -or $TrustedTemp -cne $expectedTemp -or $Output -cne $expectedOutput) {
    throw 'Python proof paths differ from the authenticated candidate root'
  }
  foreach ($directory in @($KitRoot, (Join-Path $KitRoot 't'), (Join-Path $KitRoot 't/python'),
                            (Join-Path $KitRoot '_bundle'), $TrustedTemp, (Split-Path -Parent $Output))) {
    Assert-PlainDirectory $directory
  }
  $manifestPath = Join-Path $KitRoot '_bundle/manifest.json'
  [void](Assert-PlainFile $manifestPath)
  if ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ManifestSha256) {
    throw 'The independently supplied manifest digest changed'
  }
  $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
  $pth = @( $manifest.files | Where-Object { $_.path -ceq 't/python/python312._pth' } )
  $pthFile = Join-Path $KitRoot 't/python/python312._pth'
  [void](Assert-PlainFile $pthFile)
  if ($pth.Count -ne 1 -or $pth[0].sha256 -cnotmatch '^[0-9a-f]{64}$' -or
      (Get-FileHash -LiteralPath $pthFile -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pth[0].sha256) {
    throw 'The bootstrap-verified isolated Python path file changed'
  }
  $pinsFile = Join-Path $env:GITHUB_WORKSPACE '.github/windows-native-kit/tool-pins.json'
  [void](Assert-PlainFile $pinsFile)
  $pins = Get-Content -LiteralPath $pinsFile -Raw | ConvertFrom-Json
  $python = @($pins.artifacts | Where-Object { $_.name -ceq 'python' })
  if ($pins.schema -ne 1 -or $python.Count -ne 1 -or $python[0].version -cne '3.12.10' -or
      $python[0].file -cne 'python-3.12.10-embed-amd64.zip') { throw 'The reviewed Python source pin differs' }
  $zip = Join-Path $TrustedTemp 'python-3.12.10-official.zip'
  $bytes = Save-BoundedOfficialZip $python[0].url $zip $python[0].sha256
  [void](Assert-PlainFile $zip)
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $members = @(Compare-EmbeddedPythonDistribution $zip (Join-Path $KitRoot 't/python'))
  $record = @{ schema = 1; scope = 'disposable-github-hosted-windows-ci'; source_sha = $SourceSha;
    source_tree = $SourceTree; archive_sha256 = $ArchiveSha256; manifest_sha256 = $ManifestSha256;
    official_url = $python[0].url; official_zip_sha256 = $python[0].sha256; official_zip_bytes = $bytes;
    pth_sha256 = $pth[0].sha256; members = $members }
  $contents = ($record | ConvertTo-Json -Depth 8) + "`n"
  $stream = [IO.File]::Open($Output, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
  try { $data = [Text.UTF8Encoding]::new($false).GetBytes($contents); $stream.Write($data, 0, $data.Length) }
  finally { $stream.Dispose() }
  Write-Output 'Official embedded Python bytes verified before kit execution.'
} catch {
  [Console]::Error.WriteLine('Embedded Python origin verification failed: ' + $_.Exception.Message)
  exit 1
}
