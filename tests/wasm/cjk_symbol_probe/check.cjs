// SPDX-License-Identifier: MPL-2.0
const { chromium } = require('@playwright/test');
(async () => {
  const url = process.argv[2];
  if (!url) throw Error('Usage: node check.cjs URL');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const markers = new Map();
  const errors = [];
  try {
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => {
      const t = m.text();
      const match = t.match(/PJ_QA_GLYPH (zh_CN|zh_TW) index=\d+ glyph=[1-9]\d* family=Noto Sans Symbols 2 cmap=1 outline=1 missing=0 ink=(\d+)/);
      if (match && Number(match[2]) > 100) markers.set(match[1], match[0]);
      if (t.includes('PJ_QA_FAIL')) errors.push(t);
    });
    await page.goto(url);
    for (let i = 0; i < 120 && markers.size < 2 && errors.length === 0; ++i)
      await new Promise(r => setTimeout(r, 500));
    if (markers.size !== 2 || errors.length) throw Error(JSON.stringify({markers:[...markers], errors}));
    for (const line of markers.values()) console.log(line);
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1 });
