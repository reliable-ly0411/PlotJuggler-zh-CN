# pj_marketplace

Extension marketplace for PlotJuggler 4: registry fetching, package download, the installed-extension lifecycle
(install, sideload, update, uninstall, enable/disable) and the marketplace UI. Targets: `pj_marketplace` (core),
`pj_marketplace_ui` (`MarketplaceWindow`), the Qt-free `pj-plugin-check` admission helper and the standalone
`pj_marketplace_app` harness. Embedded-manifest discovery comes from the SDK (`plotjuggler_sdk::plugin_host`). The app
consumes it through `pj_runtime`'s `ExtensionCatalogService`, which also seeds the bundled (core) plugins. How it works:
[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Invariants

- Updates, uninstalls and downgrades are staged to the next launch on every platform; a loaded DSO is never replaced or
  deleted in place. dlopen resolves by path name and glibc keeps the first image of a path, so reusing a name inside a
  process serves stale bytes (docs/TECHNICAL_NOTES.md "dlopen pins the first image").
- Never open an extension or staging directory in-process before the startup drain that may replace it, and admit fresh
  bytes through `PluginCheckRunner`, or the process pins the old image and reports old versions.
- One writer per store across processes: every store mutation checks `hasStoreWriteAccess()`; staging siblings (install
  transactions, removal journal, lease, content-addressed store) derive from `PlatformUtils::canonicalStoreRoot()` and
  sit beside the extensions dir, never inside it, or the plugin scan finds scratch and two aliases of one store take two
  leases.
- A removal-journal record authorises a recursive delete: validate it fully, confine it to a direct child of the
  canonical store root, and never let the drain enable an id (the uninstall tombstone stays), or a corrupt record can
  delete outside the store or make a removed plugin loadable.
- The disabled list is persisted and its sync checked before a removal is journalled, on one `QSettings` instance
  (`writeDisabledState`), or a failed deletion lets the removed plugin load again.
- The registry pruning rule in `pj-plugin-registry` depends on admission being monotonic in `min_sdk_required` (no upper
  bound, no ABI check on registry records, platform filter first): change admission rules there first, or released hosts
  lose releases they could load (ARCHITECTURE, "Registry and compatibility").
- `min_plotjuggler_version` is displayed and never gates; the gate is the ABI major plus `min_sdk_required`, evaluated by
  the one `evaluatePluginCompatibility`.
- Paths in messages, logs and JSON go through `utf8_path.hpp`, never `path::string()` or `path(qstring.toStdString())`
  (the Windows code page throws or mangles).
- Build it only as part of the PJ4 tree: `pj_marketplace_ui` links `pj_widgets`, which a standalone configure of this
  directory does not provide.

## Key headers (`include/pj_marketplace/`)

`PlatformUtils::initializeProfile` is the native host's opt-in startup seam for
an absolute dedicated test root. It validates/probes paths before installing
both QSettings INI scopes, and routes store, staging, backup and all canonical
store siblings under the profile. No argument means no global behavior change.
`--plugin-dir` alone is a discovery override, not profile isolation. This is not
a filesystem sandbox for arbitrary plugin code or the IFW installer.

- `include/pj_marketplace/` — public headers (`marketplace.hpp`, `registry_manager.hpp`,
  `registry_resolver.hpp`,
  `download_manager.hpp`, `extension_manager.hpp`, `installed_extension.hpp`,
  `marketplace_window.hpp`, `platform_utils.hpp`,
  `qt_diagnostic_bridge.hpp`, and the store layer). Every header by role, so a helper
  that already exists (SHA-256, the file walk, version ordering, archive budgets) is
  found before it is rewritten: `docs/ARCHITECTURE.md` §3.1.
- `src/core/` — registry/download/extension managers plus the pure registry candidate
  resolver; `src/ui/` — `MarketplaceWindow`
  (`.ui`-driven); `tests/` — manager and store suites share
  the `pj_marketplace_tests` gtest runner and its offscreen-capable `QApplication` main.

## Tests

`gtest_discover_tests` registers each runner case as
`pj_marketplace_tests.<suite>.<case>` and runs it in its own process.
`plugin_check_runner_test` stays separate because it checks admission-helper
process exit results. `extension_manager_test` keeps its mock-target guard,
private temporary profile, settings identity, and entry point because it re-executes
itself in lock-holder mode for the interprocess store lease test. Each process initializes
its own profile before that branch; the child still receives the parent's explicit
store path, preserving the shared store lease. Backups never use a default user
directory. For this runner, `pj-plugin-check` is copied beside the executable for default helper lookup. The helper names the Widget family `"widget"`,
and `PluginCheckRunner` starts it with Qt's library directory first on `LD_LIBRARY_PATH` (Linux) / `PATH`
(Windows), because it `dlopen`s every candidate and a Widget plugin links Qt: outside the AppImage nothing
else lets the loader find `libQt6Widgets`, and a failed load there reads as a rejected plugin. Run the module's registered tests with
`./test.sh -R '^(pj_marketplace_tests\.|plugin_check_runner_test$|extension_manager_test$)'`.
`extension_manager_check_plugin_management` remains
a standalone, network-dependent harness excluded from CTest.

## Docs

| For | Read |
|---|---|
| Module purpose + Conan deps | [`README.md`](./README.md) |
| What it must do | [`docs/REQUIREMENTS.md`](./docs/REQUIREMENTS.md) |
| How it works | [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) |
| End-user flow | [`docs/USER_MANUAL.md`](./docs/USER_MANUAL.md) |
| Registry/package wire format | [`docs/plotjuggler-marketplace-spec-v1.0.0-en.md`](./docs/plotjuggler-marketplace-spec-v1.0.0-en.md) |

## Diagnostic localization

User-facing install, extraction and registry error templates are translated at
their Qt boundary before interpolating paths and IDs. The Qt-free archive policy
keeps its original diagnostics; DownloadManager translates only recognized
complete templates. Unknown plugin, system and library details remain verbatim.

All 34 entries in the pinned official registry have display-only name and description
translations, including uninstalled plugins. The exact ID and English source text
select the translation independently of version; unknown/changed metadata falls
back unchanged. `marketplace_text.hpp` uses the same display mapping in
list rows and the detail panel, before HTML escaping. Known category labels are
translated only for presentation; category filtering and compound sorting retain
registry tokens and original plugin names. Unknown categories remain verbatim.

The host can construct `ExtensionManager` with `defer_initial_scan=true`: pending
transactions and the store lease still initialize, but installed discovery and
store reconciliation wait until `finishInitialScan()`. This lets bundled seeding
replace DLLs before the initial installed-side DSO scan. Default callers retain
the eager snapshot. A deferred caller must finish startup before consuming
installed state or loading managed DSOs.


Website buttons and externally activated detail links use
`pj_widgets/ExternalUrl.h`; HTTP(S) desktop openers in AppImage get the host
environment without changing the marketplace process. Detail-browser relative,
fragment, `file:` and `qrc:` links retain local QTextBrowser navigation; other
schemes retain Qt desktop-services handling.
