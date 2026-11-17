// SPDX-License-Identifier: MPL-2.0
const { defineConfig } = require('@playwright/test');
const { launchOptions } = require('./support/browser');
module.exports = defineConfig({ testMatch: 'jpeg_visual.spec.js', workers: 1, timeout: 240000,
 use: { browserName: 'chromium', launchOptions: launchOptions('chromium'),
 viewport: {width: 1920, height: 1800}, deviceScaleFactor: 1, screenshot: 'only-on-failure' } });
