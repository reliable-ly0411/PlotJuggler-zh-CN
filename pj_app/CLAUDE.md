# pj_app

The executable shell: `MainWindow`, `main.cpp`, the app dialogs, the left panel and curve list, the file loader, and
the wiring between `pj_runtime`'s `AppSession` and the widget families. It also holds the concrete codecs the runtime
reaches only through interfaces (`SceneImageDecoder`, `SceneVideoFrameSource`), the MCP server, and on WebAssembly the
browser boundary (upload staging, file pickers, durable settings, presets). A class another Qt app could reuse goes
to `pj_widgets`; business logic and data services go to `pj_runtime`. How the subsystems fit together:
[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Invariants

- `~MainWindow` runs a fixed teardown order (recording, pending stream starts, toolboxes, MCP server, tabs, widgets,
  loader disconnect, `delete ui_`); moving a step later leaves a slot or plugin pointing at something already
  destroyed. The order and the reason for each step: ARCHITECTURE "Threads and teardown".
- `MainWindow::toolboxes_` is the single toolbox registry, and `MainWindow::teardownToolbox` the only exit: it
  extracts the entry first, and callbacks handed to Qt look the presenter up by id, so a callback landing mid-teardown
  finds nothing instead of a dying presenter.
- A toolbox panel is reparented once, at its destination; releasing it leaves its parent alone. Each reparent
  re-polishes the whole tree, which is slow in the browser.
- `ToolboxHostWiring.h` holds the wiring shared by `MainWindow::launchToolbox` and `HeadlessDescriptorProviderSession`;
  changing it in one owner only gives a provider plugin a different host when it runs headless.
- The Reload button is re-enabled only by `refreshReloadEnabled()`, from `FileLoader::loadFinished` and from a
  refused `loadFile`. `fileLoaded` / `fileLoadFailed` stay silent on a rejected config dialog and a queued cancel, so
  wiring the button to them leaves it disabled.
- Load progress is wired only through `wireIngestProgress()`; a hand-made copy drifts from what the tests exercise.
  The row's X/bin goes straight to `SessionManager::requestCancel(token, keep_partial)`; the producer honours the
  flag, the shell never prompts.
- Recording is a runtime capability: Record affordances follow `RecordingService::isSupported()`, never a build flag.
  A stream ending mid-capture finalizes only its own file (`RecordingService::onSourceEnded`); stopping the capture
  there would cut every other source's file short.
- `applyWorkspace` restores in order: read-only preflight, display offsets, processors, curve rebind. A processor
  restored before the offsets reads an unsettled display frame; a preflight after any mutation can no longer refuse
  cleanly. `syncCustomTopicsPanel` runs after every restore.
- The `<data_processors>` entries a layout load skipped (`kept_derived_`, exactly the elements
  `DerivedRestoreReport::skipped` names) are written back only by `saveLayoutToPath`; in `xmlSaveState` they would
  reach undo snapshots and `kExact` rollback targets, which then fail on the same missing input.
- Layout import (`LayoutImportBatch`, `HeadlessDescriptorProviderSession`, `SourcePromotionHost`, the
  rewrite-then-classify load path, the growing-import binder) implements host-side invariants defined in
  `docs/layout-import-architecture.md` of the `pj-mcap-server` repository; read it before changing them.
- Only `BrowserPersistence` writes durable browser storage, and only its preference allowlist and bounded source-free
  layout recipes. File paths, upload identities, plugin configuration, credentials, source-bound layouts and stream
  records never enter it: it outlives the page in clear text, where paths and upload identities mean nothing on the
  next load and credentials would be exposed. An unreadable stored envelope is left intact and not imported.
- A Preferences nav row's position is its stack page index: adding or hiding a row without its page shows the wrong
  page.
- A user-visible feature added, removed or moved updates `resources/feature_catalog.json` in the same change.
  `FeatureCatalogResourceTest` fails when an entry point stops naming the live labels or an `evidence` citation
  (`path#token`) stops appearing in its file, so editing a cited comment or string breaks it.
- Custom Topics deletion rights come from `pj_runtime`'s `CustomTopicsPolicy.h`, asked again after a prompt is
  answered; derived-recipe persistence stays in `pj_runtime`'s `DerivedObjects`. The shell only words refusals, runs
  prompts and owns what is UI.
- MCP: the server talks to `MainWindow` only through its public "agent control" block, never as a friend. Public
  owners are server-assigned (`mcp::ownerFor`, `agent-<client>`) and disjoint from plugin ids
  (`PJ::kAgentIdPrefix`); a plugin token acts as its plugin whatever the client claims. App work left for later asks
  `McpServer::stillAuthorized` before applying anything; every request gets exactly one response. Jobs, revocation
  and the user-first rules: [`../docs/MCP_SERVER.md`](../docs/MCP_SERVER.md).
- GUI tests: the shell leaks process-global widget state across `MainWindow` instances, so each `pj_app_gui_tests`
  case runs in its own process; run them through ctest, not the bare binary.

## Key files (`src/`)

- `MainWindow.{h,cpp,ui}`, `main.cpp`: the window and its wiring; startup, CLI flags, crash handler.
- `ui/`: embedded sub-widgets and app dialogs (`LeftPanel`, `CurveListPanel`, `TimelineWidget`, `DiagnosticsDialog`,
  the Scene2D/Scene3D config panels, the Custom Widget picker menu and config page, `McpJobsDialog`).
- `FileLoader`, `LoadInput.h`, `FanoutConfig`, `DialogPresenter`, `DialogWatch.h`, `ui/BatchLoadDialog`: file loading,
  plugin dialogs and the question asked once for a batch of files.
- `IngestProgressController`, `IngestProgressWiring.h`, `SeriesProgressController`: progress rows in the curve tree.
- `StreamingSourceManager`, `TopicDemandController`, `PendingDisplayBinder`: streaming sessions and topic demand.
- `LayoutXml`, `LayoutReplayHints.h`: layout files. `LayoutImportBatch`, `HeadlessDescriptorProviderSession`,
  `SourcePromotionHost`, `LayoutExitWatch`: the cloud layout import.
- `ToolboxPresenter`, `ToolboxChrome`, `ToolboxHostWiring.h`, `PluginPlotTabsController`,
  `PluginSceneViewsController`: toolbox presentation and plugin-owned views.
- `CustomWidgetController`: the Custom Widget picker menu, its config page and the startup crash review.
- `SourceTimelineController`, `DatasetMergeActions`: Source Timeline binding and dataset merge.
- `BrowserFileStore`, `FileSelectionService`, `BrowserPickedFile` (+ `browser_picked_file.js`), `BrowserPersistence`,
  `PresetController`, `WelcomePresetsDialog`: the WebAssembly boundary and presets.
- `mcp/`: `McpProtocol`, `McpBridge.cpp` (`--mcp-bridge`), `McpServer` (+ `McpEndpointHost`), `McpServerTools.cpp`,
  `McpUiTools` (`--mcp-ui-tools`), `McpBrowserLink`.
- `Theme`, `WidgetTuner`, `DebugMode`/`DebugUi`, `Splashscreen`, `DiagnosticDump`, `BuiltinPlugins`,
  `scene_object_classification`, `SceneImageDecoder`, `SceneVideoFrameSource`, `KeySequence`, `RasterKeyMap`: app
  services and helpers.

## Tests

- Runners (`pj_add_test_runner`): `pj_app_gui_tests` (links `pj_app_shell` + `pj_resources`), `pj_app_unit_tests` (Qt-only helpers), `pj_app_media_codec_tests` (the two codecs over `pj_scene2d_core`; run from the source root). Each case registers as `<runner>.<Suite>.<Case>` and runs in its own process (120 s timeout): `./test.sh -R '^pj_app_gui_tests\.'`.
- Suites with their own ctest entry (QRhi display passes, layout-import suites, `file_loader_test`, `source_promotion_host_test`, `headless_descriptor_provider_session_test`, `layout_import_batch_test`, `splash_meme_pool_test`, `ExportedSymbolsGuard`): the reasons and what each guards are in `docs/ARCHITECTURE.md` "Tests". Their per-suite plugin-path definitions must not propagate to other sources.
- A runner's shared GUI main owns its only `QApplication`; its cases do not define a `main()` or create another application.
- The shared GUI main (`cmake/test_mains/pj_test_main_gui.cpp`) gives every test process an application name of its own, so its settings file and data folder are its alone and are removed when it ends. A window opens and locks the default extension store in that folder whatever plugin folder it was given: a test must not assume it shares settings or data with another test process.

Tests answer modal dialogs through `tests/support/modal_answerer.h`. Tests that touch shell icons link
`pj_resources`; `tests/wasm_*probe*` run only in browser acceptance builds. The mixed-layout benchmark
in `benchmarks/` is available with `PJ_BUILD_DEMOS`.

## Native opt-in profile boundary

- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md): threads and teardown, startup, file loading and progress, streaming,
  recording, layouts, cloud import, owned views, toolbox presentation, Custom Topics, Custom Widgets, Log panels,
  browser boundary and presets, MCP, tests, known gaps.
- [docs/TECHNICAL_NOTES.md](./docs/TECHNICAL_NOTES.md): the measurements and incidents behind browser, linking, export
  and packaging choices.
- Cross-module: [derived objects](../docs/derived_objects/ARCHITECTURE.md),
  [recording](../docs/RECORDING_AND_CACHING.md), [MCP server](../docs/MCP_SERVER.md),
  [browser presets](../docs/WASM_PRESETS.md), [browser deployment](../docs/WASM_DEPLOYMENT.md).

`AppProfile` pre-parses `--profile-dir` immediately after the app identity is set,
before WidgetTuner, any app-owned QSettings, or marketplace startup. It delegates
validation and one-time activation to `PlatformUtils`: both INI scopes and core
data/temp paths stay under the explicit absolute root; failure exits, never
falls back to production. The core-only Python selftest honors the same option.
No-option native behavior is unchanged. This is not a plugin/OS/installer
sandbox; explicit user output paths are not rewritten. The Qt-only regression
harness is `tests/profile`; the full native build adds real runtime service tests.
Usage and boundary details: `docs/localization/ISOLATED_PROFILE.zh-CN.md`.

## Interface language lifecycle

`AppLanguage` owns one startup translator for the full UI lifetime. Its choices
are `zh_CN` (the fresh-profile default), `zh_TW` (Taiwan terminology), and `en_US`
(English source text). Preferences save only on acceptance for the next launch;
`--language` is session-only. Exact hyphen aliases are accepted at startup, while
browser durable storage accepts only canonical supported codes. Never change the
numeric/data locale when selecting a UI language. Both Chinese catalogs and Qt
dialog translations are embedded; source checks validate both against lupdate.
Traditional Chinese splash memes use only the eight text-free-artwork caption
compositions, not the reviewed Simplified Chinese raster variants. See
`docs/localization/MULTILINGUAL.zh-CN.md` for plugin and installer boundaries.

## Native package font fallback

Native packages may include `bin/fonts/NotoSansCJKsc-Regular.otf`. `main.cpp` registers
this separately licensed fallback before constructing the shell, keeping the existing
Noto Sans UI family while allowing Chinese text on hosts without system CJK fonts.
The native release packaging copies the pinned font and its OFL text together;
source builds and WebAssembly do not download it at application startup.

WebAssembly embeds the separately licensed Noto Sans SC subset from
`resources/fonts/NotoSansSC`, after the primary PlotJuggler Sans family.
`scripts/check_cjk_font_coverage.py` checks both Chinese catalogs; acceptance
probes also inspect actual action-font glyph shaping in the browser.

## Localized startup artwork

Chinese sessions respect the saved serious/meme artwork choice. The Chinese
meme pool contains 33 available original-image entries plus eight composed
extras; original entries 09/11/13/24 are omitted rather than falling back to
English. This does not mean all 37 originals are translated or that all 41
entries have received packaged-desktop visual acceptance.


## External web links

Help and About links use `pj_widgets/ExternalUrl.h`, also used by release toasts,
the marketplace and plugin Markdown browsers. AppImage HTTP(S) launches restore
the host environment only for the external child; other platforms/packages and
non-HTTP schemes retain Qt handling. Preferences directory opening remains on
Qt's file-URL path and is outside this fix. See
[`packaging/appimage/README.md`](../packaging/appimage/README.md#external-web-links)
for the contract and verification boundary.

## Windows executable contract

The application uses the GUI subsystem and one configured resource,
`plotjuggler.rc.in`, embedding `resources/plotjuggler.ico` plus numeric and full
version metadata from the central version settings. C++ warning flags must not
reach the resource compiler. `WindowsConsole.h` preserves inherited pipes/files
and binds GUI CRT streams before Qt starts; terminal interrupts queue window
closure only for a QApplication, not a core-only self-test. `run.ps1` uses the
explicit native-process wrapper to preserve waiting, arguments and exit status.
`WindowsApplicationContract` checks the linked PE, full version strings and
redirected CLI output; this is not an Explorer/shortcut visual acceptance.

## Fixed-plugin runtime acceptance

With `PJ_CSV_RUNTIME_PLUGIN` set to the verified rebuilt CSV DSO,
`CsvRuntimeFileLoader_{zh_CN,zh_TW,en_US}` runs real FileLoader/DiagnosticDump
empty-input diagnostics and short/scrolling warning Continue/Abort/Close paths.
The packaging workflow enables and runs this strict gate after plugin staging.
It is separate from the earlier native suite and final original-package checks.

## Native test marker ownership

Tests construct `pj_app_test::IsolatedMainWindow` from
`tests/support/isolated_main_window.h`. It prepares the marker in a fresh owned
directory before the shell and installs it through the controller's existing
accessor immediately after construction. The directory outlives MainWindow
teardown. This isolates marker cleanup only; settings, extension stores and
real application CLI processes need their own isolation. Never recursively
remove a default KnownFolder location in a test teardown.
