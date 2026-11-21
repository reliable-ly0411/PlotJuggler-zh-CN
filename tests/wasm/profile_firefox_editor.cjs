// SPDX-License-Identifier: MPL-2.0
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');

const TITLE = 'Transform Editor creates a large exact Luau series while the browser main thread stays responsive';

function needsProfile(report) {
  const matches = [];
  function visit(suite) {
    for (const spec of suite.specs || []) {
      if (spec.title === TITLE) {
        matches.push(...spec.tests.filter(test => test.projectName === 'firefox'));
      }
    }
    for (const child of suite.suites || []) visit(child);
  }
  for (const suite of report.suites || []) visit(suite);
  if (matches.length !== 1) throw new Error('Require exactly one original Firefox transform result');
  return matches[0].results.some(result => ['failed', 'timedOut'].includes(result.status));
}

// Historical jobs retained Playwright's failure attachment before JSON reporting
// was enabled. Admit only this exact case and its unchanged timing assertions.
function needsHistoricalProfile(context) {
  if (!context.includes(`- Name: editors.spec.js >> ${TITLE}\n`)) {
    throw new Error('Historical evidence is not the exact transform case');
  }
  const details = context.match(/# Error details\s+```\n([\s\S]*?)\n```/);
  if (!details) throw new Error('Historical failure details missing');
  const gap = details[1].match(/Expected: < 100\s+Received:\s+([\d.]+)/);
  if (gap && Number(gap[1]) >= 100) return true;
  if (/Expected: false\s+Received: true/.test(details[1])
      && /Timeout 60000ms exceeded while waiting on the predicate/.test(details[1])
      && context.includes('(await requestToolboxTransformResult(page, consoleMessages)).materializing')) return true;
  throw new Error('Historical evidence does not establish either original timing failure');
}

// The derivative retains the source lane's complete test, including every
// assertion and timeout. Additional timing observations belong to this replay.
function instrumentEditorSpec(source, helper) {
  const start = source.indexOf(`test('${TITLE}'`);
  if (start < 0 || source.indexOf(`test('${TITLE}'`, start + 1) !== -1) {
    throw new Error('Original transform case boundary changed');
  }
  let block = source.slice(start);
  function markBefore(anchor, name) {
    if (block.split(anchor).length !== 2) throw new Error(`Diagnostic anchor changed: ${anchor}`);
    block = block.replace(anchor, `  await page.evaluate(() => performance.mark('${name}'));\n${anchor}`);
  }
  markBefore('  const readyMessages = consoleMessages.filter(', 'pj-transform-before-ok');
  markBefore('  const heartbeat = await page.evaluate(() => {', 'pj-transform-materialized');
  return source.slice(0, start) + block
    + `\nrequire(${JSON.stringify(helper)}).installEditorEvidence(test);\n`;
}

function run(source, controller, failureContext) {
  const tests = path.join(source, 'tests/wasm');
  const reportPath = failureContext || path.join(tests, 'firefox-editors-report.json');
  const reportBytes = fs.readFileSync(reportPath);
  const admitted = failureContext ? needsHistoricalProfile(reportBytes.toString('utf8')) : needsProfile(JSON.parse(reportBytes));
  if (!admitted) {
    console.log('Original Firefox transform did not fail; no diagnostic replay requested.');
    return 0;
  }
  const sha = value => createHash('sha256').update(value).digest('hex');
  const output = path.join(source, 'firefox-editor-profile-results');
  fs.mkdirSync(output); // Never overwrite another diagnostic attempt.
  const originalPath = path.join(tests, 'editors.spec.js');
  const original = fs.readFileSync(originalPath, 'utf8');
  const spec = path.join(tests, 'firefox_editor_profile.spec.js');
  const config = path.join(tests, 'firefox_editor_profile.playwright.config.cjs');
  const derived = instrumentEditorSpec(original, path.join(controller, 'tests/wasm/support/editor_evidence.cjs'));
  fs.writeFileSync(spec, derived, { flag: 'wx' });
  fs.writeFileSync(config, "module.exports = {...require('./playwright.config'), "
    + "testMatch: 'firefox_editor_profile.spec.js', fullyParallel: false, workers: 1, retries: 0};\n", { flag: 'wx' });
  const receipt = fs.readFileSync(path.join(source, 'validation-receipts/acceptance.json'));
  const identity = JSON.parse(receipt).identity;
  if (!/^[a-f0-9]{40}$/.test(identity.source_sha) || !/^[a-f0-9]{40}$/.test(identity.controller_sha)
      || !['upstream', 'localized'].includes(identity.role)
      || identity.source_sha !== process.env.PJ_SOURCE_SHA
      || identity.controller_sha !== process.env.PJ_CONTROLLER_SHA
      || identity.role !== process.env.PJ_VALIDATION_ROLE || identity.kind !== 'acceptance') {
    throw new Error('Diagnostic identity differs from the already verified acceptance receipt');
  }
  fs.writeFileSync(path.join(output, 'original.spec.js'), original);
  fs.writeFileSync(path.join(output, 'diagnostic.spec.js'), derived);
  fs.writeFileSync(path.join(output, failureContext ? 'original-error-context.md' : 'original-report.json'), reportBytes);
  fs.writeFileSync(path.join(output, 'acceptance.json'), receipt);
  const metadata = {
    diagnosticOnly: true, identity, originalSpecSha256: sha(original), diagnosticSpecSha256: sha(derived),
    originalReportSha256: sha(reportBytes), acceptanceReceiptSha256: sha(receipt),
    originalEvidenceKind: failureContext ? 'Playwright error-context attachment' : 'Playwright JSON report',
    originalRun: process.env.PJ_ORIGINAL_RUN_ID || null, originalJob: process.env.PJ_ORIGINAL_JOB_ID || null,
    diagnosticController: process.env.PJ_DIAGNOSTIC_CONTROLLER_SHA || null,
    profiler: 'Gecko startup sampling; perturbs timing; cannot replace the original failed result',
  };
  const env = {
    ...process.env, CI: 'true', NODE_PATH: path.join(tests, 'node_modules'),
    MOZ_PROFILER_STARTUP: '1', MOZ_PROFILER_STARTUP_FILTERS: 'GeckoMain,DOM Worker,Renderer',
    MOZ_PROFILER_SHUTDOWN: path.join(output, 'gecko-profile.json'),
    PLAYWRIGHT_JSON_OUTPUT_NAME: path.join(output, 'diagnostic-report.json'),
  };
  const result = spawnSync(process.execPath, [
    path.join(tests, 'node_modules/@playwright/test/cli.js'), 'test', '--config', config,
    '--project=firefox', '--workers=1', '--reporter=line,json', '--grep', TITLE,
    '--output', path.join(output, 'test-results'),
  ], { cwd: source, env, stdio: 'inherit' });
  metadata.exitCode = result.status;
  metadata.launchError = result.error ? String(result.error) : null;
  metadata.originalReportUnchanged = sha(fs.readFileSync(reportPath)) === metadata.originalReportSha256;
  metadata.originalSpecUnchanged = sha(fs.readFileSync(originalPath)) === metadata.originalSpecSha256;
  metadata.profiles = fs.readdirSync(output).filter(name => name.startsWith('gecko-profile'));
  fs.writeFileSync(path.join(output, 'identity.json'), JSON.stringify(metadata, null, 2));
  if (!metadata.originalReportUnchanged || !metadata.originalSpecUnchanged) {
    throw new Error('Original acceptance evidence changed during diagnostic replay');
  }
  if (result.error) throw result.error;
  if (metadata.profiles.length === 0) throw new Error('Firefox did not write a shutdown profile');
  return result.status ?? 1;
}

if (require.main === module) {
  process.exitCode = run(path.resolve(process.argv[2]), path.resolve(process.argv[3]),
    process.argv[4] ? path.resolve(process.argv[4]) : undefined);
}
module.exports = { TITLE, needsProfile, needsHistoricalProfile, instrumentEditorSpec, run };
