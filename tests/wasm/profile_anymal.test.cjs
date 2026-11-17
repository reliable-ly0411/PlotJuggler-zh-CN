// SPDX-License-Identifier: MPL-2.0
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { needsProfile, instrumentAnymalSpec } = require('./profile_anymal.cjs');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function report(status, overrides = {}) {
  return { suites: [{ suites: [{ specs: [{
    title: 'anymal sample stays responsive through load and reopen',
    tests: [{ projectName: 'chromium', results: [{ status }], ...overrides }],
  }] }] }] };
}

test('only failed or timed-out original Chromium measurements admit profiling', () => {
  for (const status of ['failed', 'timedOut']) assert.equal(needsProfile(report(status)), true);
  for (const status of ['passed', 'skipped', 'interrupted']) assert.equal(needsProfile(report(status)), false);
});

test('missing, Firefox-only and duplicated evidence cannot admit profiling', () => {
  for (const value of [{}, report('failed', { projectName: 'firefox' })]) {
    assert.throws(() => needsProfile(value), /exactly one/);
  }
  const duplicate = report('failed');
  duplicate.suites.push(duplicate.suites[0]);
  assert.throws(() => needsProfile(duplicate), /exactly one/);
});

test('a later pass cannot conceal an earlier failed measurement', () => {
  assert.equal(needsProfile(report('passed', { results: [{ status: 'failed' }, { status: 'passed' }] })), true);
});


test('diagnostic derivation retains every original assertion and parses as JavaScript', () => {
  const original = fs.readFileSync(path.join(__dirname, 'presets.spec.js'), 'utf8');
  const derived = instrumentAnymalSpec(original, '/synthetic/helper.js');
  const expectations = text => text.split('\n').filter(line => /\bexpect\b/.test(line));
  assert.deepEqual(expectations(derived), expectations(original));
  assert.equal((derived.match(/test\('/g) || []).length, (original.match(/test\('/g) || []).length);
  assert.match(derived, /startAnymalProfile/);
  assert.match(derived, /originalFailure = error;\n    throw error;/);
  new vm.Script(derived);
});

test('unknown original test shapes stop before substitution', () => {
  const original = fs.readFileSync(path.join(__dirname, 'presets.spec.js'), 'utf8');
  for (const changed of ['', original.replace('const from = run.messages.length;', 'const unexpected = 0;')]) {
    // The first matching line may belong to another test; remove every anchor to test drift.
    const drift = changed.replaceAll('const from = run.messages.length;', 'const unexpected = 0;');
    assert.throws(() => instrumentAnymalSpec(drift, '/synthetic/helper.js'));
  }
});
