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


if __name__ == '__main__':
    unittest.main()
