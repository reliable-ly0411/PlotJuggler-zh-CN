// SPDX-License-Identifier: MPL-2.0
const fs = require('node:fs/promises');
const path = require('node:path');

// Installed only in a separate sampled replay, never in the acceptance case.
function installEditorEvidence(test) {
  const messages = new WeakMap();
  test.beforeEach(async ({ page }) => {
    const entries = [];
    messages.set(page, entries);
    page.on('console', message => entries.push({ at: Date.now(), type: message.type(), text: message.text() }));
    page.on('pageerror', error => entries.push({ at: Date.now(), type: 'pageerror', text: String(error) }));
  });
  test.afterEach(async ({ page }, testInfo) => {
    // Write console evidence first, even if a stalled main thread cannot answer.
    await fs.mkdir(path.dirname(testInfo.outputPath('editor-console.json')), { recursive: true });
    await fs.writeFile(testInfo.outputPath('editor-console.json'), JSON.stringify(messages.get(page) || []));
    let timer;
    let state;
    try {
      state = await Promise.race([
        page.evaluate(() => {
          const heartbeat = globalThis.__pjWasmTransformHeartbeat;
          return {
            timeOrigin: performance.timeOrigin, now: performance.now(),
            marks: performance.getEntriesByType('mark').map(entry => entry.toJSON()),
            heartbeat: heartbeat ? { started: heartbeat.started, ticks: heartbeat.ticks } : null,
          };
        }),
        new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Page evidence timed out')), 5000); }),
      ]);
    } catch (error) {
      state = { observationError: String(error) };
    } finally {
      clearTimeout(timer);
    }
    await fs.writeFile(testInfo.outputPath('editor-state.json'), JSON.stringify({
      diagnosticOnly: true, status: testInfo.status, errors: testInfo.errors, ...state,
    }, null, 2));
  });
}

module.exports = { installEditorEvidence };
