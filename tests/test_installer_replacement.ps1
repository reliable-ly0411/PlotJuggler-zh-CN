# SPDX-License-Identifier: MPL-2.0
param([string]$Root = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
$helper = Join-Path $Root 'packaging/installer/replacement_guard.ps1'
. $helper -FunctionsOnly
Initialize-PJReplacementNative # Compile the actual native binding even on Linux.
function Assert-Fails($Action, [string]$Expected) {
    try { & $Action; throw 'unexpected-success' }
    catch { if ($_.Exception.Message -notlike ('*' + $Expected + '*')) { throw } }
}
# IsPathRooted accepts drive-relative and root-relative paths on Windows;
# the guard must reject them before filesystem or native API access.
foreach ($ambiguous in @('', 'C:relative', '\root-relative', '/root-relative', '\\server\share', 'relative')) {
    Assert-Fails { Resolve-PJReplacementPath $ambiguous } 'target-path'
}
function New-FakeJob([int]$Code = 0, [int]$Active = 0, [bool]$Exited = $true) {
    $job = [pscustomobject]@{ Code=$Code; Active=$Active; Done=$Exited; Checks=0; Disposed=$false }
    $job | Add-Member ScriptMethod Exited { return $this.Done }
    $job | Add-Member ScriptMethod ExitCode { return $this.Code }
    $job | Add-Member ScriptMethod ActiveProcesses { $this.Checks++; return $this.Active }
    $job | Add-Member ScriptMethod Dispose { $this.Disposed=$true }
    return $job
}
$job = New-FakeJob
Wait-PJReplacementPurge $job 0
if ($job.Checks -ne 1) { throw 'Did not verify descendants' }
Assert-Fails { Wait-PJReplacementPurge (New-FakeJob -Code 1) 0 } 'purge-exit'
Assert-Fails { Wait-PJReplacementPurge (New-FakeJob -Active 1) 0 } 'purge-timeout'
Assert-Fails { Wait-PJReplacementPurge (New-FakeJob -Exited $false) 0 } 'purge-timeout'
$job = New-FakeJob -Active 1
$job | Add-Member ScriptMethod ActiveProcesses { $this.Checks++; if ($this.Checks -gt 1) { return 0 }; return 1 } -Force
Wait-PJReplacementPurge $job 1000
if ($job.Checks -ne 2) { throw 'Did not await asynchronous child' }

# Native tests launch only official PowerShell with temporary marker files.
# No installer, real installation deletion, or image-name kill. Registry
# checks below create and remove only new UUID keys owned by this test.
if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ('pj job test ' + [guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($temporary)
    if ([PJReplacementJob]::PathAbsent($temporary)) { throw 'Existing path reported absent' }
    if (![PJReplacementJob]::PathAbsent((Join-Path $temporary 'missing'))) { throw 'Missing path reported present' }
    $shell = Join-Path $PSHOME 'powershell.exe'
    $marker = Join-Path $temporary 'finished.txt'
    $release = Join-Path $temporary 'release-child'
    $child = "if (`$env:TEMP -ne '" + $temporary.Replace("'", "''") + "' -or `$env:TMP -ne '" + $temporary.Replace("'", "''") + "') { exit 2 }; `$deadline=[Diagnostics.Stopwatch]::StartNew(); while (![IO.File]::Exists('" + $release.Replace("'", "''") + "') -and `$deadline.ElapsedMilliseconds -lt 20000) { Start-Sleep -Milliseconds 25 }; if (![IO.File]::Exists('" + $release.Replace("'", "''") + "')) { exit 3 }; [IO.File]::WriteAllText('" + $marker.Replace("'", "''") + "','finished')"
    $childEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
    $parent = "Start-Process -FilePath '" + $shell.Replace("'", "''") + "' -NoNewWindow -ArgumentList '-NoProfile -NonInteractive -EncodedCommand " + $childEncoded + "'; exit 0"
    $parentEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($parent))
    $native = New-Object PJReplacementJob
    try {
        $native.Start($shell, ('-NoProfile -NonInteractive -EncodedCommand ' + $parentEncoded), $temporary)
        $deadline = [Diagnostics.Stopwatch]::StartNew()
        while (!$native.Exited() -and $deadline.ElapsedMilliseconds -lt 15000) { Start-Sleep -Milliseconds 25 }
        if (!$native.Exited() -or $native.ExitCode() -ne 0) { throw 'Native direct child failed' }
        if ($native.ActiveProcesses() -lt 1) { throw 'Detached child escaped job or test missed it' }
        [IO.File]::WriteAllText($release, 'release')
        Wait-PJReplacementPurge $native 15000
        if (!(Test-Path -LiteralPath $marker)) { throw 'Detached child did not complete naturally' }
    } finally { $native.Dispose() }
    $failed = New-Object PJReplacementJob
    try { Assert-Fails { $failed.Start((Join-Path $temporary 'missing.exe'), '', $temporary) } 'purge-start' }
    finally { $failed.Dispose() }

    # Force only the Assign failure branch in a separate copy of the native
    # binding. Prove its never-resumed child is gone; never run an uncontained
    # process to recover from assignment failure.
    $source = Get-Content -LiteralPath $helper -Raw -Encoding UTF8
    $nativeSource = [regex]::Match($source, "(?s)Add-Type -TypeDefinition @'\r?\n(.*?)\r?\n'@").Groups[1].Value
    $nativeSource = $nativeSource.Replace('PJReplacementJob :', 'PJReplacementJobAssignFailure :').Replace('IntPtr job, process;', 'public static uint LastPid; IntPtr job, process;').Replace('process=info.process;', 'process=info.process; LastPid=info.pid;').Replace('if(!AssignProcessToJobObject(job,process))', 'if(Boolean.Parse("true"))')
    Add-Type -TypeDefinition $nativeSource
    $failed = New-Object PJReplacementJobAssignFailure
    try { Assert-Fails { $failed.Start($shell, '-NoProfile -NonInteractive -Command "exit 0"', $temporary) } 'job-assign' }
    finally { $failed.Dispose() }
    if (Get-Process -Id ([PJReplacementJobAssignFailure]::LastPid) -ErrorAction SilentlyContinue) { throw 'Never-resumed child leaked' }
    # Real canonical-path/UUID registry lookup against two exclusively owned
    # keys. Never locate a product by DisplayName or mutate a pre-existing key.
    $identityTarget = Join-Path $temporary 'registered target'
    [void][IO.Directory]::CreateDirectory($identityTarget)
    $identityTool = Join-Path $identityTarget 'maintenancetool.exe'
    [IO.File]::WriteAllText($identityTool, 'not executable; never launched')
    $identityTarget = Resolve-PJReplacementPath $identityTarget
    $identityTool = Resolve-PJReplacementPath $identityTool
    $base = [Microsoft.Win32.Registry]::CurrentUser
    $prefix = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\'
    $names = @(('{' + [guid]::NewGuid().ToString() + '}'), ('{' + [guid]::NewGuid().ToString() + '}'))
    $created = @()
    try {
        foreach ($name in $names) {
            if ($base.OpenSubKey($prefix + $name)) { throw 'Test UUID already exists' }
        }
        $key = $base.CreateSubKey($prefix + $names[0]); $created += $names[0]
        try { $key.SetValue('InstallLocation', $identityTarget); $key.SetValue('UninstallString', ('"' + $identityTool + '" --uninstall')) }
        finally { $key.Dispose() }
        $registration = Get-PJReplacementRegistration $identityTarget $identityTool
        if ($registration.Name -ne $names[0] -or !(Test-PJReplacementRegistrationPresent $registration)) { throw 'Exact UUID not found' }
        $key = $base.CreateSubKey($prefix + $names[1]); $created += $names[1]
        try { $key.SetValue('InstallLocation', $identityTarget); $key.SetValue('UninstallString', ('"' + $identityTool + '" --uninstall')) }
        finally { $key.Dispose() }
        Assert-Fails { Get-PJReplacementRegistration $identityTarget $identityTool } 'registry-identity'
        $base.DeleteSubKey($prefix + $names[1]); $created = @($names[0])
        $key = $base.OpenSubKey($prefix + $names[0], $true)
        try { $key.SetValue('UninstallString', 'unexpected-command') } finally { $key.Dispose() }
        Assert-Fails { Get-PJReplacementRegistration $identityTarget $identityTool } 'registry-command'
    } finally { foreach ($name in $created) { $base.DeleteSubKey($prefix + $name) } }
    if (Test-PJReplacementRegistrationPresent $registration) { throw 'Exact deleted UUID still present' }
    # Only test-owned marker and scratch are removed, after all descendants exit.
    Remove-Item -LiteralPath $temporary -Recurse -Force
    Write-Output 'PASS: native contained detached child, never-resumed cleanup and exact UUID identity'
}
# Exercise the full orchestration using only fresh test-owned files. Native
# identity/process boundaries above are replaced here, not the residual gates.
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('pj replacement test ' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($testRoot)
$script:scratch = @()
function Initialize-PJReplacementNative {}
function Test-PJReplacementPathPresent([string]$Path) { return Test-Path -LiteralPath $Path }
function New-PJReplacementScratch([string]$Path) { [void][IO.Directory]::CreateDirectory($Path) }
function Resolve-PJReplacementPath([string]$Path) { return [IO.Path]::GetFullPath($Path) }
function Get-PJReplacementRegistration($Target, $Tool) {
    if ($script:scenario -eq 'identity') { throw 'registry-identity' }
    return [pscustomobject]@{Hive='CurrentUser'; View='Default'; Name='{test-only}'; Target=$Target; Tool=$Tool}
}
function Start-PJReplacementPurge($Tool, $Temporary) {
    $script:scratch += $Temporary
    $script:starts++
    if ($script:scenario -eq 'start') { throw 'purge-start' }
    $script:lastJob = New-FakeJob
    if ($script:scenario -eq 'script') { [IO.File]::WriteAllText((Join-Path $Temporary 'uninstall.vbs'), 'test-only') }
    return $script:lastJob
}
function Wait-PJReplacementPurge($Job) {
    if ($script:scenario -eq 'wait') { throw 'purge-timeout' }
    if ($script:scenario -ne 'target') {
        # Emulate a successful uninstaller only on our new test fixture.
        Remove-Item -LiteralPath $script:oldTarget -Recurse -Force
    }
}
function Test-PJReplacementRegistrationPresent($Registration) { return $script:scenario -eq 'registry' }
try {
    foreach ($case in @('identity', 'start', 'wait', 'target', 'registry', 'script', 'success')) {
        $script:scenario=$case; $script:starts=0; $script:lastJob=$null
        $script:oldTarget=Join-Path $testRoot $case
        [void][IO.Directory]::CreateDirectory($script:oldTarget)
        [IO.File]::WriteAllText((Join-Path $script:oldTarget 'maintenancetool.exe'), 'not executable; never launched')
        $expected=@{identity='registry-identity'; start='purge-start'; wait='purge-timeout'; target='target-residual'; registry='registry-residual'; script='cleanup-residual'}
        if ($case -eq 'success') { Invoke-PJReplacement $script:oldTarget }
        else { Assert-Fails { Invoke-PJReplacement $script:oldTarget } $expected[$case] }
        if ($script:starts -ne [int]($case -ne 'identity')) { throw 'Unexpected retry or identity bypass' }
        if ($script:lastJob -and !$script:lastJob.Disposed) { throw 'Job handle leaked' }
    }
} finally {
    # These are solely the fresh test fixture and isolated helper scratch.
    Remove-Item -LiteralPath $testRoot -Recurse -Force
    foreach ($directory in $script:scratch) { Remove-Item -LiteralPath $directory -Recurse -Force }
}
Write-Output 'PASS: full replacement orchestration rejects identity/start/timeout/target/registry/script failures'
Write-Output 'PASS: replacement exit, timeout, asynchronous descendants and native binding compile'
