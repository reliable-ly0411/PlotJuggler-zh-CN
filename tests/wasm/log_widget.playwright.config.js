// SPDX-License-Identifier: MPL-2.0
const { defineConfig } = require('@playwright/test');
const { launchOptions } = require('./support/browser');
module.exports = defineConfig({
  testMatch: 'log_widget_targeted.spec.js',
  workers: 1,
  timeout: 120000,
  expect: { timeout: 15000 },
  use: {
    browserName: 'chromium',
    launchOptions: launchOptions('chromium'),
    viewport: { width: 1280, height: 720 },
    screenshot: 'only-on-failure',
  },
});
