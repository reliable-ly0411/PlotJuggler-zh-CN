# pj_dialog_host

Qt host for plugin-provided dialogs. Plugins (DataSource, MessageParser, Toolbox, Dialog) describe their UIs
declaratively through the dialog protocol in `plotjuggler_sdk/pj_plugins` (its `pj_plugins/docs/dialog-plugin-guide.md`
documents the protocol); this module turns those descriptions into `QWidget` trees and drives the typed event loop
back to the plugin. One static library, `pj_dialog_engine_qt`. Public links: `plotjuggler_sdk::plugin_host`,
`pj_widgets`, `Qt6::Widgets` / `UiTools` / `SvgWidgets`, `plotjuggler_qwt` (`ChartPreviewWidget`; no `Qt6::Charts`).
Private links: `pj_plotting` (the full `PlotWidget` for embedded chart frames) and `pj_runtime` (`AppSession`,
`CatalogModel`).

## Belongs here, and not

- Here: the dialog and panel engines, the per-widget bindings (SDK events to `QObject` signals), embedded widgets
  that only make sense in plugin dialogs (`chart_preview_widget`, `drop_event_filter`) and the Lua / Python syntax
  highlighters for code editors (`src/*_syntax_highlighter.hpp`).
- App dialogs (Preferences, Diagnostics) go to `pj_app`; reusable dialog chrome and controls (`Dialog`, `FileDialog`,
  `MessageBox`, scrubbers) to `pj_widgets`; the protocol itself to `plotjuggler_sdk/pj_plugins`.
- Never link `pj_scene2D` / `pj_scene3D`: a panel's `scene_view` frame gets its view through the `EmbeddedViewHost`
  callbacks the app supplies, which keeps this module free of scene libraries.

## Invariants

Panel refreshes reuse `WidgetDataView::raw()` for the diff's owned copy rather
than parsing the same numeric preview payload twice. The SDK normalizes malformed
JSON to an empty object, so that ambiguous result is separately validated before
replacing the previous view. One-shot commands remain in the typed view while
the diff copy strips them; rejection, identical-data and command replay semantics
remain unchanged.

## What belongs here

## Public headers (`include/pj_plugins/host_qt/`)

The namespace mirrors `pj_plugins`: this is its Qt-side companion. Each header's doc-comment owns the contract.

- `dialog_engine.hpp`: `DialogEngine`, a modal plugin dialog (`openDialog`, `cancelActiveDialog`). `pj_app`'s
  `DialogPresenter` wraps it.
- `panel_engine.hpp`: `PanelEngine`, a long-lived interactive panel (toolboxes) returned as a bare `QWidget*`, closed
  through the plugin's `requestClose("<reason>")` and the `onCloseRequested` callback. A hidden root ticks at 1/10
  rate with a catch-up tick on Show. A `requestSubDialog` is modal on desktop and non-blocking in the browser.
- `widget_binding.hpp`: `applyWidgetData`, `connectWidgetSignals`, the declarative `pj_enable_when` /
  `pj_visible_when` rules. `applyWidgetData` returns the `scene_view` requests it refused, for the engine to deliver
  after the apply.
- `widget_adapters.hpp`: swaps plain `.ui` controls for the styled `pj_widgets` ones (radio group to
  `DualOptionsWidget`, `QCheckBox` to `ToggleSwitch`, combo styling, `pjMarkdown` promotion, scrollbars). The
  originals stay hidden and remain the source of truth for WidgetData and events. Engines run it once after load.
- `embedded_view_host.hpp`: `EmbeddedViewHost`, the create / attach / detach callbacks that supply the view a
  `scene_view` frame embeds. A `PanelEngineConfig` carrying one announces `PJ_DIALOG_HOST_EMBEDS_SCENE_VIEWS`
  (`src/host_info.hpp`, from the engine's constructor; `DialogEngine` announces no capability) and delivers each
  refusal as a `scene_view_error` event.
- `pj_ui_loader.hpp`: `PjUiLoader`, the `QUiLoader` that instantiates the host widgets plugin `.ui` files name
  (`RangeSlider`, `MarkerTimeline`, `DateRangePicker`, `CredentialsEditor`, `SectionHeaderBand`, `Search`,
  `ToggleSwitch`, `PJ::ComboBox`). A new plugin-usable `pj_widgets` control is registered in its `createWidget`.
- `chart_preview_widget.hpp`: a light Qwt chart for toolbox previews. `widget_binding` builds it when the frame
  carries `chart_markers` or the panel has no session and catalog; otherwise `chart_series` renders with the full
  `PlotWidget`. Interaction is off until the `chart_zoom_enabled` key.
- `drop_event_filter.hpp`: turns Qt drops of catalog items into SDK drag-drop events.
- `browser_file_picker_fallback.hpp`: WebAssembly only, `ScopedOpenFilePickerFallback` masks Qt's File System Access
  probe for the length of a Qt file call. `src/browser_save_target.hpp` offers a toolbox's exports as browser
  downloads.

## `.ui` dynamic-property contracts

Plugins set these directly in their `.ui`. They are structural (read when the tree is loaded or adapted, not per
tick) and carry no widget names in the host: any plugin whose layout fits the shape can use one. This table is the
reference for plugin authors.

| Property | Set on | Effect |
|---|---|---|
| `pjColumnSelectorList` (string) | `QTableWidget` | Names a sibling `QListWidget` that drives the table's column selection. The table becomes a read-only mirror: selecting list rows highlights the table columns with matching header text, and direct selection on the table is blocked. |
| `pjInteriorGrid` (bool) | `QTableView` / `QTableWidget` | An interior-only cell grid, with no outer border ruling. |
| `pjInlineGroup` (bool) | the radio buttons of a group | Keeps the group in its authored layout slot instead of the host re-placing it when it adapts the radios into a `DualOptionsWidget`. |
| `pjButtonsFillWidth` (bool) | `QDialogButtonBox` | The buttons share the full row width. |
| `pj_enable_when` (string) | any widget | `"<comboObjectName>:<index>[,<index>...]"`, or clauses joined by `;` (all must hold). The widget is enabled only while every clause's sibling `QComboBox` sits on one of its indices. Re-asserted after every data apply, so it wins over a plugin-pushed `enabled`. Needed in a modal sub-dialog, whose nested event loop the plugin cannot drive. A clause that fails to parse (unknown combo, no numeric index) invalidates the whole rule and the widget stays as authored. |
| `pj_visible_when` (string) | any widget | Same syntax and semantics, for visibility (redirected through the checkbox or radio adapter when the widget was swapped for a styled replacement). Label and editor hide separately: tag both widgets of a `QFormLayout` / `QGridLayout` row for the row to collapse. |
| `pjFollowTail` (bool) | `QPlainTextEdit` | A transcript or log: its first population and any wholesale replacement open on the newest lines; growth keeps a reader who scrolled up in place, and a "jump to the latest" button (`pj_widgets/TailFollowOverlay.h`) shows while they are away from the end. Untagged text opens at the top. |
| `pjMarkdown` (bool) | child `QPlainTextEdit` in a layout | After load, promoted to a read-only `QTextBrowser` with the same object name and properties. `plain_text` renders as GitHub-dialect Markdown with raw HTML disabled, resource loading blocked, and only an explicit click on an `http` / `https` link opening externally. Combine with `pjFollowTail` for a streaming transcript. Cannot promote a `QPlainTextEdit` that is the `.ui` root. |
| `pjToolboxChromeAction` (bool), `chromeActionIcon` (SVG resource path), `chromeActionSlot` (string) | `QAbstractButton` in a toolbox panel | `pj_app` hides the button in the content and stands a proxy in the panel chrome (the banner, or the floating window's title bar), forwarding clicks to the original. `chromeActionSlot="leading"` puts it before the title; anything else after. |
| `pjToolboxSideDrawer` (bool) | one `QWidget` in a toolbox panel | `pj_app` hoists the widget into a full-height, draggable `QSplitter` column at the left of the whole panel chrome, resizable down to its own `.ui` minimum width and persisted per plugin in `QSettings` as `ToolboxDrawerWidth/<plugin id>`. The plugin keeps driving it by name (see `pjHoistedWidgets`). |
| `pj_context_actions` (string) | `QListWidget` | `"id=Label[;id2=Label 2...]"`: a right-click over a row (not empty space) builds a context menu from the clauses, in order. A choice emits `WidgetEventBuilder::itemContextAction(index, id)` with the delivered-order row index; only the id crosses the ABI. A malformed clause (no `=`, empty id or label) is skipped. Absent or empty: no menu. |

- The `pj_enable_when` / `pj_visible_when` closures are cached per loaded root in an `InstalledRules` child
  (`widget_binding.cpp`), found again from any ancestor root on every data apply.
- `pjHoistedWidgets` (`kHoistedWidgetsProperty`, `widget_binding.hpp`) is host-internal: a presentation that moves a
  plugin widget elsewhere in the window records it on the panel root, so the by-name lookups still reach it. Any new
  hoisting presentation must record its widgets there, or they stop receiving data.
- Adding a contract: hoist the name to a `constexpr const char* k...Property` next to its reader and add a row above;
  a bare literal in one `.cpp` is invisible to the plugin authors who should use it (`pjInlineGroup` and
  `pjButtonsFillWidth` are still bare literals).

## Tests

Two gtest runners on the shared gui test main (`pj_add_test_runner`, `cmake/PjTests.cmake`; test files carry no
`main()`):

- `pj_dialog_host_tests`: `dialog_engine_test.cpp` (with the SDK's `mock_dialog.cpp`), `widget_binding_test.cpp`,
  `combo_rules_test.cpp`, `chart_preview_widget_test.cpp`, `browser_save_target_test.cpp`.
- `pj_dialog_host_panel_tests`: `panel_engine_test.cpp` with `mock_panel_plugin.cpp`. A separate runner because both
  mocks define the plugin entry point `PJ_get_dialog_vtable`: never merge them.

Run one runner with `./test.sh -R '^pj_dialog_host_tests\.'`.
## Fixed bundled-plugin display localization

`bundled_translations.hpp` implements the fork's pinned UI display boundary.
`PjUiLoader::load` admits only exact reviewed UI hashes (CRLF normalized to LF
for identity only); object name, property and source text must also match.
Unknown UI bytes or dynamic values are returned unchanged. Noneditable combo
items retain canonical text in a separate role for comparisons/events; editable
inputs and raw data/code/table bodies are never translated by a broad matcher.
Mixed user/internal prose is localized at its typed construction site in the
five rebuilt source-patched plugins; Mosaico retains its official binary and
remaining mixed English (issue #20), not by searching arbitrary plain-text bodies.
See `packaging/localization/plugin-patches/README.md` for build provenance and
`tests/test_bundled_translations.py` plus native Qt regressions for guards.

Official FFT 1.0.1 is also admitted by its exact reviewed UI hash, without
rebuilding its binary. Fixed statuses and anchored templates belong only to its
`status_label`; captured field names, numeric formatting and external error
details are appended verbatim. `selected_value` can contain an arbitrary field
name: its empty-state text is translated only when the same widget-data payload
explicitly disables `btn_compute` (or during static UI loading). Missing state
never consults a stale painted button. See
`docs/localization/PLUGIN-FEEDBACK.zh-CN.md` at the repository root for provenance
and the optional official-binary acceptance harness, including its integration
limits.

The same pinned FFT UI also receives a display-only layout adaptation: the
existing status label and calculate/export buttons move into a full-width footer
outside the chart splitter. Wrapped status text cannot consume the narrow input
column's action height. Widget identities, bindings, enabled states, official
plugin bytes and data semantics remain unchanged; unknown UI hashes receive no
layout adaptation. Qt-only geometry tests and the full-shell acceptance cover
three languages and compact sizes, including dynamic computed/exported text.
