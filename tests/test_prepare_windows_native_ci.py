# SPDX-License-Identifier: MPL-2.0
"""Contract checks for the opt-in, fail-closed Windows build preparation."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
SCRIPT_PATH = ROOT / 'scripts/windows/prepare_native_ci.ps1'
SCRIPT = SCRIPT_PATH.read_text(encoding='utf-8')
JOB = WORKFLOW.split('  windows-native-test-build:\n', 1)[1].split('\n  windows-native-test-clean:', 1)[0]
CLEAN_JOB = WORKFLOW.split('  windows-native-test-clean:\n', 1)[1].split('\n  source-checks:', 1)[0]
SEED_SCRIPT = SCRIPT.split("@'\nfrom pathlib import Path\n", 1)[1].split("\n'@ | & $builderPython", 1)[0]
SEED_SCRIPT = 'from pathlib import Path\n' + SEED_SCRIPT + '\n'


class NativeCiWorkflowTests(unittest.TestCase):
    def test_jobs_are_opt_in_read_only_and_upload_only_after_real_ci_verification(self):
        dispatch = WORKFLOW.split('  workflow_dispatch:\n', 1)[1].split('\npermissions:', 1)[0]
        self.assertIn('      windows_native_build:\n', dispatch)
        self.assertIn('        type: boolean\n', dispatch)
        self.assertIn('        default: false\n', dispatch)
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.windows_native_build == true", JOB)
        self.assertIn('runs-on: windows-2022', JOB)
        self.assertIn('timeout-minutes: 360', JOB)
        self.assertIn('permissions:\n  contents: read\n', WORKFLOW)
        self.assertIn('actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9', JOB)
        self.assertIn('          archive: false\n', JOB)
        self.assertLess(JOB.index('Bootstrap and run reviewed groups before upload'), JOB.index('actions/upload-artifact@'))
        self.assertLess(JOB.index('-Phase BootstrapSelfTest'), JOB.index('id: build'))
        self.assertIn('needs: [windows-native-test-build, windows-native-media]', CLEAN_JOB)
        self.assertIn('actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333', CLEAN_JOB)
        self.assertIn('          skip-decompress: true\n', CLEAN_JOB)
        self.assertIn('          digest-mismatch: error\n', CLEAN_JOB)
        self.assertEqual(CLEAN_JOB.count('actions/upload-artifact@'), 1)
        self.assertIn('name: windows-native-clean-evidence-${{ github.run_attempt }}', CLEAN_JOB)
        self.assertNotIn('archive: false', CLEAN_JOB)
        self.assertIn('path: ${{ runner.temp }}\\pj-native-ci-evidence-clean', CLEAN_JOB)
        self.assertIn("if: always() && steps.native_evidence.outcome == 'success'", CLEAN_JOB)
        self.assertLess(CLEAN_JOB.index('-Phase Verify -Archive'), CLEAN_JOB.index('id: native_evidence'))
        self.assertLess(CLEAN_JOB.index('id: native_evidence'), CLEAN_JOB.index('actions/upload-artifact@'))
        self.assertNotIn('permissions:', JOB)
        self.assertNotIn('permissions:', CLEAN_JOB)
        self.assertIn('run: ./scripts/windows/prepare_native_ci.ps1', JOB)

    def test_media_job_is_opt_in_preserves_failure_evidence_and_passes_independent_identity(self):
        media = WORKFLOW.split('  windows-native-media:\n', 1)[1].split('\n  windows-native-test-build:', 1)[0]
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.windows_native_build == true", media)
        self.assertIn('runs-on: ubuntu-24.04', media)
        self.assertIn('apt-signatures', media); self.assertIn('gpgv --keyring', media)
        self.assertIn('apt-get', media); self.assertIn('apt-download-uri.txt', media)
        self.assertIn('archive_sha256', media); self.assertIn('verify_fixture_manifest.py', media)
        for value in ('signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg', 'noble-security',
                      'apt-show.txt', 'installed-packages.tsv', 'dynamic-library-identities.json',
                      'mcap-source.tar.gz', 'mcap-source-lock.json'):
            self.assertIn(value, media)
        self.assertNotIn('--allow-insecure', media); self.assertNotIn('continue-on-error', media)
        self.assertIn('if: always()', media); self.assertIn('windows-native-media-evidence-', media)
        self.assertLess(media.index('verify_fixture_manifest.py'), media.index('manifest_sha256=%s'))
        self.assertIn('needs: [windows-native-media]', JOB)
        self.assertIn('digest-mismatch: error', JOB)
        for block in (JOB, CLEAN_JOB):
            self.assertIn('PJ_MEDIA_MANIFEST_SHA256: ${{ needs.windows-native-media.outputs.manifest_sha256 }}', block)
            self.assertIn('PJ_MEDIA_SOURCE_SHA:', block); self.assertIn('PJ_MEDIA_SOURCE_TREE:', block)
            self.assertIn('submodules: recursive', block); self.assertIn('persist-credentials: false', block)
        mutation = SCRIPT.index("Source checkout was not restored cleanly after linked mutation.")
        media_import = SCRIPT.index("'--import-generated-media'")
        main_discovery = SCRIPT.index('$mainDiscovery =')
        self.assertLess(mutation, media_import); self.assertLess(media_import, main_discovery)
        self.assertIn("'--check-generated-media'", SCRIPT)

    def test_actions_are_pinned_and_checkout_never_persists_credentials(self):
        self.assertIn('actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803', JOB)
        self.assertIn('actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1', JOB)
        self.assertIn('ilammy/msvc-dev-cmd@0b201ec74fa43914dc39ae48a89fd1d8cb592756', JOB)
        self.assertIn('submodules: recursive', JOB)
        self.assertIn('persist-credentials: false', JOB)

    def test_both_checkouts_use_and_remove_isolated_writable_global_config(self):
        for name, job in (('producer', JOB), ('clean', CLEAN_JOB)):
            with self.subTest(job=name):
                self.assertEqual(job.count('actions/checkout@'), 1)
                steps = job.split('      - uses: actions/checkout@', 1)[1].split('\n      - ', 2)
                checkout, cleanup = steps[:2]
                env = checkout.split('        env:\n', 1)[1].split('        with:\n', 1)[0]
                self.assertEqual(env, "          GIT_CONFIG_NOSYSTEM: '1'\n"
                                      '          GIT_CONFIG_GLOBAL: ${{ runner.temp }}\\pj-checkout.gitconfig\n'
                                      "          GIT_ATTR_NOSYSTEM: '1'\n")
                self.assertIn('          submodules: recursive\n', checkout)
                self.assertIn('          persist-credentials: false', checkout)
                self.assertIn('name: Remove isolated checkout Git config\n', cleanup)
                self.assertIn('        if: always()\n', cleanup)
                self.assertIn("Join-Path $env:RUNNER_TEMP 'pj-checkout.gitconfig'", cleanup)
                self.assertIn('Remove-Item -LiteralPath $path -Force', cleanup)

    @unittest.skipUnless(shutil.which('git'), 'Git is unavailable')
    def test_checkout_global_config_accepts_safe_directory_and_temporary_auth_include(self):
        with tempfile.TemporaryDirectory(prefix='pj-checkout config ') as temp:
            base = Path(temp)
            home = base / 'home'; home.mkdir()
            (home / '.gitconfig').write_text('[user]\n\tname = inherited\n', encoding='utf-8')
            config = base / 'pj-checkout.gitconfig'
            credentials = base / 'git-credentials-example.config'
            credentials.write_text('[http "https://github.com/"]\n\textraheader = synthetic-test-header\n', encoding='utf-8')
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
            env.update(HOME=str(home), GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM='1', GIT_ATTR_NOSYSTEM='1')
            subprocess.run(['git', 'config', '--global', '--add', 'safe.directory', str(base)], env=env, check=True)
            subprocess.run(['git', 'config', '--global', 'include.path', str(credentials)], env=env, check=True)
            self.assertEqual(subprocess.check_output(['git', 'config', '--global', '--get', 'safe.directory'],
                                                     env=env, text=True).strip(), str(base))
            self.assertEqual(subprocess.check_output(['git', 'config', '--global', '--get', 'include.path'],
                                                     env=env, text=True).strip(), str(credentials))
            self.assertEqual(subprocess.check_output(['git', 'config', '--global', '--includes', '--get',
                                                      'http.https://github.com/.extraheader'],
                                                     env=env, text=True).strip(), 'synthetic-test-header')
            inherited = subprocess.run(['git', 'config', '--global', '--get', 'user.name'], env=env, capture_output=True)
            self.assertNotEqual(inherited.returncode, 0)
            self.assertNotIn('synthetic-test-header', config.read_text(encoding='utf-8'))

    def test_all_later_git_children_inherit_isolated_settings(self):
        self.assertIn("$item.Name -match '^GIT_'", SCRIPT)
        for setting in ('GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL', 'GIT_ATTR_NOSYSTEM',
                        'GIT_TERMINAL_PROMPT', 'GIT_TEMPLATE_DIR', 'core.fsmonitor', 'core.hooksPath'):
            self.assertIn(setting, SCRIPT)
        self.assertLess(SCRIPT.index('Initialize-IsolatedGitEnvironment $gitControl'), SCRIPT.index("if ($Phase -eq 'Verify')"))
        self.assertNotIn("$item.Name -match '^GITHUB_'", SCRIPT)

    @unittest.skipUnless(os.name == 'nt' and shutil.which('git'), 'Real PowerShell/Git isolation test requires Windows')
    def test_poisoned_git_directory_global_hooks_and_template_are_ignored(self):
        shell = shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        self.assertIsNotNone(shell)
        with tempfile.TemporaryDirectory(prefix='pj-git-poison-') as temp:
            base = Path(temp)
            clean = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
            clean.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0')
            for name in ('a', 'b'):
                repo = base / name; repo.mkdir()
                subprocess.run(['git', 'init', '-q', str(repo)], env=clean, check=True)
                subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                'commit', '--allow-empty', '-qm', name], env=clean, check=True)
            head = subprocess.check_output(['git', '-C', str(base / 'a'), 'rev-parse', 'HEAD'], env=clean, text=True).strip()
            hooks = base / 'evil-hooks'; hooks.mkdir()
            hook_marker = base / 'hook-ran'
            (hooks / 'post-commit').write_text('#!/bin/sh\necho bad > "' + hook_marker.as_posix() + '"\n', encoding='utf-8')
            global_config = base / 'evil.gitconfig'
            global_config.write_text('[core]\n hooksPath = ' + hooks.as_posix() + '\n', encoding='utf-8')
            template = base / 'evil-template/hooks'; template.mkdir(parents=True)
            (template / 'post-checkout').write_text('#!/bin/sh\necho bad\n', encoding='utf-8')
            # Establish each poison really affects ordinary Git first; a hook
            # that Windows never executes would otherwise be a false negative.
            poison_dir = dict(clean, GIT_DIR=str(base / 'b/.git'))
            redirected = subprocess.check_output(['git', '-C', str(base / 'a'), 'rev-parse', 'HEAD'], env=poison_dir, text=True).strip()
            b_head = subprocess.check_output(['git', '-C', str(base / 'b'), 'rev-parse', 'HEAD'], env=clean, text=True).strip()
            self.assertEqual(redirected, b_head)
            poison_hook = dict(clean, GIT_CONFIG_GLOBAL=str(global_config))
            subprocess.run(['git', '-C', str(base / 'a'), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                            'commit', '--allow-empty', '-qm', 'poison-control'], env=poison_hook, check=True)
            self.assertTrue(hook_marker.is_file(), 'poisoned hook must execute in the unisolated control')
            hook_marker.unlink()
            head = subprocess.check_output(['git', '-C', str(base / 'a'), 'rev-parse', 'HEAD'], env=clean, text=True).strip()
            poison_template = dict(clean, GIT_TEMPLATE_DIR=str(template.parent))
            subprocess.run(['git', 'init', '-q', str(base / 'template-control')], env=poison_template, check=True)
            self.assertTrue((base / 'template-control/.git/hooks/post-checkout').is_file())
            assert_dir = 'function Assert-RealDirectory' + SCRIPT.split('function Assert-RealDirectory', 1)[1].split('\nfunction Assert-RealTree', 1)[0]
            isolate = 'function Initialize-IsolatedGitEnvironment' + SCRIPT.split('function Initialize-IsolatedGitEnvironment', 1)[1].split('\nfunction Invoke-CleanVerification', 1)[0]
            script = base / 'exercise.ps1'
            script.write_text("$ErrorActionPreference = 'Stop'\n" + assert_dir + '\n' + isolate + r'''
Initialize-IsolatedGitEnvironment $env:CONTROL
if ($env:GITHUB_TEST_SENTINEL -cne 'retained') { throw 'GITHUB variable lost' }
$head = (& git.exe -C $env:REPO_A rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $head -cne $env:EXPECTED_HEAD) { throw 'GIT_DIR redirected the repository' }
& git.exe -C $env:REPO_A -c user.name=Test -c user.email=test@example.invalid commit --allow-empty -qm isolated
if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $env:HOOK_MARKER)) { throw 'poisoned global hook executed' }
& git.exe init -q $env:NEW_REPO
if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath (Join-Path $env:NEW_REPO '.git/hooks/post-checkout'))) { throw 'poisoned template used' }
''', encoding='utf-8')
            env = dict(clean, GIT_DIR=str(base / 'b/.git'), GIT_CONFIG_GLOBAL=str(global_config),
                       GIT_TEMPLATE_DIR=str(template.parent), GITHUB_TEST_SENTINEL='retained',
                       CONTROL=str(base / 'controls'), REPO_A=str(base / 'a'), EXPECTED_HEAD=head,
                       HOOK_MARKER=str(hook_marker), NEW_REPO=str(base / 'new'))
            result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File', str(script)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_root_and_fail_closed_sequence(self):
        self.assertIn("$base = 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n'", SCRIPT)
        self.assertIn('$sourcePrefix = $sha.Substring(0, 12)', SCRIPT)
        for variable, child in [('source', 's'), ('qtRoot', 'q'), ('build', 'b'),
                                ('i18n', 'i'), ('tools', 't')]:
            self.assertIn(f"${variable} = Join-Path $root '{child}'", SCRIPT)
        self.assertIn("$env:CONAN_HOME = Join-Path $root 'c'", SCRIPT)
        for guard in ("$env:RUNNER_ENVIRONMENT -ne 'github-hosted'", 'Refusing to reuse an existing build root',
                      '[IO.FileAttributes]::ReparsePoint', "'--destination', $source, '--sha', $sha",
                      'prepare_native_tools.py', 'versions.env', '--lockfile-partial'):
            self.assertIn(guard, SCRIPT)
        self.assertLess(SCRIPT.index('prepare_native_source.py'), SCRIPT.index('prepare_native_tools.py'))
        self.assertLess(SCRIPT.index('$env:TEMP = $bootstrapTemp'), SCRIPT.index('prepare_native_source.py'))
        self.assertLess(SCRIPT.index('$env:CONAN_HOME ='), SCRIPT.index("@('install', $source"))
        self.assertLess(SCRIPT.index("@('install', $source"), SCRIPT.index("@('-S', $source"))
        self.assertIn('Assert-RealTree $tree', SCRIPT)
        self.assertIn('Native staging refused: consult $gapReport', SCRIPT)
        self.assertIn('--package --staging $staging --archive $kitArchive', SCRIPT)
        self.assertNotIn('throw "Compilation and discovery finished', SCRIPT)
        self.assertNotIn('upload-artifact', SCRIPT)
        self.assertIn('--show-only=json-v1', SCRIPT)
        self.assertLess(SCRIPT.index("@('--build', $build"), SCRIPT.index('$mainDiscovery ='))

    def test_conan_home_is_created_once_before_any_conan_command(self):
        assign = SCRIPT.index("$env:CONAN_HOME = Join-Path $root 'c'")
        reject = SCRIPT.index('if (Test-Path -LiteralPath $env:CONAN_HOME)', assign)
        create = 'New-Item -ItemType Directory -Path $env:CONAN_HOME | Out-Null'
        self.assertEqual(SCRIPT.count(create), 1)
        created = SCRIPT.index(create, reject)
        checked = SCRIPT.index('Assert-RealDirectory $env:CONAN_HOME', created)
        version = SCRIPT.index("Invoke-Checked $conan @('--version')")
        tree = SCRIPT.index('Assert-RealTree $env:CONAN_HOME', version)
        profile = SCRIPT.index("Invoke-Checked $conan @('profile', 'detect', '--force')")
        self.assertLess(SCRIPT.index('Refusing to reuse an existing build root'), assign)
        self.assertLess(assign, reject)
        self.assertLess(reject, created)
        self.assertLess(created, checked)
        self.assertLess(checked, version)
        self.assertLess(version, tree)
        self.assertLess(tree, profile)
        self.assertNotIn('-Force', SCRIPT[reject:checked])
        self.assertNotIn('Remove-Item', SCRIPT[reject:checked])

    @unittest.skipUnless(os.name == 'nt', 'Real PowerShell Conan-home check requires Windows')
    def test_conan_home_rejects_existing_files_and_directories(self):
        shell = shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        self.assertIsNotNone(shell)
        directory = 'function Assert-RealDirectory' + SCRIPT.split('function Assert-RealDirectory', 1)[1].split('\nfunction Assert-RealTree', 1)[0]
        tree = 'function Assert-RealTree' + SCRIPT.split('function Assert-RealTree', 1)[1].split('\nfunction Initialize-IsolatedGitEnvironment', 1)[0]
        init = SCRIPT.split("$env:CONAN_HOME = Join-Path $root 'c'", 1)[1].split("$env:CONAN_NON_INTERACTIVE = '1'", 1)[0]
        body = ("$ErrorActionPreference = 'Stop'\n" + directory + '\n' + tree +
                "\n$root = $env:PJ_TEST_ROOT\n$env:CONAN_HOME = Join-Path $root 'c'\n" + init +
                "\n[IO.File]::WriteAllText((Join-Path $env:CONAN_HOME 'owned.txt'), 'owned')\n" +
                "Assert-RealTree $env:CONAN_HOME\n")
        with tempfile.TemporaryDirectory(prefix='pj-conan-home-') as temp:
            base = Path(temp)
            def run(root):
                return subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', body],
                                      env=dict(os.environ, PJ_TEST_ROOT=str(root)), capture_output=True)
            fresh = base / 'fresh'; fresh.mkdir()
            result = run(fresh)
            self.assertEqual(result.returncode, 0, repr(result.stderr))
            sentinel = fresh / 'c' / 'owned.txt'
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'owned')
            self.assertNotEqual(run(fresh).returncode, 0)
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'owned')
            occupied = base / 'occupied'; occupied.mkdir()
            existing_file = occupied / 'c'; existing_file.write_text('keep', encoding='utf-8')
            self.assertNotEqual(run(occupied).returncode, 0)
            self.assertEqual(existing_file.read_text(encoding='utf-8'), 'keep')

    def test_bootstrap_is_trusted_system_code_before_any_downloaded_python(self):
        self.assertIn('System32/WindowsPowerShell/v1.0/powershell.exe', SCRIPT)
        self.assertIn('PjCiDirectoryIdentity]::Exact($Path)', SCRIPT)
        self.assertIn("Get-Item -LiteralPath $Path -Stream '*'", SCRIPT)
        self.assertIn('$env:TEMP = $trustedTemp', SCRIPT)
        self.assertIn('$env:TMP = $trustedTemp', SCRIPT)
        self.assertLess(SCRIPT.index('$env:TEMP = $trustedTemp'), SCRIPT.index('$receipt = @(& $shell'))
        self.assertLess(SCRIPT.index('$receipt = @(& $shell'), SCRIPT.index('$python = Join-Path $root'))
        self.assertIn("$record.kit_code_executed -ne $false", SCRIPT)
        self.assertLess(SCRIPT.index("$closureVerifier = Join-Path $root"), SCRIPT.index("$driver = Join-Path $root"))
        self.assertIn("$closureVerifier, '--verify-staged'", SCRIPT)
        self.assertIn("'-I', '-B', $driver", SCRIPT)
        self.assertIn('run_native_ci_verification.py', SCRIPT)
        self.assertNotIn('ExecutionPolicy Bypass', SCRIPT)
        self.assertIn('$rootNeed = $expanded + 1GB + 2GB', CLEAN_JOB)
        self.assertIn('$transportNeed = 2 * $compressed + 2GB', CLEAN_JOB)
        self.assertIn('$rootNeed += 2 * $compressed', CLEAN_JOB)

    def test_real_bootstrap_and_registry_controls_precede_plugin_tests(self):
        self.assertIn("$env:PJ_ALLOW_BOOTSTRAP_INTEGRATION = '1'", SCRIPT)
        self.assertIn("$env:PJ_BOOTSTRAP_TEST_SOURCE_SHA = $synthetic", SCRIPT)
        self.assertIn('test_actual_embedded_verifier_rejects_malformed_cases', SCRIPT)
        self.assertIn('test_full_fixed_root_and_refuse_reuse', SCRIPT)
        self.assertLess(SCRIPT.index("Invoke-CiTempProbe 'before-plugin-preflight'"), SCRIPT.index('$registrySource ='))
        self.assertLess(SCRIPT.index('$registrySource ='), SCRIPT.index('build_localized_plugins.py'))
        self.assertIn('bootstrap-selftest-evidence', SCRIPT)

    def test_python_origin_is_system_verified_before_any_kit_executable(self):
        bootstrap = SCRIPT.index("[IO.File]::WriteAllText($receiptPath, $receipt[0]")
        origin = SCRIPT.index("& $shell -NoProfile -NonInteractive -File $originVerifier")
        python = SCRIPT.index("$python = Join-Path $root 't/python/python.exe'")
        self.assertLess(bootstrap, origin); self.assertLess(origin, python)
        self.assertIn("$originVerifier = Join-Path $env:GITHUB_WORKSPACE 'scripts/windows/verify_embedded_python_origin.ps1'", SCRIPT)
        for option in ('-KitRoot $root', '-SourceSha $SourceSha', '-SourceTree $SourceTree',
                       '-ManifestSha256 $ManifestSha256', '-ArchiveSha256 $ArchiveSha256',
                       '-TrustedTemp $trustedTemp', '-Output $originReceipt'):
            self.assertIn(option, SCRIPT[origin:python])
        self.assertIn('ls-files --error-unmatch -- $relative', SCRIPT[bootstrap:origin])
        self.assertIn("$origin.archive_sha256 -cne $ArchiveSha256", SCRIPT[origin:python])
        self.assertIn("$origin.manifest_sha256 -cne $ManifestSha256", SCRIPT[origin:python])
        self.assertNotIn('ExecutionPolicy Bypass', SCRIPT)

    def test_real_python_origin_adversarial_selftest_is_required_before_build(self):
        self.assertIn("'test_windows_native_python_origin.py'", SCRIPT)
        self.assertIn('test_actual_dotnet_compare_accepts_exact_zip_and_rejects_tampering', SCRIPT)
        for name in ('python-origin.process.json', 'python-origin.stdout.bin', 'python-origin.stderr.bin',
                     'python_origin_script_sha256'):
            self.assertIn(name, SCRIPT)
        self.assertLess(SCRIPT.index('function Invoke-BootstrapSelfTest'), SCRIPT.index("if ($Phase -eq 'BootstrapSelfTest')"))
        self.assertIn("$originProcess.ExitCode -ne 0", SCRIPT)
        self.assertIn("$originSelftest.source_sha -cne $sha", SCRIPT)

    def test_test_driver_and_offline_ifw_are_recorded_at_configure_time(self):
        for arg in ('-DPython3_EXECUTABLE=$testPython', '-DPJ_TEST_PYTHON=$testPython',
                    '-DPJ_IFW_TEST_ARCHIVE=$archive', '-DPJ_IFW_TEST_EXTRACTOR=$extractor',
                    '-DPJ_IFW_TEST_EXTRACTOR_SHA256=$extractorSha'):
            self.assertIn(arg, SCRIPT)
        self.assertIn("'-DPJ_BUILD_TESTS=ON'", SCRIPT)
        self.assertIn("'-DPJ_PLUGIN_FEEDBACK_ACCEPTANCE=ON'", SCRIPT)
        self.assertIn("Invoke-Checked $cmake (@('-S', (Join-Path $source 'pj_app/tests/i18n'), '-B', $i18n) + $common)", SCRIPT)
        self.assertIn('\"-DPJ_CSV_RUNTIME_PLUGIN=$csvPlugin\") + $common', SCRIPT)
        self.assertIn('$prefetch.WaitForExit(12 * 60 * 1000)', SCRIPT)
        self.assertIn('$prefetch.Kill()', SCRIPT)

    def test_codemodel_query_and_original_process_evidence_precede_main_build(self):
        query = SCRIPT.index("$query = Join-Path $apiDirectory 'codemodel-v2'")
        configure = SCRIPT.index("Invoke-RecordedBuildProcess 'configure' $cmake $mainConfigure")
        build = SCRIPT.index("Invoke-RecordedBuildProcess 'build' $cmake")
        capture = SCRIPT.index("'--capture-codemodel'")
        self.assertLess(query, configure); self.assertLess(configure, build); self.assertLess(build, capture)
        self.assertIn('[IO.FileMode]::CreateNew', SCRIPT)
        self.assertIn("'--verify-codemodel'", SCRIPT)
        self.assertIn("@('runtime-catalog-language', 'extension-manager')", SCRIPT)
        self.assertIn("'--select-codemodel-rules'", SCRIPT)
        self.assertIn("if ($entry.status -cne 'selected') { continue }", SCRIPT)
        for value in ('stdout_sha256', 'stderr_sha256', 'cmake_sha256', 'ninja_sha256', 'still_running'):
            self.assertIn(value, SCRIPT)

    def test_conan_public_remotes_and_real_install_have_raw_evidence(self):
        for value in ("$item.Name -match '^CONAN_'", "$env:CONAN_NON_INTERACTIVE = '1'",
                      "Invoke-RecordedBuildProcess 'remotes' $conan @('remote', 'list', '--format=json')",
                      "Invoke-RecordedBuildProcess 'install' $conan", 'https://center2.conan.io',
                      'https://plotjuggler.jfrog.io/artifactory/api/conan/plotjuggler-conan',
                      'force_auth', 'allowed_packages', 'graph_sha256', 'lock_sha256', 'conan_sha256'):
            self.assertIn(value, SCRIPT)
        self.assertLess(SCRIPT.index("Invoke-RecordedBuildProcess 'remotes' $conan"),
                        SCRIPT.index("Invoke-RecordedBuildProcess 'install' $conan"))
        self.assertNotIn('Get-ChildItem Env: | Out-', SCRIPT)

    def test_real_csv_and_feedback_inputs_precede_discovery(self):
        self.assertLess(SCRIPT.index('build_localized_plugins.py'), SCRIPT.index('"-DPJ_CSV_RUNTIME_PLUGIN=$csvPlugin"'))
        self.assertLess(SCRIPT.index('prepare_feedback_tests.py'), SCRIPT.index('$mainDiscovery ='))
        self.assertLess(SCRIPT.index("Invoke-CiTempProbe 'before-plugin-preflight'"), SCRIPT.index('build_localized_plugins.py'))
        self.assertLess(SCRIPT.index("Invoke-CiTempProbe 'before-main-discovery'"), SCRIPT.index('$mainDiscovery ='))
        self.assertLess(SCRIPT.index("Invoke-CiTempProbe 'before-marker-discovery'"),
                        SCRIPT.index("Invoke-RecordedMarker 'discovery'"))
        self.assertIn('$result.pid -ne $process.Id', SCRIPT)
        self.assertIn('$result.auth_luid -cnotmatch', SCRIPT)
        self.assertIn("$result.elevation_type -cnotin @('default', 'full', 'limited')", SCRIPT)
        self.assertIn("'--preflight', '--plugin', 'csv-loader'", SCRIPT)
        self.assertIn("'--capture-prebuilt'", SCRIPT)
        self.assertIn('--archive-dest $qtArchives', SCRIPT)

    def test_private_registry_smoke_uses_compiled_fixture_and_full_receipt(self):
        self.assertIn('scripts/windows/native_registry_smoke', SCRIPT)
        self.assertIn('--target registry_fixture_smoke', SCRIPT)
        for text in ("'--source-dir', $registrySource", "'--test-mains-dir', $testMains",
                     "'--qt-core', (Join-Path $qt 'bin/Qt6Core.dll')", '$registryResult.normal.exit_code -ne 0',
                     '$registryResult.injected.exit_code -ne 1', 'absent_after_exact_cleanup',
                     'normal.stdout.bin', 'injected.stderr.bin', 'producer-identity.json'):
            self.assertIn(text, SCRIPT)

    def test_linked_mutation_uses_same_root_runtime_and_leaves_no_sentinel(self):
        self.assertLess(SCRIPT.index('$registrySource ='), SCRIPT.index('$mutationController ='))
        self.assertLess(SCRIPT.index('$env:PATH = (($dllDirs'), SCRIPT.index("Invoke-CiTempProbe 'before-marker-mutation'"))
        self.assertLess(SCRIPT.index("Invoke-CiTempProbe 'before-marker-mutation'"),
                        SCRIPT.index("'-I', '-B', $mutationController"))
        self.assertLess(SCRIPT.index("'-I', '-B', $mutationController"), SCRIPT.index('$mainDiscovery ='))
        for value in ('marker-mutation-evidence', "'INCOMPLETE'", 'mutant_runner_sha256',
                      'restored_runner_sha256', 'qt_preflight_sha256', 'mutant.xml', 'original.xml'):
            self.assertIn(value, SCRIPT)

    def test_both_configured_trees_get_distinct_cache_bound_identities(self):
        self.assertIn("@{ Role = 'main'; Tree = $build }", SCRIPT)
        self.assertIn("@{ Role = 'i18n'; Tree = $i18n }", SCRIPT)
        self.assertIn("'--capture-identity', $item.Role", SCRIPT)
        self.assertIn("(Join-Path $evidence 'build_identity.json')", SCRIPT)
        self.assertLess(SCRIPT.index("@('--build', $build"), SCRIPT.index("'--capture-identity', $item.Role"))

    @unittest.skipUnless(os.name == 'nt', 'PowerShell parser requires Windows')
    def test_powershell_parser_accepts_script_without_executing_it(self):
        shells = [shutil.which(name) for name in ('powershell.exe', 'pwsh.exe')]
        self.assertTrue(any(shells), 'PowerShell runtime missing')
        parse = ("$tokens = $null; $errors = $null; "
                 "$null = [System.Management.Automation.Language.Parser]::ParseFile("
                 "$env:PJ_NATIVE_CI_SCRIPT, [ref]$tokens, [ref]$errors); "
                 "if ($errors.Count -gt 0) { $errors | Out-String | Write-Error; exit 1 }")
        env = dict(os.environ, PJ_NATIVE_CI_SCRIPT=str(SCRIPT_PATH))
        for shell in dict.fromkeys(filter(None, shells)):
            with self.subTest(shell=shell):
                result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', parse],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class NativeCiSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 's'
        self.cache = self.root / 'c/source-cache'
        self.home = self.root / 'c'
        self.home.mkdir()
        self.seeds = self.source / '.github/conan/source-backup'
        self.seeds.mkdir(parents=True)
        self.content = b'verified source fixture'
        self.digest = hashlib.sha256(self.content).hexdigest()
        (self.seeds / self.digest).write_bytes(self.content)
        (self.seeds / (self.digest + '.json')).write_text('{"references":{"fixture":[]}}', encoding='utf-8')

    def run_seed(self):
        return subprocess.run([sys.executable, '-', str(self.source), str(self.cache), str(self.home)],
                              input=SEED_SCRIPT, text=True, capture_output=True)

    def test_verified_seed_and_conan_configuration(self):
        result = self.run_seed()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.cache / 's' / self.digest).read_bytes(), self.content)
        self.assertTrue((self.cache / 's' / (self.digest + '.json')).is_file())
        conf = (self.home / 'global.conf').read_text(encoding='utf-8')
        self.assertIn('core.sources:download_cache=' + self.cache.as_posix(), conf)
        self.assertIn('core.sources:download_urls=["origin",', conf)

    def test_corrupt_seed_fails_before_copying_any_bytes(self):
        (self.seeds / self.digest).write_bytes(b'corrupt')
        result = self.run_seed()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SHA-256 mismatch', result.stderr)
        self.assertFalse(self.cache.exists())

    def test_missing_references_fail_before_copy(self):
        (self.seeds / (self.digest + '.json')).write_text('{}', encoding='utf-8')
        result = self.run_seed()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('references missing', result.stderr)
        self.assertFalse(self.cache.exists())


if __name__ == '__main__':
    unittest.main()
