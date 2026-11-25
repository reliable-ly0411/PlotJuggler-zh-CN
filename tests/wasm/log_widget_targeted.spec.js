// SPDX-License-Identifier: MPL-2.0
const { test, expect } = require('@playwright/test');
const { bootApp } = require('./support/app');
const { placeholderIconCenter } = require('./support/geometry');

async function customState(page, messages) {
  const before = messages.length;
  await page.evaluate(() => window.pjWasmReportCustomWidgetsProbe());
  await expect.poll(() => messages.slice(before).some(line => line.includes('PJ_WASM_CUSTOM_DONE'))).toBe(true);
  return messages.slice(before);
}

// Exercise real canvas clicks, import, topic drop and epoch history for both
// native layouts and equivalent layouts saved by the retired official plugin.
for (const legacy of [false, true]) {
test(`a native Log restores ${legacy ? 'legacy official widget' : 'native'} layout and epoch history`, async ({ page }) => {
  test.setTimeout(240000);
  const fs = require('fs');
  const path = require('path');
  const { openFileChooser } = require('./support/pickers');
  const { clickActiveDialogButton } = require('./support/dialogs');
  const { dragQtCanvas } = require('./support/canvas');
  await page.addInitScript(() => { delete window.showOpenFilePicker; });
  const { messages, errors, screen } = await bootApp(page);
  page.on('console', message => console.log(`[runtime] ${message.text()}`));
  const chooser = await openFileChooser(page, screen);
  await chooser.setFiles({
    name: 'ros2_log_epoch.mcap', mimeType: 'application/octet-stream',
    buffer: Buffer.from(fs.readFileSync(path.join(__dirname, 'fixtures/ros2_log_epoch.mcap.b64'), 'utf8'), 'base64'),
  });
  await clickActiveDialogButton(page, screen, messages, 'ok');
  await expect.poll(() => messages.some(line => line.includes('PJ_FILE_LOAD_OK') && line.includes('ros2_log_epoch.mcap')),
    { timeout: 60000 }).toBe(true);
  const center = await placeholderIconCenter(page, screen, messages, 'log');
  expect(center.x).toBeGreaterThanOrEqual(screen.x);
  expect(center.y).toBeGreaterThanOrEqual(screen.y);
  await page.mouse.click(center.x, center.y);
  let dock;
  await expect.poll(async () => {
    dock = (await customState(page, messages)).map(line =>
      line.match(/PJ_WASM_LOG_DOCK bindings=0 pending=0 rows=0 x=(\d+) y=(\d+)/)).find(Boolean);
    return Boolean(dock);
  }, { message: "log dock must mount after the real picker click" }).toBe(true);
  let row;
  await expect.poll(async () => {
    const before = messages.length;
    await page.evaluate(() => window.pjWasmReportCurveRowsProbe());
    await expect.poll(() => messages.slice(before).some(line => line.includes('PJ_WASM_CURVE_ROWS_DONE'))).toBe(true);
    row = messages.slice(before).map(line => line.match(/PJ_WASM_CURVE_ROW path=(.+) x=(-?\d+) y=(-?\d+) children=\d+/))
      .find(match => match && match[1].includes('ros2_log_epoch.mcap') && match[1].endsWith('/rosout'));
    return Boolean(row);
  }).toBe(true);
  await dragQtCanvas(page,
    { x: screen.x + Number(row[2]), y: screen.y + Number(row[3]) },
    { x: screen.x + Number(dock[1]), y: screen.y + Number(dock[2]) });
  // The empty dock has no filters. Bind the topic first, then use the actual
  // button to show the future entries; never mutate the model from the test.
  let future;
  await expect.poll(async () => {
    const state = await customState(page, messages);
    future = state.map(line => line.match(/PJ_WASM_LOG_FUTURE x=(\d+) y=(\d+) checked=0/)).find(Boolean);
    return Boolean(future) && state.some(line =>
      /PJ_WASM_LOG_DOCK bindings=1 pending=0 rows=\d+ x=\d+ y=\d+ resolved=1/.test(line));
  }, { message: "bound log must show the unchecked future button" }).toBe(true);
  await page.mouse.click(screen.x + Number(future[1]), screen.y + Number(future[2]));
  await expect.poll(async () => (await customState(page, messages)).some(line =>
    /PJ_WASM_LOG_FUTURE x=\d+ y=\d+ checked=1/.test(line))).toBe(true);
  await expect.poll(async () => (await customState(page, messages)).some(line =>
    /PJ_WASM_LOG_DOCK bindings=1 pending=0 rows=6 x=\d+ y=\d+ resolved=1/.test(line)),
    { timeout: 30000 }).toBe(true);
  // Save actual widget wiring, start a new runtime with no dataset, then load
  // the saved layout before asynchronously picking its source file.
  const { downloadLayoutFromFileMenu } = require('./support/layout_actions');
  const { openLayoutChooser } = require('./support/pickers');
  const { waitForQtApp } = require('./support/app');
  const saved = await downloadLayoutFromFileMenu(page, screen, messages);
  const xml = saved.bytes.toString('utf8');
  fs.writeFileSync(test.info().outputPath('saved-log-layout.xml'), saved.bytes);
  expect(xml).toMatch(/<log\b/);
  expect(xml).toContain('/rosout');
  expect(xml).toContain('future_rows="grey"');
  // Layout-only restore: retain all CustomWidget source identity/wire fields.
  // No automatic file recipe is used; the file arrives through the real picker later.
  let layoutOnly = xml.replace(/<fileInfo\b[^>]*>[\s\S]*?<\/fileInfo>/g, '')
    .replace(/<fileInfo\b[^>]*\/>/g, '');
  if (legacy) {
    layoutOnly = layoutOnly.replace(/<log\b[^>]*>([\s\S]*?)<\/log>/, (_log, topics) => {
      const wires = topics.replace(/<topic\b([^>]*)\/>/g,
        (_topic, attrs) => `<input name="logs" kind="object" slot="0" ${attrs}/>`);
      return `<CustomWidget plugin="log-widget" type="log_viewer">${wires}<config><![CDATA[{"future_rows":"grey"}]]></config></CustomWidget>`;
    });
    expect(layoutOnly).toContain('<CustomWidget plugin="log-widget" type="log_viewer">');
    expect(layoutOnly).toContain('<input name="logs" kind="object"');
  }
  fs.writeFileSync(test.info().outputPath('restored-log-layout.xml'), layoutOnly);
  const beforeReady = messages.filter(line => line.includes('PJ_WASM_APP_READY')).length;
  await page.reload();
  await waitForQtApp(page, messages, beforeReady);
  const layoutChooser = await openLayoutChooser(page);
  await layoutChooser.setFiles({ name: 'late-log-layout.pj4.xml', mimeType: 'application/xml', buffer: Buffer.from(layoutOnly) });
  await expect.poll(() => messages.some(line => line.includes('PJ_WASM_LAYOUT_LOAD_OK name=late-log-layout.pj4.xml'))).toBe(true);
  await expect.poll(async () => (await customState(page, messages)).some(line =>
    /PJ_WASM_LOG_DOCK bindings=1 pending=1 rows=0 x=\d+ y=\d+ resolved=0/.test(line))).toBe(true);
  // bindings() retains the saved unresolved wire; resolved=0 proves it is not
  // falsely bound before the source arrives (the native dock contract).
  const laterChooser = await openFileChooser(page, screen);
  await laterChooser.setFiles({
    name: 'ros2_log_epoch.mcap', mimeType: 'application/octet-stream',
    buffer: Buffer.from(fs.readFileSync(path.join(__dirname, 'fixtures/ros2_log_epoch.mcap.b64'), 'utf8'), 'base64'),
  });
  await clickActiveDialogButton(page, screen, messages, 'ok');
  await expect.poll(async () => (await customState(page, messages)).some(line =>
    /PJ_WASM_LOG_DOCK bindings=1 pending=0 rows=6 x=\d+ y=\d+ resolved=1/.test(line)),
    { timeout: 30000 }).toBe(true);
  expect(errors).toEqual([]);
});
}

for (const [language, preferences] of [['zh_CN', '首选项…'], ['zh_TW', '偏好設定…']]) {
  test(`real browser starts with the ${language} built-in Log tooltip`, async ({ page }, testInfo) => {
    // Standard shipped command-line language option; no translator substitution.
    await page.route('**/qtloader.js', async route => {
      const response = await route.fetch();
      const source = await response.text();
      const headers = { ...response.headers() };
      delete headers['content-encoding'];
      delete headers['content-length'];
      await route.fulfill({ response, headers, body: source + `\nconst originalQtLoad = qtLoad; qtLoad = config => originalQtLoad({...config, arguments: ['--language', '${language}']});\n` });
    });
    const { messages, errors, screen } = await bootApp(page);
    const center = await placeholderIconCenter(page, screen, messages, 'log');
    const tooltip = messages.map(line => line.match(/PJ_WASM_LOG_TOOLTIP value=(\S+)/)).find(Boolean);
    expect(tooltip).toBeTruthy();
    expect(Buffer.from(tooltip[1], 'base64').toString('utf8')).toBe(language === 'zh_CN' ? '日志' : '日誌');
    const lines = await customState(page, messages);
    const ui = lines.map(line => line.match(/PJ_WASM_CUSTOM_UI language=(\S+) actions=(\S+)/)).find(Boolean);
    expect(ui).toBeTruthy();
    expect(ui[1]).toBe(language);
    const glyphs = lines.map(line => line.match(/PJ_WASM_CUSTOM_GLYPHS total=(\d+) missing=(\d+)/)).find(Boolean);
    expect(glyphs).toBeTruthy();
    expect(Number(glyphs[1])).toBeGreaterThan(0);
    expect(Number(glyphs[2])).toBe(0);
    console.log(`PJ_WASM_FONT_RESULT language=${language} total=${glyphs[1]} missing=${glyphs[2]}`);
    const screenshotPath = testInfo.outputPath(`${language}-rendered-picker.png`);
    await page.screenshot({ path: screenshotPath });
    await testInfo.attach(`${language}-rendered-picker`, { path: screenshotPath, contentType: 'image/png' });
    expect(Buffer.from(ui[2], 'base64').toString('utf8')).toContain(preferences);
    await page.mouse.click(center.x, center.y);
    await expect.poll(async () => (await customState(page, messages)).some(line =>
      /PJ_WASM_LOG_DOCK bindings=0 pending=0 rows=0 .* resolved=0/.test(line))).toBe(true);
    expect(errors).toEqual([]);
  });
}

// Ordinary layouts still require data; deferred custom-widget restore must not
// relax the existing empty-catalog guard for layouts with no pending widgets.
test('a layout without custom widgets still refuses an empty browser catalog', async ({ page }) => {
  await page.addInitScript(() => { delete window.showOpenFilePicker; });
  const { messages } = await bootApp(page);
  const { openLayoutChooser } = require('./support/pickers');
  const chooser = await openLayoutChooser(page);
  await chooser.setFiles({
    name: 'empty-layout.pj4.xml', mimeType: 'application/xml',
    buffer: Buffer.from('<root pj4_version="4" binding="generic"/>'),
  });
  await expect.poll(() => messages.some(line =>
    line.includes('PJ_WASM_LAYOUT_LOAD_FAILED name=empty-layout.pj4.xml reason=apply'))).toBe(true);
  expect(messages.some(line => line.includes('PJ_WASM_LAYOUT_LOAD_OK name=empty-layout.pj4.xml'))).toBe(false);
});
