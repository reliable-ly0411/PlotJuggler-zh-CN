# macOS app bundle

`build_macos_bundle.sh` turns a built tree into `PlotJuggler.app` inside
`PlotJuggler-<version>-macOS-arm64.dmg` (Apple Silicon only; the official plugins
are not built for Intel). This localization branch preserves the upstream
recipe for reference. `.github/workflows/macos-release.yml` is manual-only,
read-only and restricted to the official upstream repository; it cannot run
or publish a macOS package in this fork.

```bash
# after building the pj_app target into build/ against the aqt Qt kit:
packaging/macos/build_macos_bundle.sh --qt-dir .qt/<PJ_QT_VERSION>/macos --plugins-registry
```

## Layout

| Path in `Contents/` | What |
| --- | --- |
| `MacOS/` | `plotjuggler4` and `pj-plugin-check` (the marketplace refuses installs without it) |
| `Frameworks/` | Qt and the Conan libraries, placed by `macdeployqt` |
| `PlugIns/` | the Qt plugins (platform, styles, image formats, TLS), placed by `macdeployqt` |
| `Resources/plugins/` | the curated official plugins, seeded into the user's extension folder on first run (`ExtensionCatalogService`). Not under `PlugIns/`: codesign refuses the non-code `manifest.json` there |
| `Resources/python/` | the embedded CPython stdlib; `main.cpp` sets `PYTHONHOME` to it unless the user set one |

The raster helper (`pj-raster-helper` and its data) is not bundled.

The script fails if any bundled binary links a library outside the bundle or
the OS. `LSMinimumSystemVersion` is the highest deployment target among the
bundled binaries.

## Signing

`--sign <identity>` signs every binary inside out with the hardened runtime;
without it the bundle is ad-hoc signed. The app and `pj-plugin-check` carry
`com.apple.security.cs.disable-library-validation` (`entitlements.plist`):
plugins are not signed by our team. `--notarize` submits the signed image with
`notarytool` (`APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`) and staples it.

An explicitly opted-in upstream manual run signs and notarizes, using the
`MACOS_CERTIFICATE`, `MACOS_CERTIFICATE_PWD` and `MACOS_SIGNING_IDENTITY`
secrets (a "Developer ID Application" certificate). Signing is off by default.
This fork has no automatic macOS build, signing, notarization or Release upload.

An ad-hoc or un-notarized image still runs, but macOS blocks a downloaded copy
until the user opens it once and then picks **Open Anyway** in System Settings >
Privacy & Security, or clears the quarantine flag:

```bash
xattr -dr com.apple.quarantine /Applications/PlotJuggler.app
```

## Localization acceptance boundary

This script does not stage the fork's pinned ArduPilot BIN plugin, rebuilt
localized plugins, CJK fallback font, license/provenance payload or Chinese
package naming. It reads the upstream development registry rather than the
fork's fixed artifact lock. Its conditional checksum comparison also permits
an absent checksum. Do not use its output as an accepted localized package.
A separate macOS packaging task must close these gaps and verify arm64,
plugin/SDK loading, Python, native file dialogs, Metal, signing and a clean
installation before a localized macOS release is considered.
