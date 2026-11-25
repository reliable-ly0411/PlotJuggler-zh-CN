# SPDX-License-Identifier: MPL-2.0
# Runs only for the explicitly confirmed GUI same-directory replacement.
# No cleanup on failure: a late old uninstaller must never race a new install.
param([string]$TargetPath, [switch]$FunctionsOnly)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Initialize-PJReplacementNative {
    if ('PJReplacementJob' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
public sealed class PJReplacementJob : IDisposable {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct Startup { public int cb; public string reserved, desktop, title; public int x,y,cx,cy,xc,yc,fill,flags; public short show,reserved2; public IntPtr reserved3,input,output,error; }
    [StructLayout(LayoutKind.Sequential)]
    struct ProcessInfo { public IntPtr process,thread; public uint pid,tid; }
    [StructLayout(LayoutKind.Sequential)]
    struct Accounting { public long user,kernel,periodUser,periodKernel; public uint faults,total,active,terminated; }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr attributes,string name);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder command,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref Startup startup,out ProcessInfo info);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int kind,out Accounting info,int length,IntPtr returned);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern uint GetLongPathName(string path,StringBuilder output,uint size);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateDirectory(string path,IntPtr attributes);
    public static void CreateScratch(string path) { if(!CreateDirectory(path,IntPtr.Zero)) throw new InvalidOperationException("temporary-create"); }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern uint GetFileAttributes(string path);
    public static bool PathAbsent(string path) {
        if(GetFileAttributes(path)!=UInt32.MaxValue) return false;
        int error=Marshal.GetLastWin32Error();
        if(error==2 || error==3) return true;
        throw new InvalidOperationException("residual-query");
    }
    IntPtr job, process;
    public void Start(string executable,string arguments,string temporary) { Start(executable,arguments,temporary,null); }
    public void Start(string executable,string arguments,string temporary,System.IO.FileStream frozen) {
        job=CreateJobObject(IntPtr.Zero,null);
        if(job==IntPtr.Zero) throw new InvalidOperationException("job-create");
        // No BREAKAWAY_OK / SILENT_BREAKAWAY_OK and no KILL_ON_JOB_CLOSE.
        // Assign while suspended: even a very short-lived cscript descendant
        // is contained before the maintenance tool executes any instruction.
        var environment=new SortedDictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        foreach(DictionaryEntry item in Environment.GetEnvironmentVariables()) environment[(string)item.Key]=(string)item.Value;
        environment["TEMP"]=temporary; environment["TMP"]=temporary;
        var block=new StringBuilder();
        foreach(var item in environment) block.Append(item.Key).Append('=').Append(item.Value).Append('\0');
        block.Append('\0');
        IntPtr memory=Marshal.StringToHGlobalUni(block.ToString());
        ProcessInfo info=new ProcessInfo(); bool resumed=false;
        try {
            var startup=new Startup(); startup.cb=Marshal.SizeOf(typeof(Startup));
            // CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW.
            if(!CreateProcess(executable,new StringBuilder("\""+executable+"\" "+arguments),IntPtr.Zero,IntPtr.Zero,false,0x08000404,memory,temporary,ref startup,out info)) throw new InvalidOperationException("purge-start");
            process=info.process;
            if(!AssignProcessToJobObject(job,process)) throw new InvalidOperationException("job-assign");
            // The image is already created and contained. Release the write/
            // delete-denying verification handle BEFORE allowing purge to run.
            if(frozen!=null) frozen.Dispose();
            if(ResumeThread(info.thread)==UInt32.MaxValue) throw new InvalidOperationException("purge-resume");
            resumed=true;
        } finally {
            Marshal.FreeHGlobal(memory);
            // Only terminate our NEVER-RESUMED owned child on setup failure.
            // Never terminate a running purge or an unrelated host process.
            if(info.thread!=IntPtr.Zero) CloseHandle(info.thread);
            if(!resumed && process!=IntPtr.Zero && WaitForSingleObject(process,0)!=0) {
                if(!TerminateProcess(process,1) || WaitForSingleObject(process,5000)!=0) throw new InvalidOperationException("suspended-cleanup");
            }
        }
    }
    public bool Exited() {
        uint result=WaitForSingleObject(process,0);
        if(result==0) return true;
        if(result==258) return false;
        throw new InvalidOperationException("purge-wait");
    }
    public uint ExitCode() { uint code; if(!GetExitCodeProcess(process,out code)) throw new InvalidOperationException("purge-exit"); return code; }
    public uint ActiveProcesses() {
        Accounting info;
        if(!QueryInformationJobObject(job,1,out info,Marshal.SizeOf(typeof(Accounting)),IntPtr.Zero)) throw new InvalidOperationException("job-query");
        return info.active;
    }
    public void Dispose() { if(process!=IntPtr.Zero) { CloseHandle(process); process=IntPtr.Zero; } if(job!=IntPtr.Zero) { CloseHandle(job); job=IntPtr.Zero; } }
}
'@
}

function Resolve-PJReplacementPath([string]$Path) {
    if (!$Path -or $Path -notmatch '^[A-Za-z]:[\\/]') { throw 'target-path' }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    if ($full -eq [IO.Path]::GetPathRoot($full).TrimEnd('\')) { throw 'target-root' }
    # Refuse junction/symlink traversal, including any existing ancestor.
    $cursor = $full
    while ($cursor) {
        $item = Get-Item -LiteralPath $cursor -Force -ErrorAction Stop
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'target-reparse' }
        $next = [IO.Path]::GetDirectoryName($cursor)
        if ($next -eq $cursor) { break }; $cursor = $next
    }
    $buffer = New-Object Text.StringBuilder 32768
    $length = [PJReplacementJob]::GetLongPathName($full, $buffer, 32768)
    if (!$length -or $length -ge 32768) { throw 'target-canonical' }
    return $buffer.ToString().TrimEnd('\')
}

function Get-PJReplacementRegistration([string]$Target, [string]$Tool) {
    $registrations = @()
    foreach ($hive in @([Microsoft.Win32.RegistryHive]::CurrentUser, [Microsoft.Win32.RegistryHive]::LocalMachine)) {
        # HKCU Software is shared across views; do not count the same key twice.
        $views = @([Microsoft.Win32.RegistryView]::Default)
        if ($hive -eq [Microsoft.Win32.RegistryHive]::LocalMachine -and [Environment]::Is64BitOperatingSystem) {
            $views = @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)
        }
        foreach ($view in $views) {
            $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $view)
            try {
                $root = $base.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall')
                if (!$root) { continue }
                try {
                    foreach ($name in $root.GetSubKeyNames()) {
                        $key = $root.OpenSubKey($name)
                        if (!$key) { throw 'registry-race' }
                        try {
                            $location = [string]$key.GetValue('InstallLocation')
                            if (!$location -or $location -notmatch '^[A-Za-z]:[\\/]') { continue }
                            # Only inspect a candidate whose normalized full location matches.
                            # Short aliases also resolve; unrelated missing locations are ignored.
                            try { $location = Resolve-PJReplacementPath $location } catch { continue }
                            if (![string]::Equals($location, $Target, [StringComparison]::OrdinalIgnoreCase)) { continue }
                            if ($name -notmatch '^\{[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\}$') { throw 'registry-uuid' }
                            $uninstall = [string]$key.GetValue('UninstallString')
                            # IFW 4.10 registerApplication(): quoted tool + scStartUninstallerLong.
                            # This registry entry launches its GUI; purge below is a separate CLI command.
                            if ($uninstall -notmatch '^"([^"]+)" --start-uninstaller$') { throw 'registry-command' }
                            $registeredTool = Resolve-PJReplacementPath $Matches[1]
                            if (![string]::Equals($registeredTool, $Tool, [StringComparison]::OrdinalIgnoreCase)) { throw 'registry-tool' }
                            $registrations += [pscustomobject]@{ Hive=$hive; View=$view; Name=$name; Target=$Target; Tool=$Tool }
                        } finally { $key.Dispose() }
                    }
                } finally { $root.Dispose() }
            } finally { $base.Dispose() }
        }
    }
    # No DisplayName guessing; ambiguous UUID/path registrations fail closed.
    if ($registrations.Count -ne 1) { throw 'registry-identity' }
    if ($registrations[0].Hive -ne [Microsoft.Win32.RegistryHive]::CurrentUser) { throw 'registry-system-install' }
    return $registrations[0]
}

function Test-PJReplacementRegistrationPresent($Registration) {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($Registration.Hive, $Registration.View)
    try {
        $key = $base.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $Registration.Name)
        if ($key) { $key.Dispose(); return $true }
        return $false
    } finally { $base.Dispose() }
}

function Start-PJReplacementPurge([string]$Tool, [string]$Temporary, [IO.FileStream]$Frozen) {
    $job = New-Object PJReplacementJob
    try {
        # Cache is outside the old target and exclusive to this invocation.
        $cache = Join-Path $Temporary 'cache'
        $job.Start($Tool, ('purge -c --cache-path "' + $cache + '"'), $Temporary, $Frozen)
        return $job
    } catch { $job.Dispose(); throw }
}

function Wait-PJReplacementPurge($Job, [int]$TimeoutMilliseconds = 120000) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    do {
        if ($Job.Exited()) {
            if ($Job.ExitCode() -ne 0) { throw 'purge-exit' }
            # The direct process exiting is NOT success: wait for all contained
            # descendants, including IFW's detached cscript uninstall.vbs.
            if ($Job.ActiveProcesses() -eq 0) { return }
        }
        if ($watch.ElapsedMilliseconds -ge $TimeoutMilliseconds) { throw 'purge-timeout' }
        Start-Sleep -Milliseconds 50
    } while ($true)
}

function Test-PJReplacementPathPresent([string]$Path) {
    # File.Exists/Test-Path can report false on inaccessible paths. Only native
    # FILE_NOT_FOUND/PATH_NOT_FOUND prove disappearance; every other error fails.
    return ![PJReplacementJob]::PathAbsent($Path)
}

function New-PJReplacementScratch([string]$Path) {
    # Atomic create, never adopt an existing random-name directory.
    [PJReplacementJob]::CreateScratch($Path)
}

function Invoke-PJReplacement([string]$Target) {
    $script:PJReplacementStage = 'identity'
    Initialize-PJReplacementNative
    $canonical = Resolve-PJReplacementPath $Target
    if (!(Get-Item -LiteralPath $canonical).PSIsContainer) { throw 'target-directory' }
    $tool = Resolve-PJReplacementPath (Join-Path $canonical 'maintenancetool.exe')
    $registration = Get-PJReplacementRegistration $canonical $tool
    # Freeze the executable against overwrite/delete until the verified exact
    # image has been created and assigned to its job. Never copy or replace it.
    $frozen = [IO.File]::Open($tool, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $job = $null
    try {
        $temporary = Join-Path ([IO.Path]::GetTempPath()) ('pj-replace-' + [guid]::NewGuid().ToString('N'))
        if (Test-Path -LiteralPath $temporary) { throw 'temporary-exists' }
        New-PJReplacementScratch $temporary
        $temporary = Resolve-PJReplacementPath $temporary
        if ($temporary.StartsWith($canonical + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'temporary-target' }
        # Revalidate the exact UUID mapping immediately before destructive launch.
        $again = Get-PJReplacementRegistration $canonical $tool
        if ($again.Hive -ne $registration.Hive -or $again.View -ne $registration.View -or $again.Name -ne $registration.Name) { throw 'registry-changed' }
        $script:PJReplacementStage = 'start'
        $job = Start-PJReplacementPurge $tool $temporary $frozen
        $frozen.Dispose(); $frozen = $null
        $script:PJReplacementStage = 'wait'
        Wait-PJReplacementPurge $job
        $script:PJReplacementStage = 'residual'
        if (Test-PJReplacementPathPresent $canonical) { throw 'target-residual' }
        if (Test-PJReplacementPathPresent $tool) { throw 'tool-residual' }
        if (Test-PJReplacementRegistrationPresent $registration) { throw 'registry-residual' }
        if (Test-PJReplacementPathPresent (Join-Path $temporary 'uninstall.vbs')) { throw 'cleanup-residual' }
        # Keep the isolated scratch/cache; never manually clear the old target.
    } finally {
        if ($frozen) { $frozen.Dispose() }
        if ($job) { $job.Dispose() }
    }
}

if (!$FunctionsOnly) {
    try { Invoke-PJReplacement $TargetPath; Write-Output 'PJ_REPLACEMENT_OK'; exit 0 }
    catch { Write-Output ('PJ_REPLACEMENT_FAILED:' + $script:PJReplacementStage); exit 1 }
}
