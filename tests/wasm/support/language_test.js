// SPDX-License-Identifier: MPL-2.0
const { test: base, expect } = require('@playwright/test');
const { uiTranslations } = require('./ui_language');

const requested = process.env.PJ_WASM_TEST_LANGUAGE;
if (requested && !['en_US', 'zh_CN', 'zh_TW'].includes(requested)) {
  throw new Error(`Unsupported PJ_WASM_TEST_LANGUAGE: ${requested}`);
}

// Opt-in three-language replay of the same functional tests and assertions.
// Persist through reloads, but verify the running Qt language after boot.
const test = base.extend({
  context: async ({ context }, use) => {
    if (requested) {
      await context.addInitScript(language => {
        localStorage.setItem('qt-v0-PlotJuggler-PlotJuggler4-BrowserPersistence/preferences_v1',
          '@ByteArray(' + JSON.stringify({ version: 1, values: { 'Preferences::language': language } }) + ')');
      }, requested);
    }
    await use(context);
  },
});

async function expectRequestedLanguage(page) {
  if (requested) {
    expect((await uiTranslations(page)).language).toBe(requested);
  }
}

module.exports = { test, expect, expectRequestedLanguage };
