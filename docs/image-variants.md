# Optional resource image variants (zh.4 development)

The zh.3 Windows payload grew by 313,552,718 bytes relative to zh.2. The main
executable grew by 152,803,840 bytes, and a newly packaged image regression
executable added 160,744,448 bytes. Together these explain 99.9986% of the
installed-size increase; the DLL size difference totals zero. Qt compiled the
resource object once, but linked it into both executables. Staging every file
from `build/bin` then shipped the regression executable. Regression executables
now live in `tests_bin`, with a packaging check to prevent recurrence.

The source image payload also matters: zh.3 added 88 full-resolution Chinese
PNGs (152,789,965 bytes), while retaining 106 English JPEGs (6,745,002 bytes).
Simply re-encoding the complete PNGs losslessly produced 138,409,497 bytes.
The zh.4 variants instead occupy 46,143,582 bytes: 73 native-resolution caption
atlases and 15 complete-image fallbacks. These are **resource bytes**, not a
claim about compressed installer size. CI records actual ZIP, Qt IFW EXE,
AppImage, and native Ubuntu 24.04 DEB sizes separately. The same Qt5 RCC audit
measures zh.2, zh.3, and zh.4 with the real compiler's default compression.

## Generic renderer and build option

`PJ::resourceImageVariant()` in `plotjuggler_app/resource_image.*` depends only
on Qt Core/Gui. It knows no language, meme identifier, or log parser. Callers
provide an original `QImage`, a resource root, and either description:

```json
{"image":"variants/complete.png"}
```

```json
{"canvas":[1536,1024],"patches":[
  {"file":"variants/atlas.png","source":[0,0,1000,180],"at":[120,40]}
]}
```

Coordinates are physical pixels. Each source rectangle is copied at its native
size; the renderer does not resize caption pixels. The caller retains control
of final display size. Invalid files, geometry, or later patches return the
original atomically, with an error. Empty descriptions select the original.
Relative paths, dimensions, pixel counts, and patch counts are bounded.

`PJ_ENABLE_LOCALIZED_IMAGES=ON` is the default. `OFF` excludes the separate
`localized_resources.qrc` and its catalog entirely, while retaining English
images and translated interface text. CI builds and tests both settings.
Image loading/compositing can be proposed upstream separately from the Chinese
catalog, crop selections, fork version, and packaging measurements.

## Source and quality guarantees

The fixed source reference is `3117288ce8d710bde4f7a86ca5ed5240ebb1c301` (zh.3).
The schema-2 catalog records each original JPEG SHA-256, old full PNG SHA-256,
decoded RGBA hash, atlas rectangles, and crop pixel hashes. No English image is
modified. PNG derivatives are lossless, with no EXIF/text/private metadata;
the original provenance remains addressable by Git commit and hash. Original
copyright and visible credits remain. No new AI-generated image, lossy codec,
or runtime codec dependency is introduced.

The background outside a crop is reconstructed from the unchanged English
image. It can therefore differ from the zh.3 generated background. Native
Chinese pixels remain identical, and the outer Qt5 smooth scaling and aspect
ratio are unchanged. A separate Qt5 test compares protected caption pixels
after the actual final scaling, rather than substituting a Pillow preview.

Whole-image fallbacks preserve every decoded pixel of the reviewed zh.3 PNG:

| Image IDs | Reason for keeping the complete image |
|---|---|
| 0 | Cropping produced a visible armor/arm seam. |
| 8, 73 | Right-edge Chinese characters could be clipped. |
| 17, 55, 60, 64, 68, 75, 78, 84, 87, 97, 98 | Distributed captions, transformed/transparent text, diagrams, or altered composition make a local crop unreliable. |
| 67 | Moving the footer left a product-label ghost. |

The existing 10 untranslated image fallbacks and 8 technical-only originals
are retained. This optimization does not claim to finish those translations.
All 88 translated candidates were reviewed for caption completeness, English
coverage, edges, credits, and native resolution; CI exports actual Qt5
before/after images for final visual review.

## Reproduce and verify

Fetch the fixed reference commit, install Pillow 11.3.0 for the development
tools, then run:

```sh
python scripts/rebuild_image_variants.py
python tests/check_memes.py --reference-rev 3117288ce8d710bde4f7a86ca5ed5240ebb1c301 --export-reference reference-memes --pixel-report acceptance/image-pixels.json
```

Set `PJ_MEME_REFERENCE_DIR` to that reference directory and
`PJ_MEME_AUDIT_DIR` to an output directory before running CTest. Tests verify
native pixels, Qt5 display scaling, all 106 English images, language exports,
high DPI, alpha, invalid geometry, atomic fallback, and disabled resources.
The normal UI acceptance also loads the synthetic ArduPilot DataFlash fixture
in both languages; parser sources and other loaders are unchanged.

The read-only resource/package audit workflow verifies immutable release
hashes and inventories ZIP, SquashFS, and DEB payloads without executing the
downloaded applications. Package inventories include per-file sizes and
hashes. Build metadata uses project GitHub noreply addresses. This branch
creates CI artifacts only; it does not publish a Release or install itself.
