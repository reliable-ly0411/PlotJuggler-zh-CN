#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Synthetic adversarial ZIP checks for the independently trusted bootstrap.

The cross-platform checks run without Windows. On Windows, the adversarial ZIPs
are fed to the verifier's actual compiled .NET routines in a temporary tree.
The optional full fixed-root test creates a fresh, uniquely named destination
and intentionally leaves it intact. Set PJ_ALLOW_BOOTSTRAP_INTEGRATION=1 only
on an isolated, disposable Windows machine to permit that filesystem change.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/windows/bootstrap_native_test_kit.ps1'
SHA = 'a' * 40
TREE = 'b' * 40
CONFIG = 'RelWithDebInfo'
LOGICAL = r'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\n' + '\\' + SHA[:12]
REQUIRED = (
    't/python/python.exe', 't/python/python3.dll', 't/python/python312.dll', 't/python/python312.zip',
    't/python/python312._pth',
    's/scripts/windows/run_native_test_bundle.py', 's/scripts/windows/native_bundle_audit.py',
    's/scripts/windows/native_test_review.py', '_bundle/origins.json', 'licenses/LICENSE.txt',
)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def pth_lines(source=SHA):
    root = LOGICAL[:-12] + source[:12]
    return ['python312.zip', '.', root + r'\s', root + r'\s\scripts',
            root + r'\s\tests', root + r'\s\packaging\localization']

def pth_bytes(lines):
    return ('# synthetic isolated CPython paths\r\n' + '\r\n'.join(lines[:2]) +
            '\r\n\r\n# import site\r\n' + '\r\n'.join(lines[2:]) + '\r\n').encode('utf-8')

def sample(source=SHA):
    files = {p: ('synthetic bytes for ' + p).encode() for p in REQUIRED}
    files['t/python/python312._pth'] = pth_bytes(pth_lines(source))
    files['_bundle/origins.json'] = json.dumps({'schema': 1, 'origins': {
        'synthetic': {'license_files': ['licenses/LICENSE.txt']}}}).encode()
    dirs = set()
    for name in files:
        parent = Path(name).parent.as_posix()
        while parent != '.':
            dirs.add(parent)
            parent = Path(parent).parent.as_posix()
    dirs.update(('s/tests', 's/packaging', 's/packaging/localization'))
    names = ('cmake', 'ctest', 'python', 'embedded-cpython', 'lrelease', 'lupdate', 'rcc', 'ifw', '7z')
    manifest = {'schema': 1, 'logical_root': LOGICAL[:-12] + source[:12],
                'provenance': {'source_sha': source, 'source_tree': TREE, 'workflow_sha': 'c' * 40,
                  'source_clean': True, 'configuration': CONFIG, 'qt': '6.12.0', 'sdk': '0.39.0',
                  'windows_sdk': 'synthetic', 'compiler': 'synthetic', 'generator': 'Ninja Multi-Config',
                  'runner_image': 'synthetic', 'conan_lock_sha256': 'd' * 64, 'conan_graph_sha256': 'e' * 64,
                  'submodules': {'synthetic': 'f' * 40}, 'tools': [
                      {'name': n, 'version': '1', 'origin': 'https://example.org/synthetic', 'sha256': '0' * 64}
                      for n in names]},
                'files': [{'path': p, 'bytes': len(data), 'sha256': digest(data), 'mtime_ns': 1700000000000000000}
                          for p, data in sorted(files.items())], 'directories': sorted(dirs)}
    return files, manifest

def write_zip(path, files, manifest, *, extra=(), modes=None, raw_manifest=None, omit_directory=None):
    modes = modes or {}
    raw_manifest = raw_manifest if raw_manifest is not None else json.dumps(manifest).encode()
    with warnings.catch_warnings(), zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        warnings.simplefilter('ignore', UserWarning)
        for directory in manifest['directories']:
            if directory == omit_directory:
                continue
            info = zipfile.ZipInfo(directory + '/')
            info.external_attr = (stat.S_IFDIR | 0o755) << 16 | 0x10
            z.writestr(info, b'')
        for name, data in [*files.items(), ('_bundle/manifest.json', raw_manifest), *extra]:
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            default_mode = ((stat.S_IFDIR | 0o755) << 16 | 0x10) if name.endswith('/') else ((stat.S_IFREG | 0o644) << 16)
            info.external_attr = modes.get(name, default_mode)
            z.writestr(info, data)
    return digest(raw_manifest)

def corrupt_claimed_uncompressed_size(path, target):
    data = bytearray(path.read_bytes())
    offset = 0
    while True:
        offset = data.find(b'PK\x01\x02', offset)
        if offset < 0:
            raise AssertionError('central entry not found')
        name_len, extra_len, comment_len = struct.unpack_from('<HHH', data, offset + 28)
        name = bytes(data[offset + 46:offset + 46 + name_len]).decode()
        if name == target:
            actual, = struct.unpack_from('<I', data, offset + 24)
            struct.pack_into('<I', data, offset + 24, actual + 1)
            path.write_bytes(data)
            return
        offset += 46 + name_len + extra_len + comment_len

def make_cases(directory):
    cases = []
    def add(name, mutate=None, extra=(), modes=None, raw=None, wrong_hash=False, corrupt=False, accept=False, omit_directory=None, reason=None):
        files, manifest = sample()
        if mutate:
            mutate(files, manifest)
        path = directory / (name + '.zip')
        raw_bytes = raw(manifest) if raw else None
        mhash = write_zip(path, files, manifest, extra=extra, modes=modes, raw_manifest=raw_bytes, omit_directory=omit_directory)
        if corrupt:
            corrupt_claimed_uncompressed_size(path, 't/python/python.exe')
        cases.append({'name': name, 'zip': str(path), 'manifest_sha': '0'*64 if wrong_hash else mhash,
                      'accept': accept, 'root': LOGICAL, 'sha': SHA, 'tree': TREE, 'reason': reason})
    add('valid', accept=True)
    zip64_limit = zipfile.ZIP64_LIMIT
    try:
        zipfile.ZIP64_LIMIT = 100
        add('valid_zip64', accept=True)
    finally:
        zipfile.ZIP64_LIMIT = zip64_limit
    add('wrong_manifest_hash', wrong_hash=True)
    add('trailing_bytes')
    with (directory / 'trailing_bytes.zip').open('ab') as f:
        f.write(b'unlisted trailer')
    add('lying_entry_count')
    count_path = directory / 'lying_entry_count.zip'
    count_data = bytearray(count_path.read_bytes())
    count, = struct.unpack_from('<H', count_data, len(count_data) - 22 + 10)
    struct.pack_into('<HH', count_data, len(count_data) - 22 + 8, count - 1, count - 1)
    count_path.write_bytes(count_data)
    add('traversal', extra=[('../escape', b'x')])
    add('absolute_path', extra=[('/escape', b'x')])
    add('ads', extra=[('t/python/python.exe:evil', b'x')])
    add('device_name', extra=[('licenses/COM1.txt', b'x')])
    add('long_path', extra=[('s/' + 'x'*190, b'x')])
    add('duplicate_file', extra=[('t/python/python.exe', b'duplicate')])
    add('case_collision', extra=[('t/Python/fake', b'x')])
    add('extra_directory', extra=[('unexpected/', b'')])
    add('extra_file', extra=[('unlisted.txt', b'x')])
    add('missing_zip_directory', omit_directory='licenses')
    add('missing_zip_file', mutate=lambda f, m: f.pop('t/python/python3.dll'))
    def absent_interpreter_pth(files, manifest):
        files.pop('t/python/python312._pth')
        manifest['files'] = [item for item in manifest['files'] if item['path'] != 't/python/python312._pth']
    add('missing_interpreter_pth', mutate=absent_interpreter_pth, reason='required interpreter or verifier input missing')

    def pth_change(contents):
        def change(files, manifest):
            name = 't/python/python312._pth'
            files[name] = contents
            record = next(item for item in manifest['files'] if item['path'] == name)
            record['bytes'], record['sha256'] = len(contents), digest(contents)
        return change
    lines = pth_lines()
    reason_import = 'interpreter path file contains an import directive'
    reason_path = 'interpreter path entry differs from the allowlist'
    add('pth_active_site', mutate=pth_change(pth_bytes(lines) + b'import site\n'), reason=reason_import)
    add('pth_active_other_import', mutate=pth_change(pth_bytes(lines) + b'import os\n'), reason=reason_import)
    add('pth_import_tab', mutate=pth_change(pth_bytes(lines) + b'import\tsite\n'), reason=reason_import)
    external = list(lines); external[4] = r'C:\Windows\System32'
    add('pth_external_path', mutate=pth_change(pth_bytes(external)), reason=reason_path)
    unc = list(lines); unc[4] = r'\\server\share'
    add('pth_unc_path', mutate=pth_change(pth_bytes(unc)), reason='interpreter path entry is not a safe relative path')
    drive_relative = list(lines); drive_relative[4] = r'C:untrusted'
    add('pth_drive_relative', mutate=pth_change(pth_bytes(drive_relative)), reason='interpreter path entry is not a safe relative path')
    ads = list(lines); ads[4] += ':stream'
    add('pth_ads_path', mutate=pth_change(pth_bytes(ads)), reason='interpreter path entry has an alternate stream')
    escape = list(lines); escape[3] = r'..\..\..\outside'
    add('pth_relative_escape', mutate=pth_change(pth_bytes(escape)), reason=reason_path)
    add('pth_missing_entry', mutate=pth_change(pth_bytes(lines[:-1])), reason='interpreter path file is missing an allowlisted entry')
    reordered = list(lines); reordered[3], reordered[4] = reordered[4], reordered[3]
    add('pth_reordered', mutate=pth_change(pth_bytes(reordered)), reason=reason_path)
    add('pth_extra_entry', mutate=pth_change(pth_bytes(lines + [lines[2]])), reason='interpreter path entry is unsafe or extra')
    add('pth_invalid_utf8', mutate=pth_change(pth_bytes(lines) + b'# invalid \xff\n'), reason='interpreter path file is not strict UTF-8')
    add('pth_nul_byte', mutate=pth_change(pth_bytes(lines) + b'# hidden \x00\n'), reason='interpreter path file has a control character')
    add('pth_empty', mutate=pth_change(b''), reason='interpreter path file size is invalid')
    add('pth_bare_cr', mutate=pth_change(pth_bytes(lines).replace(b'\r\n', b'\r')), reason='interpreter path file has an unsupported line ending')
    add('pth_oversized', mutate=pth_change(pth_bytes(lines) + b'#' + b'x' * 32768), reason='interpreter path file size is invalid')
    case_lines = [lines[0].upper(), *lines[1:2], *(entry.upper() for entry in lines[2:])]
    add('pth_windows_case', mutate=pth_change(pth_bytes(case_lines)), accept=True)
    rel_lines = lines[:2] + [r'..\..\s', r'..\..\s\scripts', r'..\..\s\tests', r'..\..\s\packaging\localization']
    add('pth_same_root_relative', mutate=pth_change(pth_bytes(rel_lines)), accept=True)
    def absent_search_directory(files, manifest):
        manifest['directories'].remove('s/tests')
    add('pth_unmanifested_search_directory', mutate=absent_search_directory,
        reason='interpreter search directory is not in the manifest')
    add('symlink', modes={'licenses/LICENSE.txt': (stat.S_IFLNK | 0o777) << 16})
    add('reparse_attribute', modes={'licenses/LICENSE.txt': ((stat.S_IFREG | 0o644) << 16) | 0x400})
    add('claimed_size', corrupt=True)
    add('tampered_file', mutate=lambda f, m: f.__setitem__('t/python/python.exe', b'X' * len(f['t/python/python.exe'])))
    add('wrong_tree', mutate=lambda f, m: m['provenance'].__setitem__('source_tree', 'c' * 40))
    add('wrong_root', mutate=lambda f, m: m.__setitem__('logical_root', r'C:\elsewhere\n' + '\\' + SHA[:12]))
    add('wrong_config', mutate=lambda f, m: m['provenance'].__setitem__('configuration', 'Release'))
    add('missing_field', mutate=lambda f, m: m['provenance'].pop('source_clean'))
    add('duplicate_json_key', raw=lambda m: json.dumps(m).replace('{"schema": 1,', '{"schema": 1, "schema": 1,', 1).encode())
    add('case_duplicate_json_key', raw=lambda m: json.dumps(m).replace('{"schema": 1,', '{"schema": 1, "SCHEMA": 1,', 1).encode())
    add('nonintegral_mtime', mutate=lambda f, m: m['files'][0].__setitem__('mtime_ns', 1700000000000000001))
    add('oversized_claim', mutate=lambda f, m: m['files'][0].__setitem__('bytes', 8 * 1024**3 + 1))
    def absent_license(files, manifest):
        files['_bundle/origins.json'] = json.dumps({'schema': 1, 'origins': {'fake': {'license_files': ['licenses/absent.txt']}}}).encode()
        rec = next(x for x in manifest['files'] if x['path'] == '_bundle/origins.json')
        rec['bytes'] = len(files['_bundle/origins.json'])
        rec['sha256'] = digest(files['_bundle/origins.json'])
    add('missing_origin_license', mutate=absent_license)
    return cases

# Exercises the embedded verifier's real parsers, ZIP matching, bounded stream
# extraction, SHA checks, and origin/license checks, without touching the fixed
# destination. It does not stand in for the optional full NTFS integration test.
HARNESS = r'''
param([string]$CodePath, [string]$CasesPath, [string]$OutputRoot)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$compileTemp = Join-Path $OutputRoot 'bootstrap-compile'
[void][IO.Directory]::CreateDirectory($compileTemp)
$env:TEMP = $compileTemp; $env:TMP = $compileTemp
$parameters = New-Object System.CodeDom.Compiler.CompilerParameters
$parameters.GenerateInMemory = $true
$parameters.TempFiles = [System.CodeDom.Compiler.TempFileCollection]::new($compileTemp, $true)
foreach ($name in @('System.dll','System.Core.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll')) {
  [void]$parameters.ReferencedAssemblies.Add($name)
}
Add-Type -TypeDefinition ([IO.File]::ReadAllText($CodePath)) -CompilerParameters $parameters
$t = [NativeKitBootstrap]
$flags = [Reflection.BindingFlags]::Static -bor [Reflection.BindingFlags]::NonPublic
$membersMethod = $t.GetMethod('Members',$flags); $small = $t.GetMethod('ReadSmall',$flags)
$modelMethod = $t.GetMethod('ReadModel',$flags); $match = $t.GetMethod('MatchMembers',$flags)
$extract = $t.GetMethod('ExtractFile',$flags); $origins = $t.GetMethod('VerifyOrigins',$flags); $bounds = $t.GetMethod('ZipBounds',$flags); $pthCheck = $t.GetMethod('ValidateInterpreterPathBytes',$flags)
$cases = [IO.File]::ReadAllText($CasesPath) | ConvertFrom-Json
foreach ($case in $cases) {
  $accepted = $false; $z = $null; $reason = ''
  try {
    $inputStream = [IO.File]::OpenRead([string]$case.zip)
    try { $a=New-Object object[] 1; $a[0]=$inputStream; [void]$bounds.Invoke($null,$a) } finally { $inputStream.Dispose() }
    $z = [IO.Compression.ZipFile]::OpenRead([string]$case.zip)
    $a = New-Object object[] 2; $a[0]=$z; $a[1]=[string]$case.root
    $members = $membersMethod.Invoke($null,$a)
    $a = New-Object object[] 1; $a[0]=$members['_bundle/manifest.json']
    [byte[]]$manifest = $small.Invoke($null,$a)
    $h=[Security.Cryptography.SHA256]::Create(); try { $actual=-join ($h.ComputeHash($manifest) | ForEach-Object { $_.ToString('x2') }) } finally { $h.Dispose() }
    if ($actual -cne $case.manifest_sha) { throw 'manifest hash differs' }
    $a = New-Object object[] 5; $a[0]=$manifest; $a[1]=[string]$case.root; $a[2]=[string]$case.sha; $a[3]=[string]$case.tree; $a[4]='RelWithDebInfo'
    $model = $modelMethod.Invoke($null,$a)
    $a = New-Object object[] 2; $a[0]=$model; $a[1]=$members; [void]$match.Invoke($null,$a)
    $dir = Join-Path $OutputRoot ([string]$case.name); [void][IO.Directory]::CreateDirectory($dir)
    foreach ($record in $model.Files.Values) {
      $dest = Join-Path $dir ($record.Name.Replace('/','\'))
      [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dest))
      $a = New-Object object[] 3; $a[0]=$members[$record.Name]; $a[1]=$dest; $a[2]=[long]$record.Size
      $hash = [string]$extract.Invoke($null,$a)
      if ($hash -cne $record.Sha) { throw 'file hash differs' }
    }
    [byte[]]$pthBytes = [IO.File]::ReadAllBytes((Join-Path $dir 't\python\python312._pth'))
    if ($null -eq $pthBytes) { $pthBytes = [byte[]]::new(0) }
    $a=New-Object object[] 3; $a[0]=$pthBytes; $a[1]=[string]$case.root; $a[2]=$model; [void]$pthCheck.Invoke($null,$a)
    $a=New-Object object[] 2; $a[0]=$dir; $a[1]=$model; [void]$origins.Invoke($null,$a)
    $accepted = $true
  } catch { $accepted = $false; $reason = $_.Exception.GetBaseException().Message } finally { if ($z) { $z.Dispose() } }
  Write-Output ($case.name + '=' + $accepted.ToString().ToLowerInvariant())
  if ($case.reason) { Write-Output ($case.name + '_reason=' + $reason) }
}
# These use only synthetic paths under the test temporary directory.
$streams = $t.GetMethod('Streams',$flags); $lockdir = $t.GetMethod('LockDirectory',$flags)
$probe = Join-Path $OutputRoot 'stream-probe.txt'; [IO.File]::WriteAllText($probe,'synthetic')
$a = New-Object object[] 2; $a[0]=$probe; $a[1]=$false; [void]$streams.Invoke($null,$a)
Set-Content -LiteralPath $probe -Stream 'untrusted' -Value 'synthetic named stream'
$rejected=$false; try { [void]$streams.Invoke($null,$a) } catch { $rejected=$true }
Write-Output ('named_stream_rejected=' + $rejected.ToString().ToLowerInvariant())
$target = Join-Path $OutputRoot 'junction-target'; [void][IO.Directory]::CreateDirectory($target)
$link = Join-Path $OutputRoot 'junction'; [void](New-Item -ItemType Junction -Path $link -Target $target)
$a = New-Object object[] 1; $a[0]=$link
$rejected=$false; try { $handle=$lockdir.Invoke($null,$a); if ($handle) { $handle.Dispose() } } catch { $rejected=$true }
Write-Output ('junction_rejected=' + $rejected.ToString().ToLowerInvariant())
'''


# The optional fixed-root test compiles the exact verifier once and calls Run
# twice within one controlled process. It leaves every created file in place.
FULL_ROOT_HARNESS = r'''
param([string]$CodePath, [string]$Archive, [string]$ArchiveSha256, [string]$ManifestSha256,
      [string]$SourceSha, [string]$SourceTree, [string]$Configuration, [string]$TrustedTemp)
$ErrorActionPreference = 'Stop'
$expectedHost = [IO.Path]::Combine([Environment]::SystemDirectory, 'WindowsPowerShell', 'v1.0', 'powershell.exe')
if (-not [Environment]::Is64BitProcess -or $PSVersionTable.PSEdition -ne 'Desktop' -or
    $PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1 -or
    -not [string]::Equals([Diagnostics.Process]::GetCurrentProcess().MainModule.FileName, $expectedHost, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Use 64-bit Microsoft system Windows PowerShell 5.1'
}
$expectedTemp = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\bootstrap-temp\' + $SourceSha.Substring(0,12)
if ($TrustedTemp -cne $expectedTemp -or $env:TEMP -cne $TrustedTemp -or $env:TMP -cne $TrustedTemp -or
    [IO.Path]::GetTempPath().TrimEnd([char]'\') -cne $TrustedTemp -or
    [IO.Directory]::GetFileSystemEntries($TrustedTemp).Length -ne 0) { throw 'Untrusted compiler temporary directory' }
$assemblies = @(
    [Reflection.Assembly]::Load('System, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
    [Reflection.Assembly]::Load('System.Core, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
    [Reflection.Assembly]::Load('System.IO.Compression, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
    [Reflection.Assembly]::Load('System.IO.Compression.FileSystem, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
)
foreach ($assembly in $assemblies) {
    if (-not $assembly.GlobalAssemblyCache -or -not $assembly.Location) { throw 'Framework assembly is not in the GAC' }
}
$parameters = New-Object System.CodeDom.Compiler.CompilerParameters
$parameters.GenerateInMemory = $true; $parameters.IncludeDebugInformation = $false
$parameters.TempFiles = [System.CodeDom.Compiler.TempFileCollection]::new($TrustedTemp, $true)
foreach ($assembly in $assemblies) { [void]$parameters.ReferencedAssemblies.Add($assembly.Location) }
Add-Type -TypeDefinition ([IO.File]::ReadAllText($CodePath)) -CompilerParameters $parameters
$first = [NativeKitBootstrap]::Run($Archive, $ArchiveSha256, $ManifestSha256, $SourceSha, $SourceTree, $Configuration, $TrustedTemp)
$receipt = $first | ConvertFrom-Json
$expectedRoot = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\n\' + $SourceSha.Substring(0,12)
if ($receipt.status -cne 'verified' -or $receipt.logical_root -cne $expectedRoot -or
    -not [IO.Directory]::Exists($expectedRoot)) { throw 'First Run did not create the expected target' }
$failure = $null
try { [void][NativeKitBootstrap]::Run($Archive, $ArchiveSha256, $ManifestSha256, $SourceSha, $SourceTree, $Configuration, $TrustedTemp) }
catch { $failure = $_.Exception.GetBaseException().Message }
if ($failure -cne 'destination already exists') { throw ('Second Run did not reject the existing target: ' + $failure) }
[Console]::Out.WriteLine($first)
[Console]::Out.WriteLine('reuse_rejected=' + $failure)
'''

class StaticBootstrapTests(unittest.TestCase):
    def test_trust_boundary_and_explicit_guards(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertTrue(text.isascii(), 'Windows PowerShell 5.1 must read script bytes unambiguously')
        required = text.split('static readonly string[] Required = {', 1)[1].split('};', 1)[0]
        self.assertIn('\"t/python/python312._pth\"', required)
        for needle in ('t/python/python312._pth', 'ZipArchiveMode.Read', 'archive SHA-256 differs', 'manifest SHA-256 differs',
                       'FileMode.CreateNew', 'FindFirstStreamW', 'FindNextStreamW', 'GetFinalPathNameByHandleW',
                       'GetFileInformationByHandle', 'source identity differs', 'configuration differs',
                       'origin license is not in verified payload', 'verified_manifest_values_restored',
                       'kit_code_executed', 'new DriveInfo("C").AvailableFreeSpace', 'ZipBounds(f)', 'CompilerParameters', 'TrustedTemp', 'VerifyInterpreterPathFile(root,model)'):
            self.assertIn(needle, text)
        self.assertNotIn('ExecutionPolicy Bypass', text)
        self.assertNotIn('Start-Process', text)
        self.assertNotIn('Remove-Item', text)
        self.assertLess(text.index('Check(Hash(f)==archiveSha'), text.index('RootDirectories(root,held)'))
        self.assertLess(text.index('foreach (FileRecord record in model.Files.Values) VerifyFile('),
                        text.index('VerifyInterpreterPathFile(root,model)'))
        self.assertLess(text.index('VerifyInterpreterPathFile(root,model)'), text.index('File.SetLastWriteTimeUtc'))
        self.assertEqual(text.count('VerifyInterpreterPathFile(root,model);'), 2)
        self.assertLess(text.index('VerifyFile(manifestPath,manifest.Length,manifestSha,null)'), text.index('File.SetLastWriteTimeUtc'))

    def test_reuse_control_uses_one_compiled_verifier_and_exact_error(self):
        self.assertEqual(FULL_ROOT_HARNESS.count('Add-Type -TypeDefinition'), 1)
        self.assertEqual(FULL_ROOT_HARNESS.count('[NativeKitBootstrap]::Run('), 2)
        self.assertIn("$failure -cne 'destination already exists'", FULL_ROOT_HARNESS)
        self.assertIn('[IO.Directory]::Exists($expectedRoot)', FULL_ROOT_HARNESS)
        self.assertIn("WriteLine('reuse_rejected=' + $failure)", FULL_ROOT_HARNESS)

    def test_fixtures_cover_positive_and_malformed_zips(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = make_cases(Path(tmp))
            self.assertGreaterEqual(len(cases), 20)
            self.assertEqual([x['name'] for x in cases if x['accept']],
                             ['valid', 'valid_zip64', 'pth_windows_case', 'pth_same_root_relative'])
            with zipfile.ZipFile(Path(tmp) / 'valid.zip') as z:
                manifest = json.loads(z.read('_bundle/manifest.json'))
                self.assertEqual(manifest['logical_root'], LOGICAL)
                self.assertEqual(set(manifest['directories']), {x.filename[:-1] for x in z.infolist() if x.is_dir()})
                self.assertEqual(digest(z.read('_bundle/manifest.json')), cases[0]['manifest_sha'])
                self.assertIn('t/python/python312._pth', {x['path'] for x in manifest['files']})
            with zipfile.ZipFile(Path(tmp) / 'missing_interpreter_pth.zip') as z:
                omitted = json.loads(z.read('_bundle/manifest.json'))
                self.assertNotIn('t/python/python312._pth', z.namelist())
                self.assertNotIn('t/python/python312._pth', {x['path'] for x in omitted['files']})
            # Each semantic negative is self-consistently hashed in its own
            # manifest, so the C# path check, not a prior digest error, must fail.
            semantic = [case for case in cases if case['name'].startswith('pth_')]
            self.assertGreaterEqual(len(semantic), 15)
            for case in semantic:
                with self.subTest(case=case['name']), zipfile.ZipFile(case['zip']) as z:
                    parsed = json.loads(z.read('_bundle/manifest.json'))
                    record = next(x for x in parsed['files'] if x['path'] == 't/python/python312._pth')
                    contents = z.read('t/python/python312._pth')
                    self.assertEqual((record['bytes'], record['sha256']), (len(contents), digest(contents)))
                    self.assertEqual(digest(z.read('_bundle/manifest.json')), case['manifest_sha'])

@unittest.skipUnless(os.name == 'nt', 'actual .NET ZIP and NTFS tests require Windows')
class WindowsVerifierTests(unittest.TestCase):
    def test_actual_embedded_verifier_rejects_malformed_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            cases = make_cases(directory)
            (directory / 'cases.json').write_text(json.dumps(cases), encoding='utf-8')
            text = SCRIPT.read_text(encoding='utf-8')
            code = text.split("    $code = @'\n", 1)[1].split("\n'@", 1)[0]
            (directory / 'bootstrap.cs').write_text(code, encoding='utf-8')
            (directory / 'harness.ps1').write_text(HARNESS, encoding='utf-8')
            system_ps = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            compile_temp = directory / 'out' / 'bootstrap-compile'
            compile_temp.mkdir(parents=True)
            process_env = dict(os.environ, TEMP=str(compile_temp), TMP=str(compile_temp))
            result = subprocess.run([str(system_ps), '-NoProfile', '-NonInteractive', '-File', str(directory / 'harness.ps1'),
                                     str(directory / 'bootstrap.cs'), str(directory / 'cases.json'), str(directory / 'out')],
                                    capture_output=True, text=True, timeout=180, env=process_env)
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = dict(line.strip().split('=', 1) for line in result.stdout.splitlines() if '=' in line)
            expected = {c['name']: str(c['accept']).lower() for c in cases}
            expected.update({c['name'] + '_reason': c['reason'] for c in cases if c['reason']})
            expected.update(named_stream_rejected='true', junction_rejected='true')
            self.assertEqual(observed, expected, result.stdout + result.stderr)

    @unittest.skipUnless(os.environ.get('PJ_ALLOW_BOOTSTRAP_INTEGRATION') == '1',
                         'full fixed-root extraction requires an explicitly opted-in disposable Windows host')
    def test_full_fixed_root_and_refuse_reuse(self):
        # Never deletes the fixed-root output. A successful receipt leaves a
        # uniquely named synthetic directory for manual host disposal.
        source = os.environ.get('PJ_BOOTSTRAP_TEST_SOURCE_SHA', '')
        self.assertRegex(source, r'^[0-9a-f]{40}$')
        trusted_temp = Path(r'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a') / 'bootstrap-temp' / source[:12]
        self.assertTrue(trusted_temp.is_dir(), 'operator must independently inspect and create the exact empty compiler directory')
        self.assertFalse(any(trusted_temp.iterdir()), 'compiler directory must be fresh')
        files, manifest = sample(source)
        target = Path(LOGICAL[:-12] + source[:12])
        self.assertFalse(os.path.lexists(target), 'target must not preexist; no old data will be touched')
        # Keep the compiler temp empty until PowerShell starts. Place all newly
        # created inputs in a fresh sibling under the same test root, and leave
        # both input and extracted trees intact for later inspection.
        inputs = trusted_temp.parent / ('integration-input-' + source[:12])
        inputs.mkdir(exist_ok=False)
        path = inputs / 'synthetic.zip'
        with path.open('xb') as stream:
            manifest_hash = write_zip(stream, files, manifest)
        text = SCRIPT.read_text(encoding='utf-8')
        code = text.split("    $code = @'\n", 1)[1].split("\n'@", 1)[0]
        code_path, harness_path = inputs / 'bootstrap.cs', inputs / 'fixed-root-harness.ps1'
        with code_path.open('x', encoding='utf-8') as stream:
            stream.write(code)
        with harness_path.open('x', encoding='utf-8') as stream:
            stream.write(FULL_ROOT_HARNESS)
        system_ps = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        args = [str(system_ps), '-NoProfile', '-NonInteractive', '-File', str(harness_path),
                '-CodePath', str(code_path), '-Archive', str(path), '-ArchiveSha256', digest(path.read_bytes()),
                '-ManifestSha256', manifest_hash, '-SourceSha', source, '-SourceTree', TREE,
                '-Configuration', CONFIG, '-TrustedTemp', str(trusted_temp)]
        process_env = dict(os.environ, TEMP=str(trusted_temp), TMP=str(trusted_temp))
        result = subprocess.run(args, capture_output=True, text=True, timeout=180, env=process_env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 2, result.stdout)
        receipt = json.loads(lines[0])
        self.assertEqual(receipt['status'], 'verified')
        self.assertFalse(receipt['kit_code_executed'])
        self.assertEqual(receipt['interpreter_path_file'], 'authenticated_and_allowlisted')
        self.assertEqual(receipt['logical_root'], str(target))
        self.assertEqual(lines[1], 'reuse_rejected=destination already exists')
        self.assertEqual(digest((target / '_bundle/manifest.json').read_bytes()), manifest_hash)
        for name, expected in files.items():
            self.assertEqual((target / Path(name)).read_bytes(), expected, name)
        actual_dirs = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_dir()}
        actual_files = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
        self.assertEqual(actual_dirs, set(manifest['directories']))
        self.assertEqual(actual_files, set(files) | {'_bundle/manifest.json'})

if __name__ == '__main__':
    unittest.main()
