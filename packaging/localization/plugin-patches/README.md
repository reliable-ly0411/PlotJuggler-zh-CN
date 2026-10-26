# Pinned native plugin patches

These patches are maintained by this Chinese fork, not signed or published by
upstream. `source-lock.json` separates annotated tag objects from peeled source
commits. Every checkout uses the latter, verifies the exact SDK version and
applies a checksum-verified patch. Each plugin uses its own Conan graph and
native build; SDK 0.20.0, 0.32.0 and 0.34.1 are never substituted for one another.
The deferred Mosaico patch is not built or distributed in rc.2.

The display patches translate only fixed prose at its construction site:

- MCAP: fixed import/progress/error prose at its generation sites; topic names,
  paths, encoding IDs and external parser diagnostics remain unchanged.
- Protobuf: own fixed parser errors, preview headings and source-availability notices; source bytes and
  compiler diagnostics remain unchanged.
- Mosaico (deferred, not applied): proposed Info/status source patch retained for
  future review only. rc.2 keeps the official original binary and remaining English.
- Assistant: role headings, own status/settings notices and backend display
  labels. A separate `display_text` never changes canonical `ChatMessage.text`,
  user/model/tool content, persisted history, prompts or backend protocol.
- Transform Editor: fixed validation/help and own library-file status; actual
  Lua compiler errors, source and canonical series identifiers remain unchanged.
- WebRTC: ready/manual display columns only. Path selection/event keys stay raw.

## CSV UTF-8 file paths

`csv-loader.patch` fixes the two native file-open sites in CSV Loader 1.0.7,
pinned to `ba6ee417d91a01aae778a0ec3a4443a024671123` and SDK 0.34.1. It
converts the incoming UTF-8 path to a native `std::filesystem::path` before
opening the preview and import streams. CSV decoding, numeric parsing, time
selection, configuration strings, plugin ID/version and ABI remain unchanged.
This functional repair is separate from the five display patches above; it does
not translate CSV data or include the separate APBIN/FFT feedback changes.

Both native platforms consume the same reviewed patch through `source-lock.json`.
The CSV build requires the parser and dynamically loaded plugin path tests,
plus the four existing display-helper checks. The tests generate all inputs;
they cover ASCII, Chinese directory, Chinese filename and supplementary Unicode
paths, exact synthetic values/time axes, and missing-file behavior. Full package
acceptance also restores both generated fields and all three finite samples in
ASCII and Chinese paths with the English and Chinese application sessions.

The seed identity lists only the verified official 1.0.7 DSO hash for each
platform as an eligible same-version predecessor. Unknown same-version builds
remain protected by the existing generic migration policy. The official ZIP
checksums in `registry-lock.json` continue to identify official downloads; new
binary/manifest/identity hashes are recorded separately in `release.json`.
The upstream MIT license, source patch and dependency notices ship beside the
other rebuilt-plugin notices. No private log is a test or package input.

For an isolated proof, use `build_localized_plugins.py --preflight --plugin
csv-loader --work <new-work-directory> --prefix <new-prefix>`. Scoped selection
is rejected without `--preflight`; normal release staging still builds the
complete platform lock. See the [independent source review](../../../docs/localization/CSV-UTF8-SOURCE-REVIEW-20261026.txt)
and [integration supplement](../../../docs/localization/CSV-UTF8-INTEGRATION-20261026.md)
for completed checks and remaining gates. These changes do not modify any
previously published package.

## Display language and provenance

The host publishes `PLOTJUGGLER_UI_LANGUAGE` before loading any plugin. Each
plugin reads an immutable copy on its first display call; preference changes
require restart. No locale, credentials or protocol settings are conveyed.

`build_localized_plugins.py` runs the unchanged upstream English tests except
live/smoke scenarios. Assistant uses an explicit pure-model allowlist, excluding
dialog tests that can probe installed CLIs. Additional four-process display
fixtures check Chinese, English, unknown and empty-language fallback, including
Assistant raw user/model/system data and existing Markdown escaping. These
checks make no external AI requests. Native application tests and final original
package visual acceptance remain separately required.

The rebuilt binary keeps upstream ID/version for ABI and configuration
compatibility. Package `release.json` marks it as a fork-localized rebuild and
records source/tag/SDK, patch/helper hashes, resolved dependency revisions,
new payload hashes and test selection. Original registry checksums identify only
upstream downloads, never these rebuilt binaries. Staging removes the original
plugin directory before copying the rebuilt one, and final package validation
requires an exact file set and hashes. License texts and patches are shipped in
`share/licenses/localized-plugins`. The root source commit binds this builder and
its fixtures. Marketplace upgrades can replace the localized build with an
upstream build; this fork does not claim an upstream signature or offer its own
automatic plugin update feed.

## Mosaico exception in rc.2

Mosaico 1.3.0 remains the original official precompiled package with its original
registry ZIP checksum and exact binary/manifest hashes. It is excluded from the
five-plugin rebuild list, and the replacement helper refuses its ID. No standalone
Mosaico SDK source is newly redistributed or linked by this release. Safe existing
static UI translations remain, but mixed Info/status prose keeps English because
its user-data origin cannot be determined from final plain text.

Independent SDK v0.1.0 redistribution license evidence has not been established;
this is not a conclusion that redistribution is prohibited. The proposed source
patch is deferred until evidence or a typed safe localization interface exists.
Track [issue #20](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/20).
