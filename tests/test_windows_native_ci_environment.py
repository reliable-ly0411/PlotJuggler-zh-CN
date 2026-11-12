# SPDX-License-Identifier: MPL-2.0
"""Producer source guards and isolated PowerShell contract regressions."""
from pathlib import Path
import unittest


class ProducerScreenshotEnvironmentTest(unittest.TestCase):
    def test_inherited_paths_are_cleared_before_any_process(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/windows/prepare_native_ci.ps1').read_text(encoding='utf-8')
        clearing = "foreach ($name in @('PJ_GUI_ACCEPTANCE_DIR', 'PJ_UI_TEST_DUMP_DIR'))"
        action = "[Environment]::SetEnvironmentVariable($name, $null, 'Process')"
        self.assertLess(source.index(clearing), source.index(action))
        for later in ("Invoke-CiTempProbe 'before-plugin-preflight'", 'Invoke-Checked $builderPython',
                      "$env:PJ_GUI_ACCEPTANCE_DIR = Join-Path $build 'gui-acceptance'"):
            self.assertLess(source.index(action), source.index(later))
        self.assertNotIn('$env:PJ_UI_TEST_DUMP_DIR =', source)


class ProducerPhaseVariableTest(unittest.TestCase):
    @staticmethod
    def source():
        """Read the actual producer without running its build entry point."""
        return (Path(__file__).resolve().parents[1] / 'scripts/windows/prepare_native_ci.ps1').read_text(encoding='utf-8')

    @staticmethod
    def harness(source):
        """Run only the production parameter declaration and mutation evidence loop."""
        import re
        declaration = re.search(r"(?m)^  (\[ValidateSet\('Build', 'Verify', 'BootstrapSelfTest'\)\]\[string\]\$Phase = 'Build'),$", source)
        loop = re.search(r"(?ms)^foreach \(\$\w+ in @\('mutant-build', 'mutant-test', 'original-build', 'original-test'\)\) \{.*?^\}", source)
        if declaration is None or loop is None:
            raise AssertionError('Producer phase contract or mutation evidence loop was not found')
        return r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$harness = [scriptblock]::Create(@'
param(""" + declaration.group(1) + r""", [string]$MissingLeaf = '')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$mutationEvidence = Join-Path ([IO.Path]::GetTempPath()) 'pj-phase-fixture'
$seen = [Collections.Generic.List[string]]::new()
function Test-Path {
  param([string]$LiteralPath, [string]$PathType)
  if ($PathType -cne 'Leaf') { throw 'Unexpected evidence path kind.' }
  $leaf = [IO.Path]::GetFileName($LiteralPath)
  $seen.Add($leaf)
  return $leaf -cne $MissingLeaf
}
""" + loop.group(0) + r"""
[pscustomobject]@{ phase = $Phase; files = @($seen.ToArray()) }
'@)
$results = @((& $harness), (& $harness -Phase Verify), (& $harness -Phase BootstrapSelfTest))
$invalidRejected = $false
try { & $harness -Phase 'mutant-build' | Out-Null }
catch {
  if ($_.FullyQualifiedErrorId -notlike 'ParameterArgumentValidationError*') { throw }
  $invalidRejected = $true
}
$missingRejected = $false
try { & $harness -MissingLeaf 'mutant-test.stderr.bin' | Out-Null }
catch {
  if ($_.Exception.Message -notlike 'Missing raw linked marker mutation evidence:*') { throw }
  $missingRejected = $true
}
[pscustomobject]@{
  results = $results; invalid_rejected = $invalidRejected; missing_rejected = $missingRejected
} | ConvertTo-Json -Depth 6 -Compress
"""

    def test_mutation_loop_cannot_reassign_the_case_insensitive_phase_parameter(self):
        import re
        source = self.source()
        names = re.findall(r'\bforeach\s*\(\s*\$(\w+)\s+in\b', source, re.I)
        self.assertNotIn('phase', [name.casefold() for name in names])
        self.assertIn("[ValidateSet('Build', 'Verify', 'BootstrapSelfTest')][string]$Phase = 'Build'", source)

    def test_actual_loop_preserves_phase_and_rejects_invalid_phase_or_missing_evidence(self):
        import json
        import shutil
        import subprocess
        commands = list(dict.fromkeys(path for name in ('pwsh', 'powershell') if (path := shutil.which(name))))
        if not commands:
            self.skipTest('PowerShell is required for the actual parameter-validation regression')
        expected = [phase + extension
                    for phase in ('mutant-build', 'mutant-test', 'original-build', 'original-test')
                    for extension in ('.stdout.bin', '.stderr.bin', '.process.json')]
        for command in commands:
            with self.subTest(powershell=command):
                result = subprocess.run([command, '-NoLogo', '-NoProfile', '-NonInteractive',
                                         '-Command', self.harness(self.source())],
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
                report = json.loads(result.stdout)
                self.assertEqual([item['phase'] for item in report['results']],
                                 ['Build', 'Verify', 'BootstrapSelfTest'])
                self.assertTrue(all(item['files'] == expected for item in report['results']))
                self.assertTrue(report['invalid_rejected'])
                self.assertTrue(report['missing_rejected'])


class ProducerCacheVariableTest(unittest.TestCase):
    @staticmethod
    def cache_guard(source):
        """Extract the production checks without reading a cache or running a build."""
        start = '      $lines = [IO.File]::ReadAllLines($cache)\n'
        end = '\n    }\n    if ($cacheValid) {'
        if source.count(start) != 1 or end not in source.split(start, 1)[1]:
            raise AssertionError('Producer marker cache validation block was not found')
        return source.split(start, 1)[1].split(end, 1)[0]

    @classmethod
    def harness(cls, source):
        """Exercise the exact cache guard using synthetic in-memory cache lines."""
        return r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$beforeHome = $HOME
$beforeOptions = (Get-Variable HOME).Options
$harness = [scriptblock]::Create(@'
param([string[]]$lines, [string]$markerSource)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
""" + cls.cache_guard(source) + r"""
$cacheValid
'@)
$sourcePath = Join-Path ([IO.Path]::GetTempPath()) 'pj-marker-contract/s/scripts/windows/native_app_marker_probe'
$homeLine = 'CMAKE_HOME_DIRECTORY:INTERNAL=' + $sourcePath
$generatorLine = 'CMAKE_GENERATOR:INTERNAL=Ninja Multi-Config'
$cases = @(
  @{ name = 'valid'; lines = @($homeLine, $generatorLine) },
  @{ name = 'equivalent-slash-and-case'; lines = @(
    ('CMAKE_HOME_DIRECTORY:INTERNAL=' + $sourcePath.Replace('\', '/').ToUpperInvariant()), $generatorLine) },
  @{ name = 'missing-home'; lines = @($generatorLine) },
  @{ name = 'duplicate-home'; lines = @($homeLine, $homeLine, $generatorLine) },
  @{ name = 'wrong-source'; lines = @(($homeLine + '-unrelated'), $generatorLine) },
  @{ name = 'missing-generator'; lines = @($homeLine) },
  @{ name = 'duplicate-generator'; lines = @($homeLine, $generatorLine, $generatorLine) },
  @{ name = 'wrong-generator'; lines = @($homeLine, 'CMAKE_GENERATOR:INTERNAL=Ninja') },
  @{ name = 'case-changed-generator'; lines = @($homeLine, 'CMAKE_GENERATOR:INTERNAL=NINJA Multi-Config') }
)
$results = @(foreach ($case in $cases) {
  [pscustomobject]@{ name = $case.name; accepted = (& $harness -lines $case.lines -markerSource $sourcePath) }
})
[pscustomobject]@{
  results = $results
  home_preserved = ($HOME -ceq $beforeHome -and (Get-Variable HOME).Options -eq $beforeOptions)
} | ConvertTo-Json -Depth 6 -Compress
"""

    def test_cache_guard_does_not_shadow_home(self):
        import re
        guard = self.cache_guard(ProducerPhaseVariableTest.source())
        self.assertIsNone(re.search(r'\$(?:(?:global|script|local|private):)?home\b', guard, re.I))
        self.assertIn('CMAKE_HOME_DIRECTORY:INTERNAL=', guard)
        self.assertIn('CMAKE_GENERATOR:INTERNAL=Ninja Multi-Config', guard)

    def test_actual_cache_guard_preserves_home_and_source_identity(self):
        import json
        import shutil
        import subprocess
        commands = list(dict.fromkeys(path for name in ('pwsh', 'powershell') if (path := shutil.which(name))))
        if not commands:
            self.skipTest('PowerShell is required for the actual marker cache regression')
        expected = {'valid': True, 'equivalent-slash-and-case': True,
                    'missing-home': False, 'duplicate-home': False, 'wrong-source': False,
                    'missing-generator': False, 'duplicate-generator': False,
                    'wrong-generator': False, 'case-changed-generator': False}
        for command in commands:
            with self.subTest(powershell=command):
                result = subprocess.run([command, '-NoLogo', '-NoProfile', '-NonInteractive',
                                         '-Command', self.harness(ProducerPhaseVariableTest.source())],
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
                report = json.loads(result.stdout)
                self.assertEqual(len(report['results']), len(expected))
                self.assertEqual({item['name']: item['accepted'] for item in report['results']}, expected)
                self.assertTrue(report['home_preserved'])


class ProducerProtectedVariableTest(unittest.TestCase):
    # Parse, never execute, the producer and its PowerShell helpers. The union
    # includes names specific to Windows PowerShell or PowerShell Core.
    HARNESS = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$protectedNames = @('ConsoleFileName', 'EnabledExperimentalFeatures', 'IsCoreCLR',
                    'IsLinux', 'IsMacOS', 'IsWindows', 'PSStyle') + @(
  Get-Variable | Where-Object {
    $_.Options -band [Management.Automation.ScopedItemOptions]::ReadOnly -or
    $_.Options -band [Management.Automation.ScopedItemOptions]::Constant
  } | ForEach-Object { $_.Name }
)
function Find-ProtectedWrites([string]$Source) {
  $tokens = $null; $errors = $null
  $ast = [Management.Automation.Language.Parser]::ParseInput($Source, [ref]$tokens, [ref]$errors)
  if ($errors.Count) { throw ($errors | ForEach-Object { $_.Message } | Out-String) }
  $writes = @($ast.FindAll({
    param($node)
    $node -is [Management.Automation.Language.AssignmentStatementAst] -or
    $node -is [Management.Automation.Language.ParameterAst] -or
    $node -is [Management.Automation.Language.ForEachStatementAst] -or
    ($node -is [Management.Automation.Language.UnaryExpressionAst] -and
     $node.TokenKind -in @('PlusPlus', 'MinusMinus', 'PostfixPlusPlus', 'PostfixMinusMinus'))
  }, $true))
  foreach ($node in $writes) {
    $target = if ($node -is [Management.Automation.Language.AssignmentStatementAst]) { $node.Left }
      elseif ($node -is [Management.Automation.Language.ParameterAst]) { $node.Name }
      elseif ($node -is [Management.Automation.Language.ForEachStatementAst]) { $node.Variable }
      else { $node.Child }
    foreach ($variable in $target.FindAll({
      param($entry) $entry -is [Management.Automation.Language.VariableExpressionAst]
    }, $true)) {
      # Updating an object's member/index does not assign its containing variable.
      $parent = $variable.Parent; $memberWrite = $false
      while ($null -ne $parent -and $parent -ne $node) {
        if ($parent -is [Management.Automation.Language.MemberExpressionAst] -or
            $parent -is [Management.Automation.Language.IndexExpressionAst]) { $memberWrite = $true }
        $parent = $parent.Parent
      }
      $name = $variable.VariablePath.UserPath -replace '^(global|script|local|private):', ''
      if (-not $memberWrite -and $name -in $protectedNames) {
        [pscustomobject]@{ name = $name; line = $variable.Extent.StartLineNumber }
      }
    }
  }
}
# Negative controls prove case, scope, typed assignments, parameters and loops
# are inspected without trying to overwrite protected variables in the host.
$controls = @(
  '$hOmE = 1', '$script:HOME = 1', '[string]$home = "x"', '$HOME, $other = 1, 2',
  'foreach ($hOsT in 1) {}', 'param([string]$PiD)', '$HOME++', '--$HOME'
)
foreach ($control in $controls) {
  if (@(Find-ProtectedWrites $control).Count -ne 1) { throw ('Missed protected write: ' + $control) }
}
if (@(Find-ProtectedWrites '$env:HOME = "x"; $record.HOME = 1; $record[$HOME] = 1; $copy = $HOME').Count) {
  throw 'A variable read, environment value or object member was mistaken for a protected assignment.'
}
$reports = @(foreach ($path in ($env:PJ_VARIABLE_AUDIT_PATHS | ConvertFrom-Json)) {
  [pscustomobject]@{ path = $path; hits = @(Find-ProtectedWrites ([IO.File]::ReadAllText($path))) }
})
[pscustomobject]@{ controls = $controls.Count; reports = $reports } | ConvertTo-Json -Depth 6 -Compress
"""

    def test_powershell_ast_rejects_protected_variable_writes(self):
        import json
        import os
        import shutil
        import subprocess
        commands = list(dict.fromkeys(path for name in ('pwsh', 'powershell') if (path := shutil.which(name))))
        if not commands:
            self.skipTest('PowerShell is required for the protected-variable AST regression')
        scripts = Path(__file__).resolve().parents[1] / 'scripts/windows'
        paths = [str(scripts / name) for name in ('prepare_native_ci.ps1', 'bootstrap_native_test_kit.ps1',
                                                 'verify_embedded_python_origin.ps1', 'native_process.ps1')]
        env = dict(os.environ, PJ_VARIABLE_AUDIT_PATHS=json.dumps(paths))
        for command in commands:
            with self.subTest(powershell=command):
                result = subprocess.run([command, '-NoLogo', '-NoProfile', '-NonInteractive',
                                         '-Command', self.HARNESS], env=env, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
                report = json.loads(result.stdout)
                self.assertEqual(report['controls'], 8)
                self.assertEqual([item['path'] for item in report['reports']], paths)
                self.assertTrue(all(not item['hits'] for item in report['reports']), report['reports'])


if __name__ == '__main__':
    unittest.main()
