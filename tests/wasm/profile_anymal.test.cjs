// SPDX-License-Identifier: MPL-2.0
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { needsProfile } = require('./profile_anymal.cjs');

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
