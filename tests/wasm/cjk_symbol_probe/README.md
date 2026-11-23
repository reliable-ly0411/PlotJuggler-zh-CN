# CJK symbol fallback witness

This standalone Qt Widgets WebAssembly test does not compile PlotJuggler. It stages
the production font resources, the production font-registration block, and the
actual simplified/traditional catalog samples from the checked-out revision.
The sample context is a QA label; it is not a claim that the desktop-only
Marketplace is enabled in WebAssembly.

1. Run `python3 tests/wasm/cjk_symbol_probe/prepare.py /tmp/pj-glyph-src`.
2. Configure that directory with the same Qt multithread WASM kit and host Qt as
   the application, and build just `pjGlyphProbe`.
3. Serve the generated HTML through Emscripten's `emrun` (cross-origin isolation
   required). Run `npm ci --prefix tests/wasm`, install Playwright Chromium, then
   `node tests/wasm/cjk_symbol_probe/check.cjs http://127.0.0.1:8892/pjGlyphProbe.html`.

Each sentence must render real ink in Qt and have no missing glyphs. The
single U+25B8 range must resolve to one nonzero glyph from Noto Sans Symbols 2,
matching the actual font cmap with a nonempty outline and no split ligature.
The witness treats a different fallback family as failure, even if it displays
an apparently identical triangle.
