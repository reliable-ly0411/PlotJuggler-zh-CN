# SPDX-License-Identifier: MPL-2.0
param([Parameter(Mandatory=$true)][string]$FixturePath)
$ErrorActionPreference = 'Stop'
$fixture = Get-Content -LiteralPath $FixturePath -Raw -Encoding UTF8 | ConvertFrom-Json
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
    $script:parentPath = "C:/My Folder/it's safe; & setup.exe"
    function Get-CimInstance {
        param($ClassName, $Filter)
        if ($Filter -eq ('ProcessId=' + $PID)) { return [pscustomobject]@{ ParentProcessId=4321 } }
        if ($Filter -ne 'ProcessId=4321') { throw 'Read unrelated PID' }
        return [pscustomobject]@{ ProcessId=4321; ExecutablePath=$script:parentPath; CommandLine=('"' + $script:parentPath + '" ' + $script:started[1]) }
    }
    $parsed = & ([ScriptBlock]::Create($fixture.probe)) | ConvertFrom-Json
    if ($parsed.pid -ne 4321 -or $parsed.argv -notcontains 'Extra=quote"value' -or
        $parsed.argv -notcontains 'http://user:pass@host/') { throw 'Native Windows argv roundtrip failed' }
    $script:parentPath = 'C:/unrelated.exe'
    try { & ([ScriptBlock]::Create($fixture.probe)); throw 'Identity mismatch accepted' }
    catch { if ($_.Exception.Message -notlike '*Parent identity mismatch*') { throw } }
    Write-Output 'PASS: Windows native argv and identity checks'
}
Write-Output 'PASS: PowerShell parsing and mocked restart, no GUI/process launched'
