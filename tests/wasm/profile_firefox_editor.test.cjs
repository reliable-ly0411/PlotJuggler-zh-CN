// SPDX-License-Identifier: MPL-2.0
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { TITLE, needsProfile, instrumentEditorSpec, run } = require('./profile_firefox_editor.cjs');
const { installEditorEvidence } = require('./support/editor_evidence.cjs');

function report(status, overrides = {}) {
  return { suites: [{ specs: [{ title: TITLE, tests: [{ projectName: 'firefox', results: [{ status }], ...overrides }] }] }] };
}

test('only a failed original Firefox transform permits a diagnostic', () => {
  for (const status of ['failed', 'timedOut']) assert.equal(needsProfile(report(status)), true);
  for (const status of ['passed', 'skipped', 'interrupted']) assert.equal(needsProfile(report(status)), false);
  assert.equal(needsProfile(report('passed', { results: [{ status: 'failed' }, { status: 'passed' }] })), true);
});

test('missing, wrong-browser and duplicated original results fail closed', () => {
  const duplicate = report('failed');
  duplicate.suites.push(duplicate.suites[0]);
  for (const value of [{}, report('failed', { projectName: 'chromium' }), duplicate]) {
    assert.throws(() => needsProfile(value), /exactly one/);
  }
});

test('removing diagnostic-only additions reproduces every byte of the original spec', () => {
  const source = fs.readFileSync(path.join(__dirname, 'editors.spec.js'), 'utf8');
  const derived = instrumentEditorSpec(source, '/synthetic/helper.cjs');
  new vm.Script(derived);
  const stripped = derived.replaceAll(/^  await page.evaluate\(\(\) => performance.mark\('pj-transform-[^']+'\)\);\n/gm, '')
    .replace('\nrequire("/synthetic/helper.cjs").installEditorEvidence(test);\n', '');
  assert.equal(stripped, source);
});

test('unknown timing anchors are rejected without substituting controller tests', () => {
  const source = fs.readFileSync(path.join(__dirname, 'editors.spec.js'), 'utf8');
  for (const changed of ['', source.replace('  const heartbeat = await page.evaluate(() => {', '  const changed = 1;')]) {
    assert.throws(() => instrumentEditorSpec(changed, '/synthetic/helper.cjs'));
  }
});

test('after a failed page observation console and original error evidence survive', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pj-editor-evidence-'));
  try {
    let before;
    let after;
    const listeners = {};
    installEditorEvidence({ beforeEach: hook => { before = hook; }, afterEach: hook => { after = hook; } });
    const page = {
      on: (event, handler) => { listeners[event] = handler; },
      evaluate: async () => { throw new Error('Page already closed'); },
    };
    await before({ page });
    listeners.console({ type: () => 'info', text: () => 'PJ_WASM_TOOLBOX_TRANSFORMS count=1 materializing=1' });
    const info = { status: 'failed', errors: [{ message: '100 ms heartbeat assertion' }], outputPath: name => path.join(root, 'test', name) };
    await after({ page }, info);
    const consoleEvents = JSON.parse(fs.readFileSync(info.outputPath('editor-console.json')));
    const state = JSON.parse(fs.readFileSync(info.outputPath('editor-state.json')));
    assert.equal(consoleEvents.length, 1);
    assert.match(consoleEvents[0].text, /materializing=1/);
    assert.equal(state.status, 'failed');
    assert.deepEqual(state.errors, info.errors);
    assert.match(state.observationError, /Page already closed/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('a failing stand-in launcher retains original files, exit code and receipt identity', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pj-editor-driver-'));
  const keys = ['PJ_SOURCE_SHA', 'PJ_CONTROLLER_SHA', 'PJ_VALIDATION_ROLE'];
  const saved = keys.map(key => process.env[key]);
  try {
    const tests = path.join(root, 'tests/wasm');
    fs.mkdirSync(path.join(tests, 'node_modules/@playwright/test'), { recursive: true });
    fs.mkdirSync(path.join(root, 'validation-receipts'));
    const original = fs.readFileSync(path.join(__dirname, 'editors.spec.js'));
    const originalReport = JSON.stringify(report('failed'));
    fs.writeFileSync(path.join(tests, 'editors.spec.js'), original);
    fs.writeFileSync(path.join(tests, 'firefox-editors-report.json'), originalReport);
    const identity = { source_sha: 'a'.repeat(40), controller_sha: 'b'.repeat(40), role: 'upstream', kind: 'acceptance' };
    fs.writeFileSync(path.join(root, 'validation-receipts/acceptance.json'), JSON.stringify({ identity }));
    // Exercise the real child-process/file handoff without launching a browser.
    fs.writeFileSync(path.join(tests, 'node_modules/@playwright/test/cli.js'), `
      const fs = require('node:fs');
      fs.writeFileSync(process.env.MOZ_PROFILER_SHUTDOWN, JSON.stringify({ standInOnly: true, args: process.argv.slice(2) }));
      process.exitCode = 1;
    `);
    [process.env.PJ_SOURCE_SHA, process.env.PJ_CONTROLLER_SHA, process.env.PJ_VALIDATION_ROLE]
      = [identity.source_sha, identity.controller_sha, identity.role];
    assert.equal(run(root, root), 1);
    assert.deepEqual(fs.readFileSync(path.join(tests, 'editors.spec.js')), original);
    assert.equal(fs.readFileSync(path.join(tests, 'firefox-editors-report.json'), 'utf8'), originalReport);
    const output = path.join(root, 'firefox-editor-profile-results');
    const metadata = JSON.parse(fs.readFileSync(path.join(output, 'identity.json')));
    assert.deepEqual(metadata.identity, identity);
    assert.equal(metadata.originalReportUnchanged, true);
    assert.equal(metadata.originalSpecUnchanged, true);
    assert.equal(metadata.exitCode, 1);
    assert.deepEqual(metadata.profiles, ['gecko-profile.json']);
    const child = JSON.parse(fs.readFileSync(path.join(output, 'gecko-profile.json')));
    assert.ok(child.args.includes('--project=firefox'));
    assert.ok(child.args.includes(TITLE));
    assert.throws(() => run(root, root), /EEXIST/);
  } finally {
    keys.forEach((key, index) => {
      if (saved[index] === undefined) delete process.env[key];
      else process.env[key] = saved[index];
    });
    fs.rmSync(root, { recursive: true, force: true });
  }
});
