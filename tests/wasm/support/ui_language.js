// SPDX-License-Identifier: MPL-2.0
const { expect } = require('@playwright/test');
const translations = require('./ui_translations.json');

// Read the running application's language; never infer it from a test request
// or accept any translated string regardless of the active locale.
async function uiTranslations(page) {
  const messages = [];
  const listener = message => messages.push(message.text());
  page.on('console', listener);
  try {
    // The dedicated probe only reads a property: language selection must not
    // warm font shaping or rendering before a performance measurement. The
    // older read-only probe permits diagnosis of already archived binaries.
    const modern = await page.evaluate(() => {
      if (typeof window.pjWasmReportInterfaceLanguageProbe === 'function') {
        window.pjWasmReportInterfaceLanguageProbe();
        return true;
      }
      window.pjWasmReportCustomWidgetsProbe();
      return false;
    });
    const marker = modern ? 'PJ_WASM_INTERFACE_LANGUAGE value=' : 'PJ_WASM_CUSTOM_UI language=';
    await expect.poll(() => messages.find(message => message.includes(marker))).toBeTruthy();
    const language = messages.find(message => message.includes(marker)).split(marker)[1].split(' ')[0];
    expect(['en_US', 'zh_CN', 'zh_TW']).toContain(language);
    const tr = (context, source, ...args) => {
      const entry = translations[context]?.[source];
      expect(entry, `missing UI expectation: ${context}: ${source}`).toBeTruthy();
      const text = language === 'en_US' ? source : entry[language];
      return text.replace(/%([1-9]|n)/g, (_, index) => {
        const value = args[index === 'n' ? 0 : Number(index) - 1];
        expect(value, `missing argument for ${source}`).not.toBeUndefined();
        return String(value);
      });
    };
    tr.language = language;
    return tr;
  } finally {
    page.off('console', listener);
  }
}

// Keep the original completed/total equality check, including the displayed
// mesh unit in the active language. Other live/draw/placeholder checks remain
// at the call sites.
function completedMeshes(tr, count) {
  const template = tr('pj::scene3d::RobotModelLayer', '  •  %1/%1 meshes', '@COUNT@').trim();
  const escaped = template.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = count === undefined
    ? escaped.replace('@COUNT@', '(\\d+)').replace('@COUNT@', '\\1')
    : escaped.replaceAll('@COUNT@', String(count));
  return new RegExp(pattern);
}

module.exports = { uiTranslations, completedMeshes };
