// SPDX-License-Identifier: MPL-2.0
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');

const TITLE = 'anymal sample stays responsive through load and reopen';

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
  const fixtures = ['tests/wasm/fixtures/hosted_assets.json'];
  function collect(relative) {
    for (const entry of fs.readdirSync(path.join(source, relative), { withFileTypes: true })) {
      const name = path.join(relative, entry.name);
      if (entry.isDirectory()) collect(name);
      else fixtures.push(name);
    }
  }
  collect('resources/wasm-presets');
  const sha = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  for (const relative of fixtures) {
    if (sha(path.join(source, relative)) !== sha(path.join(controller, relative))) {
      throw new Error(`Diagnostic fixture differs from original acceptance: ${relative}`);
    }
  }
  const mirror = path.join(source, 'build-wasm-assets');
  const hosted = JSON.parse(fs.readFileSync(path.join(source, fixtures[0])));
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
    PJ_WASM_CPU_PROFILE: '1',
    PJ_WASM_PRESETS_PACKAGE_DIR: path.join(source, 'build-wasm-probe/deploy-presets'),
    PJ_WASM_ASSETS_MIRROR: mirror,
  };
  // Keep the original serial JSON immutable; the replay has separate output.
  delete env.PLAYWRIGHT_JSON_OUTPUT_NAME;
  const result = spawnSync(process.execPath, [
    path.join(source, 'tests/wasm/node_modules/@playwright/test/cli.js'),
    'test', '--config', path.join(controller, 'tests/wasm/playwright.config.js'),
    'presets.spec.js', '--project=chromium', '--workers=1', '--reporter=line',
    '--grep', TITLE, '--output', path.join(source, 'cpu-profile-results'),
  ], { cwd: source, env, stdio: 'inherit' });
  if (result.error) throw result.error;
  return result.status ?? 1;
}

if (require.main === module) {
  process.exitCode = run(path.resolve(process.argv[2]), path.resolve(__dirname, '../..'));
}

module.exports = { needsProfile };
