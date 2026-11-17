#!/usr/bin/env node
// SPDX-License-Identifier: MPL-2.0
// The localized total includes every manifest file, including on-demand assets.
// The upstream startup-budget script and its workflow remain independent.
import { readFile } from 'node:fs/promises';

if (process.argv.length !== 3) {
  console.error('Usage: node scripts/wasm_localized_size_budget.mjs <manifest.json>');
  process.exit(2);
}
const manifest = JSON.parse(await readFile(process.argv[2], 'utf8'));
const budget = 26000000;
const bytes = manifest.files.reduce((sum, file) => {
  const size = (file.representations.br ?? file.representations.identity).bytes;
  if (!Number.isSafeInteger(size) || size < 0) throw new Error(`Invalid size for ${file.path}`);
  return sum + size;
}, 0);
console.log(`Localized total: ${bytes} B (budget ${budget} B)`);
if (bytes > budget) {
  console.error(`The localized package exceeds its total budget by ${bytes - budget} B`);
  process.exit(1);
}
