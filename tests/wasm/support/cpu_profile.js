// SPDX-License-Identifier: MPL-2.0
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { createHash } = require('node:crypto');

// Bind the sampled derivative to the exact original test and package; upstream
// and localized binaries keep their own probes and language assertions.
async function startAnymalProfile(page, testInfo, packageDirectory, testDirectory) {
  const sha = async file => createHash('sha256').update(await fs.readFile(file)).digest('hex');
  return startChromiumProfile(page, testInfo.outputPath('cpu-profile'), {
    source: process.env.PJ_SOURCE_SHA,
    controller: process.env.PJ_CONTROLLER_SHA,
    role: process.env.PJ_VALIDATION_ROLE,
    packageManifestSha256: await sha(path.join(packageDirectory, 'manifest.json')),
    fixtureManifestSha256: await sha(path.join(testDirectory, 'fixtures/hosted_assets.json')),
    originalSpecSha256: await sha(path.join(testDirectory, 'presets.spec.js')),
    diagnosticSpecSha256: await sha(testInfo.file),
  });
}

// Diagnostic replay only: CDP sampling changes timing and must not replace the
// preceding unprofiled acceptance result. This helper never downloads fixtures.
async function startChromiumProfile(page, directory, identity) {
  await fs.mkdir(directory, { recursive: true });
  const session = await page.context().newCDPSession(page);
  const consoleEvents = [];
  session.on('Runtime.consoleAPICalled', event => {
    const text = event.args.map(arg => arg.value ?? arg.description ?? '').join(' ');
    if (/PJ_WASM_LAYOUT|PJ_FILE_LOAD|PJ_PRESET/.test(text)) {
      consoleEvents.push({ timestamp: event.timestamp, type: event.type, text });
    }
  });
  try {
    await fs.writeFile(path.join(directory, 'identity.json'), JSON.stringify({
      ...identity,
      diagnosticOnly: true,
      browser: page.context().browser().version(),
      cpus: os.cpus().map(({ model, speed }) => ({ model, speed })),
      platform: os.platform(),
      startedAt: new Date().toISOString(),
    }, null, 2));
    await session.send('Runtime.enable');
    await page.evaluate(() => {
      const entries = [];
      const record = items => entries.push(...items.map(item => item.toJSON()));
      const observer = new PerformanceObserver(list => record(list.getEntries()));
      observer.observe({ type: 'longtask' });
      window.pjCpuDiagnosticTasks = { entries, record, observer };
    });
    await session.send('Profiler.enable');
    await session.send('Profiler.setSamplingInterval', { interval: 1000 });
    await session.send('Profiler.start');
    await session.send('Tracing.start', {
      categories: 'devtools.timeline,v8,blink.user_timing,disabled-by-default-devtools.timeline',
      transferMode: 'ReturnAsStream',
    });
  } catch (error) {
    await session.detach().catch(() => {});
    throw error;
  }
  return {
    mark: name => page.evaluate(value => performance.mark(value), name),
    // Run even when the original assertion throws, so the slow load is retained.
    async stop() {
      let timer;
      try {
        const tasks = await page.evaluate(() => {
          const watch = window.pjCpuDiagnosticTasks;
          watch.record(watch.observer.takeRecords());
          watch.observer.disconnect();
          return { timeOrigin: performance.timeOrigin, entries: watch.entries };
        });
        await fs.writeFile(path.join(directory, 'long-tasks.json'), JSON.stringify(tasks));
        await fs.writeFile(path.join(directory, 'console-events.json'), JSON.stringify(consoleEvents));
        const { profile } = await session.send('Profiler.stop');
        await fs.writeFile(path.join(directory, 'main-thread.cpuprofile'), JSON.stringify(profile));
        const complete = new Promise((resolve, reject) => {
          timer = setTimeout(() => reject(new Error('CDP trace did not finish')), 30000);
          session.once('Tracing.tracingComplete', resolve);
        });
        // Observe errors immediately, including when Tracing.end itself fails.
        complete.catch(() => {});
        await session.send('Tracing.end');
        const { stream } = await complete;
        if (!stream) throw new Error('CDP trace completed without a stream');
        const output = await fs.open(path.join(directory, 'timeline.json'), 'w');
        try {
          let eof = false;
          while (!eof) {
            const chunk = await session.send('IO.read', { handle: stream, size: 1024 * 1024 });
            await output.writeFile(Buffer.from(chunk.data, chunk.base64Encoded ? 'base64' : 'utf8'));
            eof = chunk.eof;
          }
        } finally {
          await output.close();
          await session.send('IO.close', { handle: stream });
        }
      } finally {
        clearTimeout(timer);
        await session.detach();
      }
    },
  };
}

module.exports = { startChromiumProfile, startAnymalProfile };
