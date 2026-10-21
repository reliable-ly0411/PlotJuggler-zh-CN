# Pinned native plugin display patches

These patches are maintained by this Chinese fork, not signed or published by
upstream. `source-lock.json` separates annotated tag objects from peeled source
commits. Every checkout uses the latter, verifies the exact SDK version and
applies a checksum-verified patch. Each plugin uses its own Conan graph and
native build; SDK 0.20.0, 0.32.0 and 0.34.1 are never substituted for one another.
Mosaico's upstream CPM archive is additionally SHA-256 pinned.

The patches translate only fixed prose at its construction site:

- Protobuf: preview headings and source-availability notices; source bytes and
  compiler diagnostics remain unchanged.
- Mosaico: Info labels and internal progress/error prose; server metadata,
  paths, topic status control values and query code remain unchanged.
- Assistant: role headings, own status/settings notices and backend display
  labels. A separate `display_text` never changes canonical `ChatMessage.text`,
  user/model/tool content, persisted history, prompts or backend protocol.
- Transform Editor: fixed validation/help and own library-file status; actual
  Lua compiler errors, source and canonical series identifiers remain unchanged.
- WebRTC: ready/manual display columns only. Path selection/event keys stay raw.

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

## Unresolved release gate

The standalone Mosaico SDK v0.1.0 archive currently supplies no license text.
Its redistribution basis is under verification; the builder fails closed before
rebuilding/staging Mosaico until exact official evidence is recorded. A public
repository, the plugin repository's MIT license, or an official binary download
is not used as a substitute for that missing dependency evidence.
