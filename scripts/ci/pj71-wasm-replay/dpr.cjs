/* SPDX-License-Identifier: MPL-2.0 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const TITLE = 'Transform Editor creates a large exact Luau series while the browser main thread stays responsive';
const ORDER = [1, 2, 2, 1];
const WIDTH = 1280;
const HEIGHT = 720;
const sha = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const write = (file, payload) => fs.writeFileSync(file, JSON.stringify(payload, null, 2) + '\n', { flag: 'wx' });

function once(text, needle, replacement) {
  if (text.split(needle).length !== 2) throw new Error('Diagnostic anchor changed: ' + needle);
  return text.replace(needle, replacement);
}

function instrument(original) {
  const boundary = `test('${TITLE}'`;
  const start = original.indexOf(boundary);
  if (start < 0 || original.indexOf(boundary, start + 1) !== -1) throw new Error('Ambiguous target');
  const prelude = `\nconst dprFs = require('node:fs');
const dprExpected = Number(process.env.PJ_DIAGNOSTIC_DPR);
test.use(require('./support/browser').devicePixelRatioOptions(dprExpected));\n`;
  let selected = original.slice(start);
  selected = once(selected, '  await waitForQtApp(page, consoleMessages);', `  const dprOnLoad = await page.evaluate(() => ({
    pixelRatio: devicePixelRatio, width: innerWidth, height: innerHeight, isolated: crossOriginIsolated
  }));
  expect(dprOnLoad).toEqual({ pixelRatio: dprExpected, width: ${WIDTH}, height: ${HEIGHT}, isolated: true });
  await waitForQtApp(page, consoleMessages);`);
  selected = once(selected, '  const readyMessages = consoleMessages.filter(', `  // Geometry only; avoid screenshots or profiling during the heartbeat window.
  const dprGeometry = await page.evaluate(() => {
    const screen = document.querySelector('#screen');
    const collect = root => root ? [
      ...(root.matches?.('canvas') ? [root] : []),
      ...root.querySelectorAll('canvas'),
      ...[root, ...root.querySelectorAll('*')].flatMap(c => c.shadowRoot ? collect(c.shadowRoot) : []),
    ] : [];
    const canvas = collect(screen)
      .map(c => {
        const css = c.getBoundingClientRect();
        return { id: c.id, css: [css.width, css.height], pixels: [c.width, c.height] };
      })
      .filter(c => c.css.every(x => x > 0) && c.pixels.every(x => x > 0));
    return { pixelRatio: devicePixelRatio, width: innerWidth, height: innerHeight,
      userAgent: navigator.userAgent, canvas };
  });
  const readyMessages = consoleMessages.filter(`);
  // Keep the heartbeat interval identical by taking the geometry snapshot before it starts.
  const marker = '  // Geometry only; avoid screenshots or profiling during the heartbeat window.';
  const g = selected.indexOf(marker);
  const ready = selected.indexOf('  const readyMessages = consoleMessages.filter(', g);
  const hb = selected.indexOf('  await page.evaluate(() => {\n    const heartbeat =');
  if (!(hb >= 0 && hb < g && g < ready)) throw new Error('Heartbeat anchors out of order');
  selected = selected.slice(0, hb) + selected.slice(g, ready) + selected.slice(hb, g) + selected.slice(ready);
  selected = once(selected, '  expect(heartbeat.finished - heartbeat.started).toBeGreaterThan(75);',
    `  dprFs.writeFileSync(process.env.PJ_DIAGNOSTIC_MEASUREMENT, JSON.stringify({
    dprOnLoad, dprGeometry, started: heartbeat.started, finished: heartbeat.finished,
    ticks: heartbeat.ticks, maxGapMs: Math.max(...heartbeatGaps)
  }), { flag: 'wx' });
  expect(heartbeat.finished - heartbeat.started).toBeGreaterThan(75);`);
  return original.slice(0, start) + prelude + selected;
}

function namedTests(suites) {
  return suites.flatMap(s => [
    ...(s.specs ?? []).flatMap(spec => spec.tests.map(t => ({ title: spec.title, ...t }))),
    ...namedTests(s.suites ?? []),
  ]);
}

function validTrial(report, data, ratio, status) {
  const tests = namedTests(report.suites ?? []);
  if (tests.length !== 1 || tests[0].title !== TITLE || tests[0].projectName !== 'firefox'
      || tests[0].results?.length !== 1 || report.stats?.flaky !== 0 || report.stats?.skipped !== 0) return false;
  if (data.dprOnLoad?.pixelRatio !== ratio || data.dprOnLoad?.isolated !== true ||
      data.dprGeometry?.pixelRatio !== ratio || [data.dprOnLoad, data.dprGeometry].some(
        g => g.width !== WIDTH || g.height !== HEIGHT)
      || !data.dprGeometry.canvas?.length || !Number.isFinite(data.maxGapMs)
      || !(data.finished - data.started > 75) || data.ticks?.length <= 2) return false;
  const result = tests[0].results[0];
  if (status === 0) return result.status === 'passed' && data.maxGapMs < 100;
  if (status !== 1 || result.status !== 'failed' || result.errors?.length !== 1 || data.maxGapMs < 100) return false;
  const message = result.errors[0].message?.replace(/\x1b\[[0-9;]*m/g, '') ?? '';
  const actual = message.match(/Expected:\s*< 100\s+Received:\s*([\d.]+)/);
  return !!actual && Math.abs(Number(actual[1]) - data.maxGapMs) < 1e-6;
}

function equalGeometry(a, b, scale) {
  if (a.length !== b.length) return false;
  return a.every((x, i) => x.id === b[i].id &&
    x.css.every((n, j) => Math.abs(n - b[i].css[j]) <= 1) &&
    x.pixels.every((n, j) => Math.abs(n * scale - b[i].pixels[j]) <= 1));
}

function outcome(trials) {
  if (trials.length !== ORDER.length || trials.some((t, i) => !t.valid || t.ratio !== ORDER[i]))
    return 'inconclusive: missing trial, geometry or exact heartbeat outcome';
  const g = trials.map(t => t.data.dprGeometry.canvas);
  if (!equalGeometry(g[0], g[3], 1) || !equalGeometry(g[1], g[2], 1)
      || !equalGeometry(g[0], g[1], 2))
    return 'inconclusive: same CSS canvas and doubled backing dimensions not established';
  const differences = [trials[1].data.maxGapMs - trials[0].data.maxGapMs,
    trials[2].data.maxGapMs - trials[3].data.maxGapMs];
  // A pair is directional evidence only; neither a performance pass nor a cause attribution.
  if (differences.every(d => d >= 10)) return 'directional: larger DPR heartbeat gap in both orders (≥10 ms)';
  if (differences.every(d => d <= -10)) return 'directional: smaller DPR heartbeat gap in both orders (≥10 ms)';
  return 'inconclusive: the balanced pair lacks consistent ≥10 ms separation';
}

function run(root) {
  const tests = path.join(root, 'tests/wasm');
  const evidence = path.join(root, 'replay-evidence');
  const output = path.join(evidence, 'D-dpr');
  fs.mkdirSync(output);
  const source = path.join(tests, 'editors.spec.js');
  const originalProof = path.join(evidence, 'D-original-gate-44938040959.json');
  const receipt = path.join(root, 'validation-receipts/acceptance.json');
  const manifest = path.join(root, 'build-wasm-probe/deploy/manifest.json');
  const artifacts = ['D-package-metadata.json', 'D-evidence-metadata.json'].map(f => read(path.join(evidence, f)));
  const inputHashes = [source, originalProof, receipt, manifest].map(sha);
  const originalSource = fs.readFileSync(source, 'utf8');
  const derived = path.join(tests, 'firefox_dpr_diagnostic.spec.js');
  const config = path.join(tests, 'firefox_dpr_diagnostic.config.cjs');
  const cli = path.join(tests, 'node_modules/@playwright/test/cli.js');
  const browsers = path.join(tests, 'node_modules/playwright-core/browsers.json');
  const cfg = `const c = require('./playwright.config');\nmodule.exports = {
    ...c, projects: c.projects.filter(p => p.name === 'firefox'),
    testMatch: 'firefox_dpr_diagnostic.spec.js', fullyParallel: false, workers: 1, retries: 0
  };\n`;
  fs.writeFileSync(derived, instrument(originalSource), { flag: 'wx' });
  const trials = [];
  try {
    fs.writeFileSync(config, cfg, { flag: 'wx' });
    fs.copyFileSync(derived, path.join(output, 'diagnostic.spec.js'), fs.constants.COPYFILE_EXCL);
    fs.copyFileSync(source, path.join(output, 'original.spec.js'), fs.constants.COPYFILE_EXCL);
    const measured = ORDER.map((ratio, i) => {
      const trial = path.join(output, `trial-${i + 1}-dpr${ratio}`);
      fs.mkdirSync(trial);
      const report = path.join(trial, 'playwright.json');
      const measurement = path.join(trial, 'measurement.json');
      const result = spawnSync(process.execPath, [cli, 'test', '--config', config, '--project=firefox',
        '--workers=1', '--retries=0', '--reporter=line,json', '--grep', TITLE, '--output', path.join(trial, 'results')],
        { cwd: tests, stdio: 'inherit', env: { ...process.env, CI: 'true', PJ_DIAGNOSTIC_DPR: String(ratio),
          PJ_DIAGNOSTIC_MEASUREMENT: measurement, PLAYWRIGHT_JSON_OUTPUT_NAME: report } });
      let data, valid = false, error = result.error?.message;
      try {
        data = read(measurement);
        valid = validTrial(read(report), data, ratio, result.status);
      } catch (problem) {
        error = problem.message;
      }
      const info = { ratio, status: result.status, valid, error, data };
      trials.push(info);
      return info;
    });
    const sameInputs = [source, originalProof, receipt, manifest].map(sha).every((h, i) => h === inputHashes[i]);
    const diagnosis = sameInputs ? outcome(measured) : 'inconclusive: source or acceptance input changed';
    write(path.join(output, 'summary.json'), {
      diagnosticOnly: true, acceptanceResult: 'unchanged', diagnosis, order: ORDER, measured,
      source: read(receipt).identity, sourceSpecSha256: inputHashes[0], originalReportSha256: inputHashes[1],
      receiptSha256: inputHashes[2], manifestSha256: inputHashes[3], derivedSha256: sha(derived),
      artifacts: artifacts.map(a => ({ id: a.id, digest: a.digest, run: a.workflow_run?.id })),
      node: process.version, run: process.env.GITHUB_RUN_ID, attempt: process.env.GITHUB_RUN_ATTEMPT,
      controller: process.env.GITHUB_SHA, runner: process.env.RUNNER_NAME, image: process.env.ImageVersion,
      firefox: read(browsers).browsers.filter(x => x.name === 'firefox'), sameInputs,
    });
    console.log(diagnosis);
    return diagnosis.startsWith('directional:') ? 0 : 1;
  } finally {
    fs.rmSync(derived);
    if (fs.existsSync(config)) fs.rmSync(config);
  }
}

module.exports = { instrument, outcome, validTrial };
if (require.main === module) process.exitCode = run(process.cwd());
