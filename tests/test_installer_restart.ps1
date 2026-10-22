# SPDX-License-Identifier: MPL-2.0
param([Parameter(Mandatory=$true)][string]$FixturePath)
$ErrorActionPreference = 'Stop'
$fixture = Get-Content -LiteralPath $FixturePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($name in @('probe', 'command')) {
    $encoded = $fixture.($name + 'Transport')
    # Apply IFW's @...@ substitution before decoding the actual transport.
    $adjusted = [regex]::Replace($encoded, '@[^@]*@', '')
    $decoded = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($adjusted))
    if ($decoded -cne $fixture.$name) { throw 'IFW damaged encoded PowerShell transport' }
}
# Negative control for the actual bug: raw @() ... @{} is consumed as an
# unknown IFW variable. PowerShell can still exit successfully, without JSON.
$fragment = '$argv = @(); $argv += "setup.exe"; $json = @{ pid=4321; argv=$argv } | ConvertTo-Json -Compress -Depth 4; [string]$json'
$good = & ([ScriptBlock]::Create($fragment)) | ConvertFrom-Json
if ($good.pid -ne 4321 -or $good.argv[0] -ne 'setup.exe') { throw 'Probe fragment positive control failed' }
$corrupted = [regex]::Replace($fragment, '@[^@]*@', '')
$bad = & { $WarningPreference = 'SilentlyContinue'; & ([ScriptBlock]::Create($corrupted)) }
if (![string]::IsNullOrWhiteSpace($bad)) { throw 'Raw IFW transport negative control failed' }
Write-Output 'PASS: raw IFW substitution loses JSON; encoded transport preserves both scripts'
foreach ($source in @($fixture.probe, $fixture.command)) {
    $tokens = $null; $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
}
function Wait-Process {}
function Get-Process { return $null }
$script:started = $null
function Start-Process { param($FilePath, $ArgumentList) $script:started = @($FilePath, $ArgumentList) }
& ([ScriptBlock]::Create($fixture.command))
if ($script:started.Count -ne 2 -or $script:started[1] -notlike '*"TargetDir=C:/chosen folder/*') {
    throw 'Restart did not preserve the selected directory'
}
if ($script:started[1] -notlike '*"--proxy" "http://user:pass@host/"*') { throw 'Proxy arguments lost' }
if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
    # Real files are required by the production identity check. Never launch them.
    $testDirectory = Join-Path ([IO.Path]::GetTempPath()) ('pj identity space ' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $testDirectory | Out-Null
    $script:parentPath = Join-Path $testDirectory "it's safe; & setup.exe"
    New-Item -ItemType File -Path $script:parentPath | Out-Null
    $realProbe = $fixture.probe.Replace("C:/My Folder/it''s safe; & setup.exe", $script:parentPath.Replace("'", "''"))
    try {
    # Each production probe is a fresh powershell.exe. Tests repeat in one PS5
    # process, where Add-Type otherwise rejects the already compiled type.
    function Add-Type {
        param($TypeDefinition)
        if ($TypeDefinition -like '*class PJInstallerArgv*' -and ('PJInstallerArgv' -as [type])) { return }
        Microsoft.PowerShell.Utility\Add-Type -TypeDefinition $TypeDefinition
    }
    function Get-CimInstance {
        param($ClassName, $Filter)
        if ($Filter -eq ('ProcessId=' + $PID)) { return [pscustomobject]@{ ParentProcessId=4321 } }
        if ($Filter -ne 'ProcessId=4321') { throw 'Read unrelated PID' }
        return [pscustomobject]@{ ProcessId=4321; ExecutablePath=$script:parentPath; CommandLine=('"' + $script:parentPath + '" ' + $script:started[1]) }
    }
    $parsed = & ([ScriptBlock]::Create($realProbe)) | ConvertFrom-Json
    if ($parsed.pid -ne 4321 -or $parsed.argv -notcontains 'Extra=quote"value' -or
        $parsed.argv -notcontains 'http://user:pass@host/') { throw 'Native Windows argv roundtrip failed' }
    Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class PJShortPathTest { [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern uint GetShortPathName(string path, System.Text.StringBuilder result, uint size); }'
    $short = New-Object Text.StringBuilder 32768
    $length = [PJShortPathTest]::GetShortPathName($script:parentPath, $short, 32768)
    if (!$length -or $length -ge 32768) { throw 'Could not query native short path for identity regression' }
    $script:parentPath = $short.ToString()
    $parsed = & ([ScriptBlock]::Create($realProbe)) | ConvertFrom-Json
    if ($parsed.pid -ne 4321) { throw 'Short/long executable identity failed' }
    if ($script:parentPath -notmatch '~') { Write-Output 'NOTE: filesystem supplied no distinct 8.3 alias; long-path identity still checked' }
    $script:parentPath = Join-Path $testDirectory 'unrelated.exe'
    New-Item -ItemType File -Path $script:parentPath | Out-Null
    try { & ([ScriptBlock]::Create($realProbe)); throw 'Identity mismatch accepted' }
    catch { if ($_.Exception.Message -notlike '*Parent identity mismatch*') { throw } }
    Remove-Item -LiteralPath $script:parentPath
    try { & ([ScriptBlock]::Create($realProbe)); throw 'Missing executable path accepted' }
    catch { if ($_.Exception.Message -notlike '*Parent identity mismatch*') { throw } }
    Write-Output 'PASS: Windows native argv, short/long path identity and fail-closed checks'
    } finally { Remove-Item -LiteralPath $testDirectory -Recurse -Force }
}
Write-Output 'PASS: PowerShell parsing and mocked restart, no GUI/process launched'
