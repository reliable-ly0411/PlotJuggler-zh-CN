// SPDX-License-Identifier: MPL-2.0
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { uiTranslations, completedMeshes } = require('./support/ui_language');

// Replay the console framing emitted by Qt/Emscripten. Browser tests separately
// verify the requested language against the actual application's property.
function pageWithProbe(message, modern = true) {
  const page = new EventEmitter();
  page.evaluate = async () => {
    page.emit('console', { text: () => message });
    return modern;
  };
  return page;
}

for (const [language, ending] of [['en_US', ''], ['zh_CN', '\n'], ['zh_TW', '\r\n']]) {
  test(`reads exact ${language} despite Qt line framing`, async () => {
    const page = pageWithProbe(`PJ_WASM_INTERFACE_LANGUAGE value=${language}${ending}`);
    const tr = await uiTranslations(page);
    assert.equal(tr.language, language);
    assert.equal(page.listenerCount('console'), 0);
  });
}

test('reads archived multi-field probe without confusing later fields', async () => {
  const page = pageWithProbe('PJ_WASM_CUSTOM_UI language=zh_CN font=Noto glyphs=14\n', false);
  assert.equal((await uiTranslations(page)).language, 'zh_CN');
  assert.equal(page.listenerCount('console'), 0);
});

test('rejects an unsupported language instead of accepting another translation', async () => {
  const page = pageWithProbe('PJ_WASM_INTERFACE_LANGUAGE value=de_DE\n');
  await assert.rejects(uiTranslations(page));
  assert.equal(page.listenerCount('console'), 0);
});


test('completed meshes requires equal counts in the active interface language', async () => {
  const labels = { en_US: 'meshes', zh_CN: '个网格', zh_TW: '個網格' };
  for (const [language, label] of Object.entries(labels)) {
    const page = pageWithProbe(`PJ_WASM_INTERFACE_LANGUAGE value=${language}`);
    const ready = completedMeshes(await uiTranslations(page));
    assert.equal(ready.test(`Microduck  •  27/27 ${label}`), true);
    assert.equal(ready.test(`Microduck  •  26/27 ${label}`), false);
    for (const other of Object.values(labels).filter(value => value !== label)) {
      assert.equal(ready.test(`Microduck  •  27/27 ${other}`), false);
    }
  }
});
