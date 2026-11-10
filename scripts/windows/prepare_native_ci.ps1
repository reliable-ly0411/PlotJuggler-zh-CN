# SPDX-License-Identifier: MPL-2.0
# Compile, stage and independently verify a test-only kit on disposable CI.
[CmdletBinding()]
param(
  [ValidateSet('Build', 'Verify', 'BootstrapSelfTest')][string]$Phase = 'Build',
  [string]$Archive = '', [string]$ArchiveSha256 = '', [string]$ManifestSha256 = '',
  [string]$SourceSha = '', [string]$SourceTree = '', [long]$ExpandedBytes = 0, [switch]$RetainBuild
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

# Do not let hosted-runner inherited paths direct optional screenshot writes
# outside this job's owned tree. The feedback path is set explicitly below.
foreach ($name in @('PJ_GUI_ACCEPTANCE_DIR', 'PJ_UI_TEST_DUMP_DIR')) {
  [Environment]::SetEnvironmentVariable($name, $null, 'Process')
}

function Invoke-Checked([string]$Exe, [string[]]$Arguments = @()) {
  & $Exe @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" }
}

function Invoke-RecordedBuildProcess([string]$PhaseName, [string]$Executable, [string[]]$Arguments,
                                     [string]$WorkingDirectory, [string]$EvidenceDirectory,
                                     [string]$Kind, [string]$GraphPath = '') {
  if ($PhaseName -notmatch '^(remotes|install|configure|build)$' -or $Kind -notin @('conan', 'cmake')) {
    throw 'Unexpected recorded build process.'
  }
  Assert-RealDirectory $WorkingDirectory
  Assert-RealDirectory $EvidenceDirectory
  $stdout = Join-Path $EvidenceDirectory ($PhaseName + '.stdout.bin')
  $stderr = Join-Path $EvidenceDirectory ($PhaseName + '.stderr.bin')
  $receipt = Join-Path $EvidenceDirectory ($PhaseName + '.process.json')
  foreach ($path in @($stdout, $stderr, $receipt)) {
    if (Test-Path -LiteralPath $path) { throw 'Refusing to reuse recorded process evidence.' }
  }
  $beforeTool = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant()
  $beforeNinja = if ($Kind -eq 'cmake') { (Get-FileHash -LiteralPath $ninja -Algorithm SHA256).Hash.ToLowerInvariant() } else { '' }
  $beforeLock = (Get-FileHash -LiteralPath (Join-Path $source 'conan.lock') -Algorithm SHA256).Hash.ToLowerInvariant()
  # The fixed same-root paths do not need complex Windows command-line quoting.
  $nativeArguments = @($Arguments | ForEach-Object {
    if ($_ -match '[\s"]') {
      if ($_ -match '"|\\$') { throw 'Unexpected recorded argument requiring complex quoting.' }
      '"' + $_ + '"'
    } else { $_ }
  })
  $process = Start-Process -FilePath $Executable -ArgumentList $nativeArguments -WorkingDirectory $WorkingDirectory `
    -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $record = @{ schema = 1; argv = @($Executable) + $Arguments; cwd = $WorkingDirectory;
    exit_code = $process.ExitCode; still_running = $false; source_sha = $sha; source_tree = $sourceTree;
    lock_sha256 = $beforeLock; stdout_sha256 = (Get-FileHash -LiteralPath $stdout -Algorithm SHA256).Hash.ToLowerInvariant();
    stderr_sha256 = (Get-FileHash -LiteralPath $stderr -Algorithm SHA256).Hash.ToLowerInvariant() }
  if ($Kind -eq 'conan') { $record.conan_sha256 = $beforeTool }
  else {
    $record.cmake_sha256 = $beforeTool
    $record.ninja_sha256 = $beforeNinja
  }
  if ($GraphPath -and (Test-Path -LiteralPath $GraphPath -PathType Leaf)) {
    $record.graph_sha256 = (Get-FileHash -LiteralPath $GraphPath -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  $stream = [IO.File]::Open($receipt, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
  try {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($record | ConvertTo-Json -Depth 8))
    $stream.Write($bytes, 0, $bytes.Length)
  } finally { $stream.Dispose() }
  if ($process.ExitCode -ne 0) { throw "$PhaseName failed with exit code $($process.ExitCode); raw evidence retained." }
  if ((Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant() -cne $beforeTool -or
      (Get-FileHash -LiteralPath (Join-Path $source 'conan.lock') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $beforeLock -or
      ($Kind -eq 'cmake' -and (Get-FileHash -LiteralPath $ninja -Algorithm SHA256).Hash.ToLowerInvariant() -cne $beforeNinja)) {
    throw 'The recorded process executable, Ninja or source lock changed during execution.'
  }
  if ($GraphPath -and -not (Test-Path -LiteralPath $GraphPath -PathType Leaf)) {
    throw 'Conan install completed without its installed graph.'
  }
}

function Assert-RealDirectory([string]$Path) {
  $item = Get-Item -LiteralPath $Path -Force
  if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw "Expected a real directory, not a reparse point: $Path"
  }
}

function Assert-RealTree([string]$Path) {
  Assert-RealDirectory $Path
  $bad = Get-ChildItem -LiteralPath $Path -Force -Recurse |
    Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } |
    Select-Object -First 1
  if ($bad) { throw "Reparse point in native build tree: $($bad.FullName)" }
}

function Initialize-IsolatedGitEnvironment([string]$ControlDirectory) {
  # Do not print inherited variables: some may contain secrets. Preserve
  # GITHUB_* while removing every inherited Git redirect, config and hook.
  foreach ($item in @(Get-ChildItem Env:)) {
    if ($item.Name -match '^GIT_') { Remove-Item -LiteralPath ('Env:' + $item.Name) -ErrorAction Stop }
  }
  Assert-RealDirectory (Split-Path -Parent $ControlDirectory)
  if (Test-Path -LiteralPath $ControlDirectory) { throw 'Refusing to reuse Git isolation controls.' }
  New-Item -ItemType Directory -Path $ControlDirectory | Out-Null
  $template = Join-Path $ControlDirectory 'template'
  $hooks = Join-Path $ControlDirectory 'hooks'
  New-Item -ItemType Directory -Path $template, $hooks | Out-Null
  foreach ($directory in @($ControlDirectory, $template, $hooks)) { Assert-RealDirectory $directory }
  $env:GIT_CONFIG_NOSYSTEM = '1'
  $env:GIT_CONFIG_GLOBAL = 'NUL'
  $env:GIT_ATTR_NOSYSTEM = '1'
  $env:GIT_TERMINAL_PROMPT = '0'
  $env:GIT_TEMPLATE_DIR = $template
  $env:GIT_CONFIG_COUNT = '2'
  $env:GIT_CONFIG_KEY_0 = 'core.fsmonitor'
  $env:GIT_CONFIG_VALUE_0 = 'false'
  $env:GIT_CONFIG_KEY_1 = 'core.hooksPath'
  $env:GIT_CONFIG_VALUE_1 = $hooks
}

function Initialize-DirectoryIdentityType {
  if ('PjCiDirectoryIdentity' -as [type]) { return }
  # Compile only trusted caller code, before reading any artifact executable.
  Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class PjCiDirectoryIdentity {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern SafeFileHandle CreateFileW(string p, uint access, uint share, IntPtr sec, uint mode, uint flags, IntPtr template);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern uint GetFinalPathNameByHandleW(SafeFileHandle h, StringBuilder p, uint n, uint flags);
  public static bool Exact(string path) {
    using (var h = CreateFileW(path, 0, 7, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero)) {
      if (h.IsInvalid) return false;
      var b = new StringBuilder(32768); uint n = GetFinalPathNameByHandleW(h, b, (uint)b.Capacity, 0);
      return n > 0 && n < b.Capacity && String.Equals(b.ToString(), @"\\?\" + Path.GetFullPath(path), StringComparison.OrdinalIgnoreCase);
    }
  }
}
'@ -ErrorAction Stop
}

function Assert-TrustedDirectory([string]$Path) {
  Assert-RealDirectory $Path
  if (-not [PjCiDirectoryIdentity]::Exact($Path)) { throw "Directory has an alias or unexpected final path: $Path" }
  $named = @(Get-Item -LiteralPath $Path -Stream '*' -ErrorAction Stop | Where-Object { $_.Stream -ne ':$DATA' -and $_.Stream -ne '::$DATA' })
  if ($named.Count) { throw "Directory has a named data stream: $Path" }
}

function Invoke-BootstrapSelfTest {
  # Exercise the verifier's real .NET ZIP/NTFS adversarial suite and its
  # fixed-root first-run/reuse negative control on this disposable host only.
  if ($env:GITHUB_SHA -cnotmatch '^[0-9a-f]{40}$') { throw 'Bootstrap self-test source SHA is invalid.' }
  $trustedHead = @(& git.exe -C $env:GITHUB_WORKSPACE rev-parse HEAD)
  if ($LASTEXITCODE -ne 0 -or $trustedHead.Count -ne 1 -or $trustedHead[0].Trim() -cne $env:GITHUB_SHA) {
    throw 'Bootstrap self-tests require the exact trusted checkout.'
  }
  $trustedTree = @(& git.exe -C $env:GITHUB_WORKSPACE rev-parse 'HEAD^{tree}')
  if ($LASTEXITCODE -ne 0 -or $trustedTree.Count -ne 1 -or $trustedTree[0].Trim() -cnotmatch '^[0-9a-f]{40}$') {
    throw 'Cannot establish the bootstrap self-test source tree.'
  }
  $trustedStatus = @(& git.exe -C $env:GITHUB_WORKSPACE status --porcelain=v1 --untracked-files=all --ignore-submodules=none)
  if ($LASTEXITCODE -ne 0 -or $trustedStatus.Count -ne 0) { throw 'Bootstrap self-test checkout is not clean.' }
  foreach ($relative in @('tests/test_windows_native_bootstrap.py', 'scripts/windows/bootstrap_native_test_kit.ps1',
                           'tests/test_windows_native_python_origin.py', 'scripts/windows/verify_embedded_python_origin.ps1')) {
    $tracked = @(& git.exe -C $env:GITHUB_WORKSPACE ls-files --error-unmatch -- $relative)
    if ($LASTEXITCODE -ne 0 -or $tracked.Count -ne 1 -or $tracked[0].Trim() -cne $relative) {
      throw 'Bootstrap self-test code must be tracked in the trusted checkout.'
    }
  }
  Initialize-DirectoryIdentityType
  $synthetic = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N').Substring(0, 8)
  $prefix = $synthetic.Substring(0, 12)
  $parent = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a'
  $temp = Join-Path (Join-Path $parent 'bootstrap-temp') $prefix
  $target = Join-Path (Join-Path $parent 'n') $prefix
  if ((Test-Path -LiteralPath $temp) -or (Test-Path -LiteralPath $target)) { throw 'Synthetic bootstrap paths already exist.' }
  foreach ($path in @('C:\', 'C:\Users', 'C:\Users\Administrator', $parent,
                      (Join-Path $parent 'n'), (Join-Path $parent 'bootstrap-temp'), $temp)) {
    if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
    Assert-TrustedDirectory $path
  }
  if (@(Get-ChildItem -LiteralPath $temp -Force).Count -ne 0) { throw 'Synthetic bootstrap temp is not fresh.' }
  $evidence = Join-Path $env:RUNNER_TEMP ('pj-bootstrap-selftest-' + $prefix)
  if (Test-Path -LiteralPath $evidence) { throw 'Synthetic bootstrap evidence already exists.' }
  New-Item -ItemType Directory -Path $evidence | Out-Null
  Assert-RealDirectory $evidence
  $python = (Get-Command python.exe -CommandType Application).Source
  $testArgs = @('-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_windows_native_bootstrap.py', '-v')
  $stdout = Join-Path $evidence 'stdout.bin'
  $stderr = Join-Path $evidence 'stderr.bin'
  $env:PJ_ALLOW_BOOTSTRAP_INTEGRATION = '1'
  $env:PJ_BOOTSTRAP_TEST_SOURCE_SHA = $synthetic
  $process = Start-Process -FilePath $python -ArgumentList $testArgs -WorkingDirectory $env:GITHUB_WORKSPACE -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $log = [IO.File]::ReadAllText($stderr)
  if ($process.ExitCode -ne 0 -or $log -notmatch '(?m)test_actual_embedded_verifier_rejects_malformed_cases[^\r\n]*\.\.\. ok' -or
      $log -notmatch '(?m)test_full_fixed_root_and_refuse_reuse[^\r\n]*\.\.\. ok') {
    throw 'Real bootstrap ZIP/NTFS or fixed-root/reuse negative controls did not complete.'
  }
  $test = Join-Path $env:GITHUB_WORKSPACE 'tests/test_windows_native_bootstrap.py'
  $script = Join-Path $env:GITHUB_WORKSPACE 'scripts/windows/bootstrap_native_test_kit.ps1'
  $record = @{ schema = 1; scope = 'disposable-windows-ci-only'; source_sha = $env:GITHUB_SHA;
    synthetic_sha = $synthetic; executable = $python; argv = @($python) + $testArgs; cwd = $env:GITHUB_WORKSPACE;
    exit_code = $process.ExitCode; test_sha256 = (Get-FileHash -LiteralPath $test -Algorithm SHA256).Hash.ToLowerInvariant();
    bootstrap_sha256 = (Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant();
    stdout_sha256 = (Get-FileHash -LiteralPath $stdout -Algorithm SHA256).Hash.ToLowerInvariant();
    stderr_sha256 = (Get-FileHash -LiteralPath $stderr -Algorithm SHA256).Hash.ToLowerInvariant() }
  [IO.File]::WriteAllText((Join-Path $evidence 'process.json'), ($record | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))

  # The official-Python pre-execution verifier must itself pass real .NET ZIP
  # positive and adversarial controls on Windows before any build or kit run.
  $originTest = Join-Path $env:GITHUB_WORKSPACE 'tests/test_windows_native_python_origin.py'
  $originScript = Join-Path $env:GITHUB_WORKSPACE 'scripts/windows/verify_embedded_python_origin.ps1'
  foreach ($path in @($originTest, $originScript)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Python origin self-test source is missing.' }
  }
  $originArgs = @('-I', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_windows_native_python_origin.py', '-v')
  $originStdout = Join-Path $evidence 'python-origin.stdout.bin'
  $originStderr = Join-Path $evidence 'python-origin.stderr.bin'
  $originPythonHash = (Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant()
  $originProcess = Start-Process -FilePath $python -ArgumentList $originArgs -WorkingDirectory $env:GITHUB_WORKSPACE `
    -NoNewWindow -Wait -PassThru -RedirectStandardOutput $originStdout -RedirectStandardError $originStderr
  $originRecord = @{ schema = 1; scope = 'disposable-windows-ci-only'; source_sha = $env:GITHUB_SHA;
    source_tree = $trustedTree[0].Trim(); synthetic_sha = $synthetic; executable = $python;
    executable_sha256 = $originPythonHash;
    argv = @($python) + $originArgs; cwd = $env:GITHUB_WORKSPACE; exit_code = $originProcess.ExitCode;
    test_sha256 = (Get-FileHash -LiteralPath $originTest -Algorithm SHA256).Hash.ToLowerInvariant();
    bootstrap_sha256 = (Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant();
    python_origin_script_sha256 = (Get-FileHash -LiteralPath $originScript -Algorithm SHA256).Hash.ToLowerInvariant();
    stdout_sha256 = (Get-FileHash -LiteralPath $originStdout -Algorithm SHA256).Hash.ToLowerInvariant();
    stderr_sha256 = (Get-FileHash -LiteralPath $originStderr -Algorithm SHA256).Hash.ToLowerInvariant() }
  [IO.File]::WriteAllText((Join-Path $evidence 'python-origin.process.json'),
    ($originRecord | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
  $originLog = [IO.File]::ReadAllText($originStderr)
  if ($originProcess.ExitCode -ne 0 -or
      (Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant() -cne $originPythonHash -or
      $originLog -notmatch '(?m)test_actual_dotnet_compare_accepts_exact_zip_and_rejects_tampering[^\r\n]*\.\.\. ok') {
    throw 'Real Python-origin ZIP comparison and adversarial controls did not complete.'
  }
  if (-not $env:GITHUB_OUTPUT) { throw 'GitHub step output destination is missing.' }
  [IO.File]::AppendAllText($env:GITHUB_OUTPUT, "evidence_dir=$evidence`n", [Text.UTF8Encoding]::new($false))
}

function Invoke-CleanVerification {
  if ($ArchiveSha256 -cnotmatch '^[0-9a-f]{64}$' -or $ManifestSha256 -cnotmatch '^[0-9a-f]{64}$' -or
      $SourceSha -cnotmatch '^[0-9a-f]{40}$' -or $SourceTree -cnotmatch '^[0-9a-f]{40}$' -or
      $env:PJ_MEDIA_MANIFEST_SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
      $env:PJ_MEDIA_SOURCE_SHA -cne $SourceSha -or $env:PJ_MEDIA_SOURCE_TREE -cne $SourceTree -or
      $SourceSha -cne $env:GITHUB_SHA -or $ExpandedBytes -le 0 -or $ExpandedBytes -gt 32GB) {
    throw 'Independent archive, manifest, measured expanded size and source identities are required.'
  }
  $head = @(& git.exe -C $env:GITHUB_WORKSPACE rev-parse HEAD)
  if ($LASTEXITCODE -ne 0 -or $head.Count -ne 1) { throw 'Cannot verify the trusted checkout commit.' }
  $tree = @(& git.exe -C $env:GITHUB_WORKSPACE rev-parse 'HEAD^{tree}')
  if ($LASTEXITCODE -ne 0 -or $tree.Count -ne 1) { throw 'Cannot verify the trusted checkout tree.' }
  $status = @(& git.exe -C $env:GITHUB_WORKSPACE status --porcelain=v1 --untracked-files=all --ignore-submodules=none)
  if ($LASTEXITCODE -ne 0 -or $head[0].Trim() -cne $SourceSha -or $tree[0].Trim() -cne $SourceTree -or $status.Count -ne 0) {
    throw 'The trusted bootstrap checkout is not the exact clean source and tree.'
  }
  $submodules = @(& git.exe -C $env:GITHUB_WORKSPACE submodule status --recursive)
  if ($LASTEXITCODE -ne 0 -or @($submodules | Where-Object { $_ -match '^[-+U]' }).Count -ne 0) {
    throw 'The trusted bootstrap checkout has uninitialized or divergent submodules.'
  }
  if (-not (Test-Path -LiteralPath $Archive -PathType Leaf) -or
      (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ArchiveSha256) {
    throw 'Downloaded raw archive bytes differ from the independent build digest.'
  }
  $freeRoot = ([IO.DriveInfo]::new('C')).AvailableFreeSpace
  if ($freeRoot -lt ($ExpandedBytes + 1GB + 2GB)) { throw 'Insufficient free space to extract, run and retain the reserve.' }
  $prefix = $SourceSha.Substring(0, 12)
  $parent = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a'
  $root = Join-Path (Join-Path $parent 'n') $prefix
  if ($RetainBuild) {
    # This is an owned, disposable CI root. Preserve the build without deleting
    # or aliasing anything, so the verified ZIP can occupy the exact same root.
    Assert-RealTree $root
    $retainedParent = Join-Path $parent 'build-only'
    if (-not (Test-Path -LiteralPath $retainedParent)) { New-Item -ItemType Directory -Path $retainedParent | Out-Null }
    Assert-RealDirectory $retainedParent
    $retained = Join-Path $retainedParent $prefix
    if (Test-Path -LiteralPath $retained) { throw 'Refusing to overwrite the retained build.' }
    Move-Item -LiteralPath $root -Destination $retained
    Assert-RealTree $retained
  }
  if (Test-Path -LiteralPath $root) { throw 'Bootstrap destination must not already exist.' }
  # Verify each caller-controlled directory before the system bootstrap.
  Initialize-DirectoryIdentityType
  $trustedTemp = Join-Path (Join-Path $parent 'bootstrap-temp') $prefix
  if (Test-Path -LiteralPath $trustedTemp) { throw 'Refusing to reuse a trusted bootstrap temp directory.' }
  foreach ($path in @('C:\', 'C:\Users', 'C:\Users\Administrator', $parent,
                      (Join-Path $parent 'bootstrap-temp'), $trustedTemp)) {
    if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
    Assert-TrustedDirectory $path
  }
  if (@(Get-ChildItem -LiteralPath $trustedTemp -Force).Count -ne 0) { throw 'Trusted bootstrap temp is not empty.' }
  $receiptParent = Join-Path $parent 'receipts'
  if (-not (Test-Path -LiteralPath $receiptParent)) { New-Item -ItemType Directory -Path $receiptParent | Out-Null }
  Assert-RealDirectory $receiptParent
  if (-not [PjCiDirectoryIdentity]::Exact($receiptParent) -or
      @(Get-Item -LiteralPath $receiptParent -Stream '*' -ErrorAction Stop | Where-Object { $_.Stream -ne ':$DATA' -and $_.Stream -ne '::$DATA' }).Count) {
    throw 'Bootstrap receipt parent has an alias or named stream.'
  }
  $receipts = Join-Path $receiptParent $prefix
  if (Test-Path -LiteralPath $receipts) { throw 'Refusing to reuse a bootstrap receipt directory.' }
  New-Item -ItemType Directory -Path $receipts | Out-Null
  Assert-RealDirectory $receipts
  if (-not [PjCiDirectoryIdentity]::Exact($receipts)) { throw 'Bootstrap receipt directory has an alias.' }
  $receiptPath = Join-Path $receipts 'bootstrap.json'
  $bootstrap = Join-Path $env:GITHUB_WORKSPACE 'scripts/windows/bootstrap_native_test_kit.ps1'
  if (-not (Test-Path -LiteralPath $bootstrap -PathType Leaf)) { throw 'Trusted checkout bootstrap is missing.' }
  $shell = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
  if (-not (Test-Path -LiteralPath $shell -PathType Leaf)) { throw 'System Windows PowerShell 5.1 is missing.' }
  $env:TEMP = $trustedTemp
  $env:TMP = $trustedTemp
  $receipt = @(& $shell -NoProfile -NonInteractive -File $bootstrap -Archive $Archive -ArchiveSha256 $ArchiveSha256 `
    -ManifestSha256 $ManifestSha256 -SourceSha $SourceSha -SourceTree $SourceTree `
    -Configuration 'RelWithDebInfo' -TrustedTemp $trustedTemp)
  if ($LASTEXITCODE -ne 0 -or $receipt.Count -ne 1) { throw 'Independent system bootstrap failed; no kit program was started.' }
  $record = $receipt[0] | ConvertFrom-Json
  if ($record.status -cne 'verified' -or $record.archive_sha256 -cne $ArchiveSha256 -or
      $record.manifest_sha256 -cne $ManifestSha256 -or $record.source_sha -cne $SourceSha -or
      $record.source_tree -cne $SourceTree -or $record.configuration -cne 'RelWithDebInfo' -or
      $record.logical_root -cne $root -or $record.bootstrap_temp -cne $trustedTemp -or $record.kit_code_executed -ne $false) {
    throw 'Independent bootstrap receipt does not match the requested artifact and root.'
  }
  [IO.File]::WriteAllText($receiptPath, $receipt[0] + "`n", [Text.UTF8Encoding]::new($false))
  # Authenticate the Python distribution from the trusted checkout using only
  # system PowerShell/.NET before invoking any executable from the kit.
  foreach ($relative in @('scripts/windows/verify_embedded_python_origin.ps1', '.github/windows-native-kit/tool-pins.json')) {
    $tracked = @(& git.exe -C $env:GITHUB_WORKSPACE ls-files --error-unmatch -- $relative)
    if ($LASTEXITCODE -ne 0 -or $tracked.Count -ne 1 -or $tracked[0].Trim() -cne $relative) {
      throw 'Python origin verifier and tool pins must be tracked by the trusted checkout.'
    }
  }
  $originVerifier = Join-Path $env:GITHUB_WORKSPACE 'scripts/windows/verify_embedded_python_origin.ps1'
  $originReceipt = Join-Path $receipts 'python-origin.json'
  if (-not (Test-Path -LiteralPath $originVerifier -PathType Leaf) -or (Test-Path -LiteralPath $originReceipt)) {
    throw 'Trusted Python origin verifier is missing or its receipt already exists.'
  }
  & $shell -NoProfile -NonInteractive -File $originVerifier -KitRoot $root -SourceSha $SourceSha -SourceTree $SourceTree `
    -ManifestSha256 $ManifestSha256 -ArchiveSha256 $ArchiveSha256 -TrustedTemp $trustedTemp -Output $originReceipt
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $originReceipt -PathType Leaf)) {
    throw 'Official Python origin verification failed before any kit executable was started.'
  }
  $originInfo = Get-Item -LiteralPath $originReceipt -Force
  if ($originInfo.PSIsContainer -or ($originInfo.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Python origin receipt is not an ordinary file.'
  }
  $origin = Get-Content -LiteralPath $originReceipt -Raw | ConvertFrom-Json
  if ($origin.schema -ne 1 -or $origin.scope -cne 'disposable-github-hosted-windows-ci' -or
      $origin.source_sha -cne $SourceSha -or $origin.source_tree -cne $SourceTree -or
      $origin.archive_sha256 -cne $ArchiveSha256 -or $origin.manifest_sha256 -cne $ManifestSha256 -or
      $origin.official_zip_sha256 -cnotmatch '^[0-9a-f]{64}$' -or @($origin.members).Count -lt 5) {
    throw 'Python origin receipt does not match the authenticated candidate.'
  }
  $python = Join-Path $root 't/python/python.exe'
  # This source-reviewed verifier must independently recheck the authenticated
  # provenance, the source-reviewed dynamic inventory and clean host modules.
  # Its absence or any mismatch blocks the CI run; the test driver by itself
  # is not a proof of dynamic dependency closure.
  $closureVerifier = Join-Path $root 's/scripts/windows/verify_native_ci_closure.py'
  Invoke-Checked $python @('-I', '-B', $closureVerifier, '--verify-staged', '--root', $root,
    '--manifest', (Join-Path $root '_bundle/manifest.json'), '--manifest-sha256', $ManifestSha256,
    '--source-sha', $SourceSha, '--source-tree', $SourceTree,
    '--reviewed-policy', (Join-Path $root 's/.github/windows-native-kit/ci-closure-policy.json'),
    '--evidence-receipt', (Join-Path $root 'b/native-kit/closure-evidence/receipt.json'))
  $driver = Join-Path $root 's/scripts/windows/run_native_ci_verification.py'
  Invoke-Checked $python @('-I', '-B', $driver, '--root', $root, '--manifest', (Join-Path $root '_bundle/manifest.json'),
    '--manifest-sha256', $ManifestSha256, '--archive-sha256', $ArchiveSha256, '--source-sha', $SourceSha,
    '--source-tree', $SourceTree, '--config', 'RelWithDebInfo', '--plan', 'b/native-kit/run-plan.json',
    '--policy', 'b/native-kit/closure-evidence/ci-policy.json', '--bootstrap-receipt', $receiptPath)
  if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ArchiveSha256) {
    throw 'Archive bytes changed during the CI run.'
  }
}

# Never run this privileged-path preparation on a user machine or a self-hosted
# runner. No existing root is removed or reused, including on a retry.
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_EVENT_NAME -ne 'workflow_dispatch') {
  throw 'A disposable GitHub-hosted Windows workflow_dispatch runner is required.'
}
$gitControl = Join-Path $env:RUNNER_TEMP ('pj-git-control-' + [Guid]::NewGuid().ToString('N'))
Initialize-IsolatedGitEnvironment $gitControl
if ($Phase -eq 'BootstrapSelfTest') { Invoke-BootstrapSelfTest; return }
if ($Phase -eq 'Verify') { Invoke-CleanVerification; return }
if ($env:GITHUB_SERVER_URL -ne 'https://github.com' -or
    $env:GITHUB_REPOSITORY -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$' -or
    $env:GITHUB_SHA -cnotmatch '^[0-9a-f]{40}$' -or
    $env:GITHUB_WORKFLOW_SHA -cnotmatch '^[0-9a-f]{40}$') {
  throw 'Invalid GitHub source or workflow identity.'
}
if ($env:VCToolsVersion -notmatch '^14\.4[0-9]' -or $env:VSCMD_ARG_TGT_ARCH -ne 'x64' -or
    -not (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
  throw 'The x64 MSVC 2022 14.4x environment is required.'
}
$bootstrapPython = (Get-Command python.exe -CommandType Application).Source
$env:PYTHONDONTWRITEBYTECODE = '1'
$remote = "$($env:GITHUB_SERVER_URL)/$($env:GITHUB_REPOSITORY).git"
$sha = $env:GITHUB_SHA
$sourcePrefix = $sha.Substring(0, 12)
$base = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\n'
$root = Join-Path $base $sourcePrefix

# Walk and check each parent before creating the next. Do not follow an
# existing junction, symlink, or other reparse point into a different tree.
foreach ($path in @('C:\', 'C:\Users', 'C:\Users\Administrator',
                    'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a', $base)) {
  if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
  Assert-RealDirectory $path
}
if (Test-Path -LiteralPath $root) { throw "Refusing to reuse an existing build root: $root" }
New-Item -ItemType Directory -Path $root | Out-Null
Assert-RealDirectory $root
$bootstrapTemp = Join-Path $root 'bootstrap-temp'
New-Item -ItemType Directory -Path $bootstrapTemp | Out-Null
$env:TEMP = $bootstrapTemp
$env:TMP = $bootstrapTemp
$source = Join-Path $root 's'
$qtRoot = Join-Path $root 'q'
$build = Join-Path $root 'b'
$i18n = Join-Path $root 'i'
$tools = Join-Path $root 't'
# A new Conan home must not inherit remote credentials or overrides from CI.
foreach ($item in @(Get-ChildItem Env:)) {
  if ($item.Name -match '^CONAN_') { Remove-Item -LiteralPath ('Env:' + $item.Name) -ErrorAction Stop }
}
$env:CONAN_HOME = Join-Path $root 'c'
if (Test-Path -LiteralPath $env:CONAN_HOME) { throw 'Refusing to reuse an existing Conan home.' }
New-Item -ItemType Directory -Path $env:CONAN_HOME | Out-Null
Assert-RealDirectory $env:CONAN_HOME
$env:CONAN_NON_INTERACTIVE = '1'
foreach ($name in 'PYTHONHOME', 'PYTHONPATH', 'PYTHONSTARTUP', 'PKG_CONFIG_PATH', 'PJ_VERSION', 'QT_PLUGIN_PATH') {
  Remove-Item -LiteralPath ("Env:" + $name) -ErrorAction SilentlyContinue
}
Write-Host "Source commit: $sha; workflow commit: $env:GITHUB_WORKFLOW_SHA; root: $root"
Write-Host "Runner image: $env:ImageOS $env:ImageVersion; MSVC: $env:VCToolsVersion; SDK: $env:WindowsSDKVersion"

# The checkout is only the local source of an exact, clean, self-contained
# clone. It is never the configured source directory or a target artifact.
Invoke-Checked $bootstrapPython @((Join-Path $env:GITHUB_WORKSPACE 'scripts/windows/prepare_native_source.py'),
  '--source', $env:GITHUB_WORKSPACE, '--destination', $source, '--sha', $sha, '--remote', $remote)
Assert-RealTree $source
$sourceTree = (& git.exe -C $source rev-parse 'HEAD^{tree}').Trim()
if ($LASTEXITCODE -ne 0 -or $sourceTree -cnotmatch '^[0-9a-f]{40}$') { throw 'Cannot establish source tree identity.' }
Invoke-Checked $bootstrapPython @((Join-Path $source 'scripts/windows/prepare_native_tools.py'),
  '--root', $root, '--pins', (Join-Path $source '.github/windows-native-kit/tool-pins.json'))
Assert-RealTree $tools

# Build-only Python packages are kept in a private venv. The test driver is the
# separately pinned embeddable interpreter prepared above, not this venv and
# not Conan's embedded CPython runtime.
$builder = Join-Path $tools 'builder'
Invoke-Checked $bootstrapPython @('-m', 'venv', $builder)
$builderPython = Join-Path $builder 'Scripts/python.exe'
Invoke-Checked $builderPython @('-m', 'pip', 'install', '--no-cache-dir', 'conan==2.34.0',
  'ninja==1.11.1.4', 'git+https://github.com/miurahr/aqtinstall.git@8c3695d4a4e1ceabf6a74dc6c79681656dc6b74b')
$conan = Join-Path $builder 'Scripts/conan.exe'
$ninja = Join-Path $builder 'Scripts/ninja.exe'
$cmake = Join-Path $tools 'cmake/bin/cmake.exe'
$testPython = Join-Path $tools 'python/python.exe'
$env:PATH = (Join-Path $builder 'Scripts') + ';' + (Join-Path $tools 'cmake/bin') + ';' + $env:PATH
$temp = Join-Path $tools 'build-temp'
New-Item -ItemType Directory -Path $temp | Out-Null
$env:TEMP = $temp
$env:TMP = $temp
Invoke-Checked $builderPython @('-m', 'pip', 'freeze')
Invoke-Checked $conan @('--version')
Invoke-Checked $ninja @('--version')
Invoke-Checked $cmake @('--version')

$versions = @{}
foreach ($line in [IO.File]::ReadAllLines((Join-Path $source 'versions.env'))) {
  if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^\s#]+)\s*$') {
    if ($versions.ContainsKey($Matches[1])) { throw 'Duplicate versions.env key.' }
    $versions[$Matches[1]] = $Matches[2]
  }
}
$qtVersion = $versions['PJ_QT_VERSION']
if (-not $qtVersion -or $qtVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid pinned Qt version.' }
$qt = Join-Path $qtRoot "$qtVersion/msvc2022_64"
$qtArchives = Join-Path $root 'd/qt-archives'
New-Item -ItemType Directory -Path $qtArchives | Out-Null
for ($attempt = 1; $attempt -le 5; $attempt++) {
  & $builderPython -m aqt install-qt windows desktop $qtVersion win64_msvc2022_64 `
    --outputdir $qtRoot --keep --archive-dest $qtArchives
  if ($LASTEXITCODE -eq 0) { break }
  if ($attempt -eq 5) { throw 'Pinned Qt installation failed after five attempts.' }
  Start-Sleep -Seconds (15 * $attempt)
}
Assert-RealTree $qtRoot
foreach ($path in @('bin/qmake.exe', 'bin/lrelease.exe', 'bin/lupdate.exe', 'bin/rcc.exe',
                    'translations/qtbase_zh_CN.qm')) {
  if (-not (Test-Path -LiteralPath (Join-Path $qt $path) -PathType Leaf)) { throw "Missing Qt input: $path" }
}
$actualQt = & (Join-Path $qt 'bin/qmake.exe') -query QT_VERSION
if ($LASTEXITCODE -ne 0 -or $actualQt.Trim() -cne $qtVersion) { throw 'Qt version differs from versions.env.' }
Write-Host "Qt: $actualQt ($qt)"
if (-not (Get-ChildItem -LiteralPath $qtArchives -File)) { throw 'Qt archive evidence was not retained.' }
Get-ChildItem -LiteralPath $qtArchives -File | Get-FileHash -Algorithm SHA256 |
  ForEach-Object { Write-Host "Qt archive SHA-256 $($_.Hash.ToLowerInvariant()) $([IO.Path]::GetFileName($_.Path))" }

# Match the native Windows Conan graph and source-backup policy. CONAN_HOME is
# set before profile detection and before any CMake configure.
Assert-RealTree $env:CONAN_HOME
Invoke-Checked $conan @('profile', 'detect', '--force')
Invoke-Checked $conan @('remote', 'add', 'plotjuggler-conan', 'https://plotjuggler.jfrog.io/artifactory/api/conan/plotjuggler-conan')
Invoke-Checked $conan @('remote', 'enable', 'plotjuggler-conan')
$sourceCache = Join-Path $env:CONAN_HOME 'source-cache'
@'
from pathlib import Path
import hashlib, json, re, shutil, sys
source, cache, home = map(Path, sys.argv[1:])
seeds = source / '.github/conan/source-backup'
blobs = sorted(p for p in seeds.iterdir() if re.fullmatch(r'[0-9a-f]{64}', p.name))
if not blobs:
    raise SystemExit('No Conan source backups found')
for blob in blobs:
    if hashlib.sha256(blob.read_bytes()).hexdigest() != blob.name:
        raise SystemExit('Conan source backup SHA-256 mismatch: ' + blob.name)
    if not json.loads(blob.with_suffix('.json').read_text(encoding='utf-8')).get('references'):
        raise SystemExit('Conan source backup references missing: ' + blob.name)
target = cache / 's'
target.mkdir(parents=True)
for blob in blobs:
    shutil.copy2(blob, target / blob.name)
    shutil.copy2(blob.with_suffix('.json'), target / (blob.name + '.json'))
conf = home / 'global.conf'
lines = conf.read_text(encoding='utf-8').splitlines() if conf.exists() else []
lines = [line for line in lines if not line.startswith(('core.sources:download_cache=', 'core.sources:download_urls='))]
lines += [f'core.sources:download_cache={cache.as_posix()}',
          'core.sources:download_urls=["origin", "https://c3i.jfrog.io/artifactory/conan-center-backup-sources/"]']
conf.write_text('\n'.join(lines) + '\n', encoding='utf-8')
'@ | & $builderPython - $source $sourceCache $env:CONAN_HOME
if ($LASTEXITCODE -ne 0) { throw 'Conan source-backup verification failed.' }
$prefetch = Start-Process -FilePath $builderPython -NoNewWindow -PassThru -ArgumentList @(
  (Join-Path $source 'scripts/prefetch_assimp_source.py'), '--cache-dir', $sourceCache)
if (-not $prefetch.WaitForExit(12 * 60 * 1000)) {
  $prefetch.Kill()
  $prefetch.WaitForExit()
  throw 'Conan source prefetch exceeded its 12-minute wall-clock limit.'
}
if ($prefetch.ExitCode -ne 0) { throw "Conan source prefetch failed with exit code $($prefetch.ExitCode)." }
New-Item -ItemType Directory -Path $build | Out-Null
$conanEvidence = Join-Path $build 'native-kit/conan-evidence'
New-Item -ItemType Directory -Path $conanEvidence -Force | Out-Null
Invoke-RecordedBuildProcess 'remotes' $conan @('remote', 'list', '--format=json') $source $conanEvidence 'conan'
$actualRemotes = @(Get-Content -LiteralPath (Join-Path $conanEvidence 'remotes.stdout.bin') -Raw | ConvertFrom-Json)
$expectedRemotes = @{ 'conancenter' = 'https://center2.conan.io';
  'plotjuggler-conan' = 'https://plotjuggler.jfrog.io/artifactory/api/conan/plotjuggler-conan' }
if ($actualRemotes.Count -ne 2) { throw 'The Conan home does not have exactly the two public expected remotes.' }
$seenRemotes = @{}
foreach ($entry in $actualRemotes) {
  if (-not $expectedRemotes.ContainsKey($entry.name) -or $seenRemotes.ContainsKey($entry.name) -or
      $entry.url -cne $expectedRemotes[$entry.name] -or $entry.verify_ssl -ne $true -or $entry.enabled -ne $true -or
      $null -ne $entry.allowed_packages -or $entry.recipes_only -ne $false -or $entry.force_auth -ne $false) {
    throw 'Conan remote identity or public non-authenticated settings differ.'
  }
  $seenRemotes[$entry.name] = $true
}
Invoke-Checked (Get-Command python.exe -CommandType Application).Source @((Join-Path $source 'scripts/bootstrap_host_sdk.py'))
$conanGraph = Join-Path $build 'conan-install-graph.json'
Invoke-RecordedBuildProcess 'install' $conan @('install', $source, "--output-folder=$build", '--build=missing',
  '-r=plotjuggler-conan', '-r=conancenter', "--lockfile=$(Join-Path $source 'conan.lock')", '--lockfile-partial',
  '-s', 'build_type=RelWithDebInfo', '-s', 'compiler.cppstd=20', '-c', 'tools.build:jobs=2',
  '-o', 'cpython/*:shared=True', '-s', 'cpython/*:build_type=Release', '-s', 'compiler.version=194',
  '-c', 'tools.cmake.cmaketoolchain:generator=Ninja Multi-Config', '--format=json',
  "--out-file=$conanGraph") $source $conanEvidence 'conan' $conanGraph
Assert-RealTree $env:CONAN_HOME

$selftest = $env:BOOTSTRAP_SELFTEST_DIR
if (-not $selftest -or -not [IO.Path]::IsPathFullyQualified($selftest)) { throw 'Bootstrap self-test evidence directory is missing.' }
Assert-RealDirectory $selftest
$selftestFull = [IO.Path]::GetFullPath($selftest)
$runnerTemp = [IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\') + '\'
if (-not $selftestFull.StartsWith($runnerTemp, [StringComparison]::OrdinalIgnoreCase) -or
    [IO.Path]::GetFileName($selftestFull) -notmatch '^pj-bootstrap-selftest-[0-9a-f]{12}$') {
  throw 'Bootstrap self-test evidence is outside its fresh hosted-runner directory.'
}
$selftestRecord = Get-Content -LiteralPath (Join-Path $selftestFull 'process.json') -Raw | ConvertFrom-Json
if ($selftestRecord.schema -ne 1 -or $selftestRecord.scope -cne 'disposable-windows-ci-only' -or
    $selftestRecord.source_sha -cne $sha -or $selftestRecord.synthetic_sha -cnotmatch '^[0-9a-f]{40}$' -or
    $selftestRecord.exit_code -ne 0 -or
    $selftestRecord.test_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $source 'tests/test_windows_native_bootstrap.py') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $selftestRecord.bootstrap_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $source 'scripts/windows/bootstrap_native_test_kit.ps1') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $selftestRecord.stdout_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $selftestFull 'stdout.bin') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $selftestRecord.stderr_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $selftestFull 'stderr.bin') -Algorithm SHA256).Hash.ToLowerInvariant()) {
  throw 'Bootstrap self-test evidence differs from actual source, results or raw output.'
}
$selftestLog = [IO.File]::ReadAllText((Join-Path $selftestFull 'stderr.bin'))
if ($selftestLog -notmatch '(?m)test_actual_embedded_verifier_rejects_malformed_cases[^\r\n]*\.\.\. ok' -or
    $selftestLog -notmatch '(?m)test_full_fixed_root_and_refuse_reuse[^\r\n]*\.\.\. ok') {
  throw 'Bootstrap self-test did not actually pass both real NTFS and fixed-root controls.'
}
$originSelftest = Get-Content -LiteralPath (Join-Path $selftestFull 'python-origin.process.json') -Raw | ConvertFrom-Json
if ($originSelftest.schema -ne 1 -or $originSelftest.scope -cne 'disposable-windows-ci-only' -or
    $originSelftest.source_sha -cne $sha -or $originSelftest.source_tree -cne $sourceTree -or
    $originSelftest.synthetic_sha -cne $selftestRecord.synthetic_sha -or
    $originSelftest.exit_code -ne 0 -or $originSelftest.bootstrap_sha256 -cne $selftestRecord.bootstrap_sha256 -or
    $originSelftest.test_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $source 'tests/test_windows_native_python_origin.py') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $originSelftest.python_origin_script_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $source 'scripts/windows/verify_embedded_python_origin.ps1') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $originSelftest.stdout_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $selftestFull 'python-origin.stdout.bin') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $originSelftest.stderr_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $selftestFull 'python-origin.stderr.bin') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    [IO.File]::ReadAllText((Join-Path $selftestFull 'python-origin.stderr.bin')) -notmatch
      '(?m)test_actual_dotnet_compare_accepts_exact_zip_and_rejects_tampering[^\r\n]*\.\.\. ok') {
  throw 'Python origin Windows adversarial self-test evidence differs or did not run.'
}
$selftestCopy = Join-Path $build 'native-kit/bootstrap-selftest-evidence'
New-Item -ItemType Directory -Path $selftestCopy -Force | Out-Null
foreach ($name in @('process.json', 'stdout.bin', 'stderr.bin',
                    'python-origin.process.json', 'python-origin.stdout.bin', 'python-origin.stderr.bin')) {
  Copy-Item -LiteralPath (Join-Path $selftestFull $name) -Destination (Join-Path $selftestCopy $name)
}

# CSV plugin preflight itself runs CTest discovery, so the read-only CI Qt
# probe must run before it, under the actual token and exact temporary path.
$env:PATH = (Join-Path $builder 'Scripts') + ';' + (Join-Path $qt 'bin') + ';' + $env:PATH
$ciTempSource = Join-Path $source 'scripts/windows/native_ci_temp_probe'
if (-not (Test-Path -LiteralPath (Join-Path $ciTempSource 'CMakeLists.txt') -PathType Leaf)) {
  throw 'The source-reviewed CI Qt temporary-path probe is missing.'
}
$ciTempBuild = Join-Path $build 'ci-temp-probe'
Invoke-Checked $cmake @('-S', $ciTempSource, '-B', $ciTempBuild, '-G', 'Ninja Multi-Config',
  "-DCMAKE_PREFIX_PATH=$qt", "-DCMAKE_MAKE_PROGRAM=$ninja")
Invoke-Checked $cmake @('--build', $ciTempBuild, '--config', 'RelWithDebInfo', '--target', 'pj_native_ci_temp_probe', '--parallel', '2')
$ciTempExe = Join-Path $ciTempBuild 'RelWithDebInfo/pj_native_ci_temp_probe.exe'
if (-not (Test-Path -LiteralPath $ciTempExe -PathType Leaf)) { throw 'The compiled CI Qt temporary-path probe is missing.' }
$ciTempRunRoot = Join-Path $root 'ci-discovery'
if (Test-Path -LiteralPath $ciTempRunRoot) { throw 'Refusing to reuse a CI discovery run root.' }
New-Item -ItemType Directory -Path (Join-Path $ciTempRunRoot 'tmp') -Force | Out-Null
$env:TEMP = Join-Path $ciTempRunRoot 'tmp'
$env:TMP = $env:TEMP
$ciTempEvidence = Join-Path $build 'native-kit/ci-temp-probe-evidence'
New-Item -ItemType Directory -Path $ciTempEvidence -Force | Out-Null
function Invoke-CiTempProbe([string]$Name) {
  if ($Name -notin @('before-plugin-preflight', 'before-marker-mutation', 'before-marker-discovery', 'before-main-discovery')) { throw 'Unknown CI temp-probe phase.' }
  $qtCore = Join-Path $qt 'bin/Qt6Core.dll'
  $stdout = Join-Path $ciTempEvidence ($Name + '.stdout.bin')
  $stderr = Join-Path $ciTempEvidence ($Name + '.stderr.bin')
  if ((Test-Path -LiteralPath $stdout) -or (Test-Path -LiteralPath $stderr)) { throw 'CI temp-probe evidence already exists.' }
  $arguments = @('--run-root', $ciTempRunRoot, '--temp', $env:TEMP, '--qt', $qtVersion, '--qt-core', $qtCore)
  $exeSha = (Get-FileHash -LiteralPath $ciTempExe -Algorithm SHA256).Hash.ToLowerInvariant()
  $qtSha = (Get-FileHash -LiteralPath $qtCore -Algorithm SHA256).Hash.ToLowerInvariant()
  $actualPath = $env:PATH
  $process = Start-Process -FilePath $ciTempExe -ArgumentList $arguments -WorkingDirectory $source -NoNewWindow -PassThru -Wait `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  if ($process.ExitCode -ne 0) { throw "CI Qt temporary-path probe failed in phase $Name." }
  $result = Get-Content -LiteralPath $stdout -Raw | ConvertFrom-Json
  if ($result.scope -cne 'disposable-windows-ci-only' -or $result.qt_version -cne $qtVersion -or
      $result.pid -ne $process.Id -or $result.session -lt 0 -or $result.integrity_rid -le 0 -or -not $result.user_sid -or
      $result.auth_luid -cnotmatch '^[0-9a-f]{8}:[0-9a-f]{8}$' -or $result.elevation_type -cnotin @('default', 'full', 'limited') -or
      -not [string]::Equals([IO.Path]::GetFullPath($result.qt_core), [IO.Path]::GetFullPath($qtCore), [StringComparison]::OrdinalIgnoreCase) -or
      -not [string]::Equals([IO.Path]::GetFullPath($result.qt_temp), [IO.Path]::GetFullPath($env:TEMP), [StringComparison]::OrdinalIgnoreCase) -or
      $env:TMP -cne $env:TEMP -or $actualPath -cne $env:PATH -or
      (Get-FileHash -LiteralPath $ciTempExe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $exeSha -or
      (Get-FileHash -LiteralPath $qtCore -Algorithm SHA256).Hash.ToLowerInvariant() -cne $qtSha) {
    throw "CI Qt temporary-path probe evidence did not match phase $Name."
  }
  $receipt = @{ schema = 1; phase = $Name; cwd = $source; executable = $ciTempExe; argv = $arguments; exit_code = $process.ExitCode;
    path = $actualPath; temp = $env:TEMP; tmp = $env:TMP; executable_sha256 = $exeSha; qt_core_sha256 = $qtSha;
    stdout_sha256 = (Get-FileHash -LiteralPath $stdout -Algorithm SHA256).Hash.ToLowerInvariant();
    stderr_sha256 = (Get-FileHash -LiteralPath $stderr -Algorithm SHA256).Hash.ToLowerInvariant() }
  [IO.File]::WriteAllText((Join-Path $ciTempEvidence ($Name + '.json')), ($receipt | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
}
Invoke-CiTempProbe 'before-plugin-preflight'

$sourceTreeCheck = (& git.exe -C $source rev-parse 'HEAD^{tree}').Trim()
if ($LASTEXITCODE -ne 0 -or $sourceTreeCheck -cne $sourceTree) { throw 'Source tree changed after Conan setup.' }

# Exercise only the source-controlled, UUID-scoped private HKCU fixture on this
# disposable hosted runner. The controller owns its exact key and raw logs;
# an incomplete run or cleanup failure prevents all downstream packaging.
$registrySource = Join-Path $source 'scripts/windows/native_registry_smoke'
$registryController = Join-Path $registrySource 'run_smoke.py'
if (-not (Test-Path -LiteralPath (Join-Path $registrySource 'CMakeLists.txt') -PathType Leaf) -or
    -not (Test-Path -LiteralPath $registryController -PathType Leaf)) {
  throw 'The required source-reviewed private-registry smoke and controller are missing.'
}
$registryBuild = Join-Path $build 'registry-smoke'
$registryLogs = Join-Path $build 'native-kit/registry-smoke-build'
$testMains = Join-Path $source 'cmake/test_mains'
New-Item -ItemType Directory -Path $registryLogs -Force | Out-Null
& $cmake -S $registrySource -B $registryBuild -G 'Ninja Multi-Config' "-DCMAKE_PREFIX_PATH=$qt" "-DCMAKE_MAKE_PROGRAM=$ninja" "-DPJ_TEST_MAINS_DIR=$testMains" 2>&1 |
  Tee-Object -FilePath (Join-Path $registryLogs 'configure.log')
if ($LASTEXITCODE -ne 0) { throw 'Private-registry smoke configuration failed.' }
& $cmake --build $registryBuild --config RelWithDebInfo --target registry_fixture_smoke --parallel 2 2>&1 |
  Tee-Object -FilePath (Join-Path $registryLogs 'build.log')
if ($LASTEXITCODE -ne 0) { throw 'Private-registry smoke compilation failed.' }
$registryExe = Join-Path $registryBuild 'RelWithDebInfo/registry_fixture_smoke.exe'
if (-not (Test-Path -LiteralPath $registryExe -PathType Leaf)) { throw 'The compiled private-registry smoke executable is missing.' }
$registryEvidence = Join-Path $build 'native-kit/registry-smoke-evidence'
if (Test-Path -LiteralPath $registryEvidence) { throw 'Refusing to reuse private-registry smoke evidence.' }
Invoke-Checked $builderPython @('-I', '-B', $registryController, '--exe', $registryExe, '--source-dir', $registrySource,
  '--test-mains-dir', $testMains, '--qt-core', (Join-Path $qt 'bin/Qt6Core.dll'), '--output', $registryEvidence)
$registryReceipt = Join-Path $registryEvidence 'receipt.json'
if (-not (Test-Path -LiteralPath $registryReceipt -PathType Leaf)) { throw 'Private-registry smoke receipt is missing.' }
$registryResult = Get-Content -LiteralPath $registryReceipt -Raw | ConvertFrom-Json
if ($registryResult.schema -ne 1 -or $registryResult.complete -ne $true -or
    $registryResult.normal.exit_code -ne 0 -or $registryResult.injected.exit_code -ne 1 -or
    @($registryResult.normal.absent_after).Count -ne 2 -or
    @($registryResult.normal.absent_after | Where-Object { $_ -ne $true }).Count -ne 0 -or
    @($registryResult.injected.present_before_exact_cleanup).Count -ne 2 -or
    @($registryResult.injected.present_before_exact_cleanup | Where-Object { $_ -ne $true }).Count -ne 0 -or
    @($registryResult.injected.absent_after_exact_cleanup).Count -ne 2 -or
    @($registryResult.injected.absent_after_exact_cleanup | Where-Object { $_ -ne $true }).Count -ne 0 -or
    $registryResult.exe_sha256 -cne (Get-FileHash -LiteralPath $registryExe -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $registryResult.qt_core_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $qt 'bin/Qt6Core.dll') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $registryResult.guard_header_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $testMains 'pj_test_windows_registry.h') -Algorithm SHA256).Hash.ToLowerInvariant()) {
  throw 'Private-registry lifecycle, executable identity or exact-key cleanup did not complete.'
}
foreach ($raw in @('normal.stdout.bin', 'normal.stderr.bin', 'injected.stdout.bin', 'injected.stderr.bin')) {
  if (-not (Test-Path -LiteralPath (Join-Path $registryEvidence $raw) -PathType Leaf)) { throw "Missing private-registry raw output: $raw" }
}
$registrySourceFiles = @(& git.exe -C $source ls-files -- 'scripts/windows/native_registry_smoke')
if ($LASTEXITCODE -ne 0 -or $registrySourceFiles.Count -eq 0) { throw 'The private-registry smoke has no tracked source.' }
$sourceHashes = @()
foreach ($relative in $registrySourceFiles) {
  $item = Join-Path $source $relative
  if (-not (Test-Path -LiteralPath $item -PathType Leaf)) { throw "Tracked private-registry input is missing: $relative" }
  $sourceHashes += @{ path = $relative.Replace('\', '/'); sha256 = (Get-FileHash -LiteralPath $item -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$compilerPath = (Get-Command cl.exe -CommandType Application).Source
$registryIdentity = @{ schema = 1; source_sha = $sha; source_tree = $sourceTree; configuration = 'RelWithDebInfo';
  source_files = $sourceHashes; executable_sha256 = (Get-FileHash -LiteralPath $registryExe -Algorithm SHA256).Hash.ToLowerInvariant();
  qt_core_sha256 = (Get-FileHash -LiteralPath (Join-Path $qt 'bin/Qt6Core.dll') -Algorithm SHA256).Hash.ToLowerInvariant();
  compiler_sha256 = (Get-FileHash -LiteralPath $compilerPath -Algorithm SHA256).Hash.ToLowerInvariant();
  receipt_sha256 = (Get-FileHash -LiteralPath $registryReceipt -Algorithm SHA256).Hash.ToLowerInvariant() }
[IO.File]::WriteAllText((Join-Path $registryLogs 'producer-identity.json'), ($registryIdentity | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))

# Build the fixed CSV plugin in an isolated test-only prefix before the main
# CMake configure. Its exact DLL path is compiled into the real FileLoader
# regression; a different or unstaged binary must never satisfy that test.
$csvPrefix = Join-Path $build 'csv-prefix'
$csvWork = Join-Path $build 'csv-plugin-work'
$env:CMAKE_PREFIX_PATH = $qt
$env:PJ_DISABLE_TELEMETRY = '1'
Push-Location $source
try {
  Invoke-Checked $builderPython @('-X', 'utf8', (Join-Path $source 'packaging/localization/build_localized_plugins.py'),
    '--preflight', '--plugin', 'csv-loader', '--work', $csvWork, '--prefix', $csvPrefix)
} finally { Pop-Location }
$csvOutput = @(& $builderPython -X utf8 -c "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from run_csv_runtime_acceptance import staged_csv; print(staged_csv(Path(sys.argv[2])))" `
  (Join-Path $source 'packaging/localization') $csvPrefix)
if ($LASTEXITCODE -ne 0 -or $csvOutput.Count -ne 1 -or -not (Test-Path -LiteralPath $csvOutput[0] -PathType Leaf)) {
  throw 'Could not establish the exact staged CSV plugin identity.'
}
$csvPlugin = $csvOutput[0].Trim().Replace('\', '/')

# Both CMake trees record the exact future runtime interpreter and offline IFW
# inputs at their final paths. Application-suite discovery is done only on the
# disposable CI runner after the compiler, Qt and test inputs are ready.
$extractor = Join-Path $tools '7z/7za.exe'
$archive = Join-Path $tools 'ifw/ifw.7z'
$extractorSha = (Get-FileHash -LiteralPath $extractor -Algorithm SHA256).Hash.ToLowerInvariant()
$env:PATH = (Join-Path $tools 'python') + ';' + (Join-Path $qt 'bin') + ';' + $env:PATH
$common = @('-G', 'Ninja Multi-Config', "-DCMAKE_PREFIX_PATH=$qt", "-DCMAKE_MAKE_PROGRAM=$ninja",
  "-DPython3_EXECUTABLE=$testPython", "-DPJ_TEST_PYTHON=$testPython", "-DPJ_IFW_TEST_ARCHIVE=$archive",
  "-DPJ_IFW_TEST_EXTRACTOR=$extractor", "-DPJ_IFW_TEST_EXTRACTOR_SHA256=$extractorSha",
  '-DPJ_NATIVE_BUNDLE_MODE=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo', '-DCMAKE_POLICY_DEFAULT_CMP0141=NEW', '-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded')
Invoke-Checked $cmake (@('-S', (Join-Path $source 'pj_app/tests/i18n'), '-B', $i18n) + $common)
Invoke-Checked $cmake @('--build', $i18n, '--config', 'RelWithDebInfo', '--parallel', '2')
# Query before the first main-tree configure. No existing index/query is reused.
$apiDirectory = Join-Path $build '.cmake/api/v1/query'
if (Test-Path -LiteralPath (Join-Path $build '.cmake/api')) { throw 'Refusing to reuse a CMake File API query tree.' }
New-Item -ItemType Directory -Path $apiDirectory -Force | Out-Null
foreach ($dir in @((Join-Path $build '.cmake'), (Join-Path $build '.cmake/api'),
                    (Join-Path $build '.cmake/api/v1'), $apiDirectory)) { Assert-RealDirectory $dir }
$query = Join-Path $apiDirectory 'codemodel-v2'
$queryHandle = [IO.File]::Open($query, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
$queryHandle.Dispose()
$codemodelEvidence = Join-Path $build 'native-kit/codemodel'
if (Test-Path -LiteralPath $codemodelEvidence) { throw 'Refusing to reuse CMake File API evidence.' }
New-Item -ItemType Directory -Path (Join-Path $codemodelEvidence 'process') -Force | Out-Null
$mainConfigure = @('-S', $source, '-B', $build, "-DCMAKE_TOOLCHAIN_FILE=$(Join-Path $build 'conan_toolchain.cmake')",
  '-DPJ_BUILD_TESTS=ON', '-DPJ_BUILD_DEMOS=OFF', '-DPJ_PLUGIN_FEEDBACK_ACCEPTANCE=ON',
  "-DPJ_CSV_RUNTIME_PLUGIN=$csvPlugin") + $common
Invoke-RecordedBuildProcess 'configure' $cmake $mainConfigure $root (Join-Path $codemodelEvidence 'process') 'cmake'
Invoke-RecordedBuildProcess 'build' $cmake @('--build', $build, '--config', 'RelWithDebInfo', '--parallel', '2') `
  $root (Join-Path $codemodelEvidence 'process') 'cmake'
$planner = Join-Path $source 'scripts/windows/plan_native_stage.py'
Invoke-Checked $builderPython @('-I', '-B', $planner, '--root', $root, '--logical-root', $root,
  '--source-sha', $sha, '--source-tree', $sourceTree, '--capture-codemodel',
  '--output', (Join-Path $codemodelEvidence 'capture.json'))
$dllDirs = @()
foreach ($list in @('pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt')) {
  $file = Join-Path $build $list
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing runtime path list: $list" }
  foreach ($line in [IO.File]::ReadAllLines($file)) {
    if (-not $line.Trim()) { continue }
    $directory = [IO.Path]::GetFullPath($line.Trim())
    $allowed = $env:CONAN_HOME.TrimEnd('\') + '\'
    if (-not $directory.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) {
      throw "Runtime directory lies outside the same-root Conan home: $directory"
    }
    Assert-RealDirectory $directory
    $dllDirs += $directory
  }
}
$env:PATH = (($dllDirs | Select-Object -Unique) -join ';') + ';' + $env:PATH

# Run the actual linked MainWindow negative control, not a method-only probe.
# The controller modifies only its exact private source checkout, restores it,
# rebuilds and reruns the original test, and retains an incomplete sentinel on
# any failure. A failed or interrupted attempt can never reach staging.
$mutationController = Join-Path $source 'scripts/windows/native_marker_mutation.py'
if (-not (Test-Path -LiteralPath $mutationController -PathType Leaf)) { throw 'The linked MainWindow marker negative-control script is missing.' }
$mutationEvidence = Join-Path $build 'native-kit/marker-mutation-evidence'
if (Test-Path -LiteralPath $mutationEvidence) { throw 'Refusing to reuse linked marker mutation evidence.' }
Invoke-CiTempProbe 'before-marker-mutation'
$mutationQtEvidence = Join-Path $ciTempEvidence 'before-marker-mutation.stdout.bin'
Invoke-Checked $builderPython @('-I', '-B', $mutationController, '--root', $root, '--output', $mutationEvidence,
  '--source-sha', $sha, '--source-tree', $sourceTree, '--qt-evidence', $mutationQtEvidence,
  '--qt-core', (Join-Path $qt 'bin/Qt6Core.dll'))
if ((Test-Path -LiteralPath (Join-Path $mutationEvidence 'INCOMPLETE')) -or
    -not (Test-Path -LiteralPath (Join-Path $mutationEvidence 'receipt.json') -PathType Leaf)) {
  throw 'The linked marker mutation remains incomplete; staging is forbidden.'
}
$mutationReceipt = Get-Content -LiteralPath (Join-Path $mutationEvidence 'receipt.json') -Raw | ConvertFrom-Json
$markerSourceFile = Join-Path $source 'pj_runtime/src/ActiveWidgetsMarker.cpp'
$restoredRunner = Join-Path $build 'pj_app/RelWithDebInfo/pj_app_gui_tests.exe'
if ($mutationReceipt.schema -ne 1 -or $mutationReceipt.complete -ne $true -or
    $mutationReceipt.scope -cne 'disposable-windows-ci-only' -or $mutationReceipt.source_sha -cne $sha -or
    $mutationReceipt.source_tree -cne $sourceTree -or
    $mutationReceipt.case -cne 'MainWindowCustomWidgetTest.WindowCloseClearsAnOrphanRecordInsideTheSurvivingFixtureRoot' -or
    $mutationReceipt.mutated_source_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    $mutationReceipt.baseline_runner_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    $mutationReceipt.mutant_runner_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    $mutationReceipt.original_source_sha256 -cne (Get-FileHash -LiteralPath $markerSourceFile -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $mutationReceipt.restored_runner_sha256 -cne (Get-FileHash -LiteralPath $restoredRunner -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $mutationReceipt.qt_preflight_sha256 -cne (Get-FileHash -LiteralPath $mutationQtEvidence -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $mutationReceipt.mutated_source_sha256 -ceq $mutationReceipt.original_source_sha256 -or
    $mutationReceipt.mutant_runner_sha256 -ceq $mutationReceipt.restored_runner_sha256) {
  throw 'Linked marker mutation receipt does not bind the actual restored source, runner and Qt preflight.'
}
foreach ($phase in @('mutant-build', 'mutant-test', 'original-build', 'original-test')) {
  foreach ($extension in @('.stdout.bin', '.stderr.bin', '.process.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $mutationEvidence ($phase + $extension)) -PathType Leaf)) {
      throw "Missing raw linked marker mutation evidence: $phase$extension"
    }
  }
}
foreach ($report in @('mutant.xml', 'original.xml')) {
  if (-not (Test-Path -LiteralPath (Join-Path $mutationEvidence $report) -PathType Leaf)) { throw "Missing linked marker result: $report" }
}
$sourceStatus = @(& git.exe -C $source status --porcelain=v1 --untracked-files=all --ignore-submodules=none)
if ($LASTEXITCODE -ne 0 -or $sourceStatus.Count -ne 0) { throw 'Source checkout was not restored cleanly after linked mutation.' }

# The generated media job is a separate trusted workflow dependency. Import
# only after the mutation restored a genuinely clean checkout, and before the
# complete main/i18n discovery. No tracked source file is overwritten.
if ($env:PJ_MEDIA_MANIFEST_SHA256 -cnotmatch '^[0-9a-f]{64}$' -or
    $env:PJ_MEDIA_SOURCE_SHA -cne $sha -or $env:PJ_MEDIA_SOURCE_TREE -cne $sourceTree) {
  throw 'The successful media job digest or exact source identity is missing.'
}
$mediaInput = Join-Path $env:RUNNER_TEMP 'pj-native-media'
$mediaReceipt = Join-Path $build 'native-kit/media-fixtures/generation-receipt.json'
Invoke-Checked $builderPython @('-I', '-B', $planner, '--root', $root, '--logical-root', $root,
  '--source-sha', $sha, '--source-tree', $sourceTree, '--import-generated-media', $mediaInput, '--output', $mediaReceipt)

# Marker tests are an independent, optional real-App condition. Record actual
# commands and bytes when the reviewed source exists, but never approve an App
# case merely because a same-named JUnit test was supplied.
$markerSource = Join-Path $source 'scripts/windows/native_app_marker_probe'
if (Test-Path -LiteralPath (Join-Path $markerSource 'CMakeLists.txt') -PathType Leaf) {
  $markerBuild = Join-Path $build 'app-marker-probe'
  $markerEvidence = Join-Path $build 'native-kit/app-marker-evidence'
  if (Test-Path -LiteralPath $markerEvidence) { throw 'Refusing to reuse App marker evidence.' }
  New-Item -ItemType Directory -Path $markerEvidence | Out-Null
  function Invoke-RecordedMarker([string]$PhaseName, [string]$Executable, [string[]]$Arguments) {
    $stdout = Join-Path $markerEvidence ($PhaseName + '.stdout.bin')
    $stderr = Join-Path $markerEvidence ($PhaseName + '.stderr.bin')
    # Start-Process joins its argument array on Windows. Quote a whitespace
    # argument explicitly so the recorded argv matches the child argv.
    $nativeArguments = @($Arguments | ForEach-Object {
      if ($_ -match '[\s"]') {
        if ($_ -match '"|\\$') { throw 'Unexpected marker command argument requiring complex quoting.' }
        '"' + $_ + '"'
      } else { $_ }
    })
    $process = Start-Process -FilePath $Executable -ArgumentList $nativeArguments -WorkingDirectory $root -NoNewWindow -PassThru -Wait `
      -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $record = @{ schema = 1; executable = $Executable; argv = @($Executable) + $Arguments; cwd = $root;
      exit_code = $process.ExitCode; still_running = $false; path = $env:PATH; temp = $env:TEMP; tmp = $env:TMP;
      executable_sha256 = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant();
      stdout_sha256 = (Get-FileHash -LiteralPath $stdout -Algorithm SHA256).Hash.ToLowerInvariant();
      stderr_sha256 = (Get-FileHash -LiteralPath $stderr -Algorithm SHA256).Hash.ToLowerInvariant() }
    [IO.File]::WriteAllText((Join-Path $markerEvidence ($PhaseName + '.json')), ($record | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    return $process.ExitCode
  }
  $configured = Invoke-RecordedMarker 'configure' $cmake @('-S', $markerSource, '-B', $markerBuild, '-G', 'Ninja Multi-Config',
    "-DCMAKE_PREFIX_PATH=$qt", "-DCMAKE_MAKE_PROGRAM=$ninja")
  $built = -1
  if ($configured -eq 0) {
    $built = Invoke-RecordedMarker 'build' $cmake @('--build', $markerBuild, '--config', 'RelWithDebInfo')
  }
  $markerExecutables = @('native_app_marker_probe.exe', 'marker_probe_policy_test.exe',
                         'marker_probe_windows_tests.exe', 'plotjuggler_marker_test_fixture.exe')
  $markerFiles = @($markerExecutables | ForEach-Object { Join-Path $markerBuild (Join-Path 'RelWithDebInfo' $_) })
  if ($configured -eq 0 -and $built -eq 0 -and @($markerFiles | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }).Count -eq 0) {
    $cache = Join-Path $markerBuild 'CMakeCache.txt'
    $cacheValid = Test-Path -LiteralPath $cache -PathType Leaf
    if ($cacheValid) {
      $lines = [IO.File]::ReadAllLines($cache)
      $home = @($lines | Where-Object { $_ -like 'CMAKE_HOME_DIRECTORY:INTERNAL=*' })
      $generator = @($lines | Where-Object { $_ -ceq 'CMAKE_GENERATOR:INTERNAL=Ninja Multi-Config' })
      $cacheValid = $home.Count -eq 1 -and $generator.Count -eq 1 -and
        [string]::Equals([IO.Path]::GetFullPath($home[0].Substring('CMAKE_HOME_DIRECTORY:INTERNAL='.Length)),
                         [IO.Path]::GetFullPath($markerSource), [StringComparison]::OrdinalIgnoreCase)
    }
    if ($cacheValid) {
    $exeHashes = @{ probe = (Get-FileHash -LiteralPath $markerFiles[0] -Algorithm SHA256).Hash.ToLowerInvariant();
      policy_test = (Get-FileHash -LiteralPath $markerFiles[1] -Algorithm SHA256).Hash.ToLowerInvariant();
      windows_test = (Get-FileHash -LiteralPath $markerFiles[2] -Algorithm SHA256).Hash.ToLowerInvariant();
      process_fixture = (Get-FileHash -LiteralPath $markerFiles[3] -Algorithm SHA256).Hash.ToLowerInvariant() }
    $identity = @{ schema = 1; role = 'app-marker-probe'; source_sha = $sha; source_tree = $sourceTree; configuration = 'RelWithDebInfo';
      source_dir = 's/scripts/windows/native_app_marker_probe'; build_tree = 'b/app-marker-probe';
      cmake_cache_sha256 = (Get-FileHash -LiteralPath $cache -Algorithm SHA256).Hash.ToLowerInvariant();
      qt_core_sha256 = (Get-FileHash -LiteralPath (Join-Path $qt 'bin/Qt6Core.dll') -Algorithm SHA256).Hash.ToLowerInvariant();
      executables_sha256 = $exeHashes }
    [IO.File]::WriteAllText((Join-Path $markerEvidence 'build-identity.json'), ($identity | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    Invoke-CiTempProbe 'before-marker-discovery'
    $markerCtest = Join-Path $tools 'cmake/bin/ctest.exe'
    $discoveryCode = Invoke-RecordedMarker 'discovery' $markerCtest @('--test-dir', $markerBuild, '-C', 'RelWithDebInfo', '--show-only=json-v1')
    if ($discoveryCode -eq 0) {
      $junit = Join-Path $markerEvidence 'junit.xml'
      $markerCode = Invoke-RecordedMarker 'execution' $markerCtest @('--test-dir', $markerBuild, '-C', 'RelWithDebInfo',
        '--no-tests=error', '--verbose', '--test-output-size-passed', '1073741824', '--test-output-size-failed', '1073741824',
        '--output-junit', $junit)
      if ($markerCode -ne 0 -or -not (Test-Path -LiteralPath $junit -PathType Leaf)) {
        Write-Warning 'App marker tests did not complete; real-App cases remain unapproved.'
      }
    } else { Write-Warning 'App marker discovery failed; real-App cases remain unapproved.' }
    } else { Write-Warning 'App marker cache is missing or differs; real-App cases remain unapproved.' }
  } else { Write-Warning 'App marker build is incomplete; real-App cases remain unapproved.' }
} else { Write-Host 'App marker source is absent; real-App cases remain unapproved.' }

$probe = Join-Path $i18n 'temp-probe'
Invoke-Checked $cmake @('-S', (Join-Path $source 'scripts/windows/native_temp_probe'), '-B', $probe,
  '-G', 'Ninja Multi-Config', "-DCMAKE_PREFIX_PATH=$qt", "-DCMAKE_MAKE_PROGRAM=$ninja")
Invoke-Checked $cmake @('--build', $probe, '--config', 'RelWithDebInfo', '--parallel', '2')
foreach ($tree in @($source, $qtRoot, $env:CONAN_HOME, $build, $i18n, $tools)) { Assert-RealTree $tree }

$planner = Join-Path $source 'scripts/windows/plan_native_stage.py'
foreach ($item in @(@{ Role = 'main'; Tree = $build }, @{ Role = 'i18n'; Tree = $i18n })) {
  $evidence = Join-Path $item.Tree 'native-kit'
  New-Item -ItemType Directory -Path $evidence -Force | Out-Null
  Invoke-Checked $builderPython @($planner, '--root', $root, '--logical-root', $root,
    '--source-sha', $sha, '--source-tree', $sourceTree, '--capture-identity', $item.Role,
    '--qt-version', $qtVersion, '--windows-sdk', $env:WindowsSDKVersion, '--msvc', $env:VCToolsVersion,
    '--output', (Join-Path $evidence 'build_identity.json'))
}

# The feedback plugin script verifies the official FFT archive and selects the
# APBIN binary emitted by this exact build. It never touches release assets.
$feedback = Join-Path $build 'feedback-plugins'
Invoke-Checked $builderPython @('-X', 'utf8', (Join-Path $source 'packaging/localization/prepare_feedback_tests.py'),
  '--source', $source, '--build', $build, '--config', 'RelWithDebInfo', '--output', $feedback)
$fftNotices = Join-Path $build 'feedback-fft-notices'
New-Item -ItemType Directory -Path $fftNotices | Out-Null
@'
from pathlib import Path
import hashlib, sys, urllib.request
url = 'https://raw.githubusercontent.com/PlotJuggler/pj-official-plugins/2bc991cae2dba7f9f1468dbf8dd72d89797699bc/LICENSE'
expected = '3701f21353125c50abb10b6a440148a00e41a43a10da994f6d240264030dfe2b'
with urllib.request.urlopen(url, timeout=120) as response:
    data = response.read(1048577)
if len(data) != 1071 or hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit('Pinned FFT source license did not match')
with (Path(sys.argv[1]) / 'LICENSE').open('xb') as output:
    output.write(data)
'@ | & $builderPython - $fftNotices
if ($LASTEXITCODE -ne 0) { throw 'Pinned FFT source license preparation failed.' }
$fonts = Join-Path $build 'ci-fonts'
New-Item -ItemType Directory -Path $fonts | Out-Null
@'
from pathlib import Path
import hashlib, sys, urllib.request
target = Path(sys.argv[1])
base = 'https://raw.githubusercontent.com/notofonts/noto-cjk/523d033d6cb47f4a80c58a35753646f5c3608a78/'
files = {
    'Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf': '2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b',
    'LICENSE': '6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2',
}
for relative, expected in files.items():
    with urllib.request.urlopen(base + relative, timeout=120) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit('Pinned test font or license SHA-256 mismatch: ' + relative)
    with (target / Path(relative).name).open('xb') as output:
        output.write(data)
'@ | & $builderPython - $fonts
if ($LASTEXITCODE -ne 0) { throw 'Pinned test font preparation failed.' }
$env:QT_QPA_FONTDIR = $fonts
$env:QT_PLUGIN_PATH = Join-Path $qt 'plugins'
$env:PJ_FEEDBACK_PLUGIN_DIR = $feedback
$env:PJ_APBIN_TEST_DIR = Join-Path $feedback 'ardupilot-dataflash'
$env:PJ_GUI_ACCEPTANCE_DIR = Join-Path $build 'gui-acceptance'
New-Item -ItemType Directory -Path $env:PJ_GUI_ACCEPTANCE_DIR | Out-Null
Invoke-CiTempProbe 'before-main-discovery'
$ctest = Join-Path $tools 'cmake/bin/ctest.exe'
$mainDiscovery = Join-Path $build 'native-kit/discovery.json'
$i18nDiscovery = Join-Path $i18n 'native-kit/discovery.json'
foreach ($item in @(@{ Tree = $build; Output = $mainDiscovery }, @{ Tree = $i18n; Output = $i18nDiscovery })) {
  $process = Start-Process -FilePath $ctest -ArgumentList @('--test-dir', $item.Tree, '-C', 'RelWithDebInfo',
    '--show-only=json-v1') -NoNewWindow -PassThru -Wait -RedirectStandardOutput $item.Output
  if ($process.ExitCode -ne 0) { throw "CTest discovery failed for $($item.Tree)." }
}
$hostSdk = @(& $builderPython -X utf8 -c "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from host_versions import read_host_versions; print(read_host_versions(Path(sys.argv[2]))['sdk_version'])" `
  (Join-Path $source 'packaging/localization') $source)
if ($LASTEXITCODE -ne 0 -or $hostSdk.Count -ne 1) { throw 'Cannot establish the host SDK version.' }
Invoke-Checked $builderPython @('-X', 'utf8', (Join-Path $source 'packaging/localization/run_csv_runtime_acceptance.py'),
  '--build', $build, '--prefix', $csvPrefix, '--capture-prebuilt', (Join-Path $build 'native-kit/csv-prebuilt.json'),
  '--source-sha', $sha, '--source-tree', $sourceTree, '--kit-root', $root, '--qt-dir', $qt, '--ctest', $ctest,
  '--qt-version', $qtVersion, '--host-sdk', $hostSdk[0].Trim())

$candidate = Join-Path $build 'native-kit/stage-candidate.json'
$gapReport = Join-Path $build 'native-kit/stage-gaps.json'
if (Test-Path -LiteralPath (Join-Path $mutationEvidence 'INCOMPLETE')) { throw 'Linked marker mutation sentinel forbids staging.' }
$reviewedPolicy = Join-Path $source '.github/windows-native-kit/ci-closure-policy.json'
$closureVerifier = Join-Path $source 'scripts/windows/verify_native_ci_closure.py'
$havePolicy = Test-Path -LiteralPath $reviewedPolicy -PathType Leaf
$haveVerifier = Test-Path -LiteralPath $closureVerifier -PathType Leaf
if ($havePolicy -ne $haveVerifier) { throw 'The source-reviewed closure policy and verifier must be supplied together.' }
$candidateArguments = @('--root', $root, '--logical-root', $root, '--source-sha', $sha, '--source-tree', $sourceTree,
  '--discovery', "main=$mainDiscovery", '--discovery', "i18n=$i18nDiscovery", '--output', $candidate, '--report', $gapReport)
if ($havePolicy) {
  foreach ($file in @('.github/windows-native-kit/ci-closure-policy.json', 'scripts/windows/verify_native_ci_closure.py')) {
    & git.exe -C $source ls-files --error-unmatch -- $file | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Closure input is not tracked by the exact source commit: $file" }
  }
  Invoke-Checked $builderPython @('-I', '-B', $planner, '--root', $root, '--logical-root', $root,
    '--source-sha', $sha, '--source-tree', $sourceTree, '--check-generated-media', '--output', $mediaReceipt)
  $reviewed = Get-Content -LiteralPath $reviewedPolicy -Raw | ConvertFrom-Json
  if ($reviewed.schema -ne 2 -or $reviewed.verifier_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
      (Get-FileHash -LiteralPath $closureVerifier -Algorithm SHA256).Hash.ToLowerInvariant() -cne $reviewed.verifier_sha256) {
    throw 'Source-reviewed closure policy does not pin the actual declarations verifier.'
  }
  $declarations = Join-Path $build 'native-kit/runtime-declarations.json'
  if (Test-Path -LiteralPath $declarations) { throw 'Refusing to reuse runtime declarations.' }
  Invoke-Checked $builderPython @('-I', '-B', $closureVerifier, '--prepare-declarations', '--root', $root,
    '--source-sha', $sha, '--source-tree', $sourceTree, '--reviewed-policy', $reviewedPolicy, '--output', $declarations)
  if (-not (Test-Path -LiteralPath $declarations -PathType Leaf)) { throw 'Reviewed runtime declarations were not generated.' }
  $candidateArguments += @('--declarations', $declarations)
}
& $builderPython -I -B $planner @candidateArguments
if ($LASTEXITCODE -ne 2) { throw "Stage candidate generation failed with exit code $LASTEXITCODE." }
if ($havePolicy) {
  $capture = Get-Content -LiteralPath (Join-Path $codemodelEvidence 'capture.json') -Raw | ConvertFrom-Json
  if ($capture.index -cnotmatch '^b/native-kit/codemodel/reply/index-[A-Za-z0-9_.-]+\.json$') {
    throw 'The retained CMake File API index path is invalid.'
  }
  $selectionPath = Join-Path $codemodelEvidence 'selection.json'
  Invoke-Checked $builderPython @('-I', '-B', $planner, '--root', $root, '--logical-root', $root,
    '--source-sha', $sha, '--source-tree', $sourceTree, '--select-codemodel-rules',
    '--candidate-plan', $candidate, '--report', $gapReport, '--reviewed-policy', $reviewedPolicy,
    '--output', $selectionPath)
  $selection = Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json
  if ($selection.schema -ne 1 -or $selection.source_sha -cne $sha -or $selection.source_tree -cne $sourceTree) {
    throw 'The source-reviewed CMake File API rule selection differs.'
  }
  foreach ($entry in $selection.rules) {
    if ($entry.rule -cnotin @('runtime-catalog-language', 'extension-manager') -or
        $entry.status -cnotin @('selected', 'not_selected')) { throw 'Unknown CMake File API rule selection.' }
    if ($entry.status -cne 'selected') { continue }
    $result = Join-Path $codemodelEvidence ('verified-' + $entry.rule + '.json')
    Invoke-Checked $builderPython @('-I', '-B', $closureVerifier, '--verify-codemodel', '--root', $root,
      '--source-sha', $sha, '--source-tree', $sourceTree, '--reviewed-policy', $reviewedPolicy,
      '--candidate-plan', $candidate, '--codemodel-index', $capture.index, '--codemodel-rule', $entry.rule,
      '--output', $result)
  }
}
$gaps = Get-Content -LiteralPath $gapReport -Raw | ConvertFrom-Json
Write-Host 'Unclosed candidate inputs:'
foreach ($gap in $gaps.blockers) { Write-Host "$($gap.code): $($gap.suite) $($gap.case) $($gap.detail)" }
Write-Host 'Not-executed case inventory:'
foreach ($item in $gaps.coverage) { Write-Host "$($item.suite) $($item.case) $($item.status): $($item.reason)" }
$kitParent = Split-Path -Parent $base
$stagingParent = Join-Path $kitParent 'staging'
$archiveParent = Join-Path $kitParent 'archives'
foreach ($directory in @($stagingParent, $archiveParent)) {
  if (-not (Test-Path -LiteralPath $directory)) { New-Item -ItemType Directory -Path $directory | Out-Null }
  Assert-RealDirectory $directory
}
$staging = Join-Path $stagingParent $sourcePrefix
$kitArchive = Join-Path $archiveParent 'windows-native-kit.zip'
$packageReceipt = Join-Path $build 'native-kit/package-receipt.json'
& $builderPython -I -B $planner --root $root --logical-root $root --source-sha $sha --source-tree $sourceTree `
  --output $candidate --report $gapReport --package --staging $staging --archive $kitArchive --package-receipt $packageReceipt
if ($LASTEXITCODE -ne 0) { throw "Native staging refused: consult $gapReport and the specific closure error above." }
$package = Get-Content -LiteralPath $packageReceipt -Raw | ConvertFrom-Json
if ($package.status -cne 'staged-awaiting-independent-ci' -or $package.source_sha -cne $sha -or
    $package.source_tree -cne $sourceTree -or $package.archive_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    $package.manifest_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $package.archive_bytes -le 0 -or $package.expanded_bytes -le 0 -or
    (Get-FileHash -LiteralPath $kitArchive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $package.archive_sha256) {
  throw 'Staged ZIP receipt differs from the actual archive or source identity.'
}
if (-not $env:GITHUB_OUTPUT) { throw 'GitHub step output destination is missing.' }
$outputLines = @("archive_path=$kitArchive", "archive_sha256=$($package.archive_sha256)",
  "manifest_sha256=$($package.manifest_sha256)", "archive_bytes=$($package.archive_bytes)",
  "expanded_bytes=$($package.expanded_bytes)", "source_sha=$sha", "source_tree=$sourceTree")
[IO.File]::AppendAllText($env:GITHUB_OUTPUT, (($outputLines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
Write-Host 'An unverified ZIP was staged. The independent bootstrap and real CI groups must succeed before upload.'
