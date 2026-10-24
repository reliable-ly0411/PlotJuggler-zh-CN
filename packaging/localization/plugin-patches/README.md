# Pinned native plugin display patches

These patches are maintained by this Chinese fork, not signed or published by
upstream. `source-lock.json` separates annotated tag objects from peeled source
commits. Every checkout uses the latter, verifies the exact SDK version and
applies a checksum-verified patch. Each plugin uses its own Conan graph and
native build; SDK 0.20.0, 0.32.0 and 0.34.1 are never substituted for one another.
The deferred Mosaico patch is not built or distributed in rc.2.

The patches translate only fixed prose at its construction site:

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

The host publishes `PLOTJUGGLER_UI_LANGUAGE` before loading any plugin. Each
plugin reads an immutable copy on its first display call; preference changes
require restart. The accepted IDs are `en_US`, `zh_CN` and `zh_TW`; missing,
empty, noncanonical and unknown values use English. `text(english, simplified,
traditional)` selects only fixed prose, while `isChinese()` covers both Chinese
scripts for display grammar. Traditional Chinese uses Taiwan terminology such
as 檔案, 匯入, 訊息 and 函式. No locale, credentials or protocol settings are conveyed.
The deferred Mosaico patch uses the same interface, but remains unapplied.

`build_localized_plugins.py` runs the unchanged upstream English tests except
live/smoke scenarios. Assistant uses an explicit pure-model allowlist, excluding
dialog tests that can probe installed CLIs. Additional five-process display
fixtures check Simplified Chinese, Traditional Chinese, English, unknown and
empty-language fallback, including Assistant raw user/model/system/tool data,
MCAP paths, existing Markdown escaping and the immutable startup selection. These
checks make no external AI requests. Native application tests and final original
package visual acceptance remain separately required.

For a fast offline check without Qt, Conan or the SDK, run
`python3 packaging/localization/plugin-patches/test_display_language.py` from
the repository root. It compiles the helper fixture and every fixed-prose tuple
from all maintained patches, tests three languages plus absent/invalid/oversized
values, and checks format placeholders and protocol names. It does not compile
plugin binaries or establish Mosaico release eligibility.

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
