// SPDX-License-Identifier: MPL-2.0
const { test, expect } = require('@playwright/test');
const { bootApp } = require('./support/app');
test('Qt decodes all JPEG resources and paints each reviewed Chinese composition', async ({page}, testInfo) => {
 const {messages, errors} = await bootApp(page);
 await page.evaluate(() => window.pjWasmShowJpegVisualProbe(-1));
 await expect.poll(() => messages.some(x => x.includes('PJ_WASM_JPEG_COUNT'))).toBe(true);
 const counts = messages.find(x => x.includes('PJ_WASM_JPEG_COUNT')).match(/raw=(\d+) composed=(\d+) total=(\d+)/).slice(1).map(Number);
 expect(counts[0]).toBe(31); expect(counts[1]).toBe(33); expect(counts[2]).toBe(64);
 for(let i=0;i<counts[2];i++) {
  const before=messages.length;
  await page.evaluate(i => window.pjWasmShowJpegVisualProbe(i), i);
  await expect.poll(() => messages.slice(before).some(x => x.includes(`PJ_WASM_JPEG_PAINT index=${i} `))).toBe(true);
  const line=messages.slice(before).find(x => x.includes(`PJ_WASM_JPEG_PAINT index=${i} `));
  console.log(line);
  const dims=line.match(/width=(\d+) height=(\d+) shownw=(\d+) shownh=(\d+)/).slice(1).map(Number);
  expect(dims[0]).toBeGreaterThan(0); expect(dims[1]).toBeGreaterThan(0);
  expect(dims[2]).toBe(dims[0]); expect(dims[3]).toBe(dims[1]);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const name=`qt-jpeg-${String(i).padStart(2,'0')}.png`;
  await page.screenshot({path:testInfo.outputPath(name)});
 }
 expect(messages.filter(x=>x.includes('PJ_WASM_JPEG_ERROR'))).toEqual([]);
 expect(errors).toEqual([]);
});
