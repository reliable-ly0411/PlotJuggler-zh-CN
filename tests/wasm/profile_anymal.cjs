// SPDX-License-Identifier: MPL-2.0
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');

const TITLE = 'anymal sample stays responsive through load and reopen';

// Derive only the target case. Unknown source shapes fail closed instead of
// substituting a different branch's assertions or requiring its custom probes.
function instrumentAnymalSpec(source, helper) {
  const start = source.indexOf(`test('${TITLE}'`);
  const end = source.indexOf("\ntest('a sample that fails", start);
  if (start < 0 || end < 0) throw new Error('Original Anymal case boundaries changed');
  let block = source.slice(start, end);
  function replaceOnce(before, after) {
    if (block.split(before).length !== 2) throw new Error(`Diagnostic anchor changed: ${before}`);
    block = block.replace(before, after);
  }
  replaceOnce('async ({ page, browserName }) => {', 'async ({ page, browserName }, testInfo) => {');
  replaceOnce('  const samples = await startSamples();\n  try {',
    '  const samples = await startSamples();\n  let profile;\n  let originalFailure;\n  try {');
  const boot = '    const run = await bootSamples(context, errors, samples);';
  replaceOnce(boot, boot + `\n    profile = await require(${JSON.stringify(helper)}).startAnymalProfile(\n`
    + '      run.page, testInfo, SAMPLES_PACKAGE, __dirname);');
  replaceOnce('      const from = run.messages.length;',
    '      await profile.mark(`anymal-${pass}-start`);\n      const from = run.messages.length;');
  replaceOnce('      const restore = run.messages.slice(from)',
    '      await profile.mark(`anymal-${pass}-models-ready`);\n      const restore = run.messages.slice(from)');
  replaceOnce('  } finally {\n    await samples.close();\n  }', `  } catch (error) {
    originalFailure = error;
    throw error;
  } finally {
    try {
      if (profile) await profile.stop();
    } catch (error) {
      if (!originalFailure) throw error;
      console.error('CPU diagnostic also failed:', error);
    } finally {
      await samples.close();
    }
  }`);
  return source.slice(0, start) + block + source.slice(end);
}

// Only an actual failed Chromium result admits a diagnostic replay. A passing
// replay never changes the already-failed serial acceptance step.
function needsProfile(report) {
  const matches = [];
  function visit(suite) {
    for (const spec of suite.specs || []) {
      if (spec.title === TITLE) {
        matches.push(...spec.tests.filter(test => test.projectName === 'chromium'));
      }
    }
    for (const child of suite.suites || []) visit(child);
  }
  for (const suite of report.suites || []) visit(suite);
  if (matches.length !== 1) throw new Error('Require exactly one original Chromium Anymal result');
  return matches[0].results.some(result => ['failed', 'timedOut'].includes(result.status));
}

// Reuse only this job's already-verified package and fixture mirror. No fetch,
// build, artifact transfer or network fallback occurs in this diagnostic.
function run(source, controller) {
  const report = JSON.parse(fs.readFileSync(path.join(source, 'tests/wasm/serial-report.json')));
  if (!needsProfile(report)) {
    console.log('Original Anymal test did not fail; no CPU replay requested.');
    return 0;
  }
  const sha = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const mirror = path.join(source, 'build-wasm-assets');
  const hosted = JSON.parse(fs.readFileSync(path.join(source, 'tests/wasm/fixtures/hosted_assets.json')));
  for (const [file, expected] of Object.entries(hosted.files)) {
    const local = path.join(mirror, file);
    if (fs.statSync(local).size !== expected.bytes || sha(local) !== expected.sha256) {
      throw new Error(`Existing diagnostic fixture failed its pinned hash: ${file}`);
    }
  }
  const env = {
    ...process.env,
    CI: 'true',
    NODE_PATH: path.join(source, 'tests/wasm/node_modules'),
    PJ_WASM_PRESETS_PACKAGE_DIR: path.join(source, 'build-wasm-probe/deploy-presets'),
    PJ_WASM_ASSETS_MIRROR: mirror,
  };
  const tests = path.join(source, 'tests/wasm');
  const spec = path.join(tests, 'cpu_profile_replay.spec.js');
  const config = path.join(tests, 'cpu_profile_replay.playwright.config.cjs');
  fs.writeFileSync(spec, instrumentAnymalSpec(fs.readFileSync(path.join(tests, 'presets.spec.js'), 'utf8'),
    path.join(controller, 'tests/wasm/support/cpu_profile.js')), { flag: 'wx' });
  fs.writeFileSync(config, "module.exports = {...require('./playwright.config'), "
    + "testMatch: 'cpu_profile_replay.spec.js', fullyParallel: false, workers: 1};\n", { flag: 'wx' });
  // Keep the original serial JSON immutable; the replay has separate output.
  delete env.PLAYWRIGHT_JSON_OUTPUT_NAME;
  const result = spawnSync(process.execPath, [
    path.join(source, 'tests/wasm/node_modules/@playwright/test/cli.js'),
    'test', '--config', config,
    '--project=chromium', '--workers=1', '--reporter=line',
    '--grep', TITLE, '--output', path.join(source, 'cpu-profile-results'),
  ], { cwd: source, env, stdio: 'inherit' });
  if (result.error) throw result.error;
  const output = path.join(source, 'cpu-profile-results');
  fs.mkdirSync(output, { recursive: true });
  fs.copyFileSync(spec, path.join(output, 'diagnostic.spec.js'));
  fs.copyFileSync(path.join(tests, 'presets.spec.js'), path.join(output, 'original.spec.js'));
  return result.status ?? 1;
}

if (require.main === module) {
  process.exitCode = run(path.resolve(process.argv[2]), path.resolve(__dirname, '../..'));
}

module.exports = { needsProfile, instrumentAnymalSpec };
