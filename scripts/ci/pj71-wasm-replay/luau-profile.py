"""Extend only the pinned profile helper's derivative spec, not the original acceptance spec."""
from pathlib import Path
import sys

before = Path(sys.argv[1]).read_text()
needle = """  markBefore('  const heartbeat = await page.evaluate(() => {', 'pj-transform-materialized');"""
assert before.count(needle) == 1
added = r'''
  function observe(needle, replacement) {
    if (block.split(needle).length !== 2) throw new Error(`Expected one Luau diagnostic anchor: ${needle}`);
    block = block.replace(needle, replacement);
  }
  const click = "  await clickActiveDialogButton(page, screen, consoleMessages, 'ok');\n"
    + "  await expect.poll(\n    () => consoleMessages.filter(";
  observe(click,
    "  console.log('PJ_LUAU_PHASE', Date.now(), 'submit-click begin');\n"
    + "  page.on('console', message => {\n"
    + "    if (message.text().includes('PJ_WASM_TOOLBOX_TRANSFORM_READY plugin=toolbox-transform-editor')) "
    + "console.log('PJ_LUAU_PHASE', Date.now(), 'READY observed');\n"
    + "  });\n" + click);
  const materializing = '    async () => (await requestToolboxTransformResult(page, consoleMessages)).materializing,';
  observe(materializing,
    "    async () => {\n"
    + "      console.log('PJ_LUAU_PHASE', Date.now(), 'materialization poll begin');\n"
    + "      const result = await requestToolboxTransformResult(page, consoleMessages);\n"
    + "      console.log('PJ_LUAU_PHASE', Date.now(), 'materialization poll returned', result.materializing);\n"
    + "      return result.materializing;\n    },");
  markBefore('  const plotState = await requestPlotState(', 'pj-transform-exact-series-readback-passed');'''
Path(sys.argv[2]).write_text(before.replace(needle, needle + added))
