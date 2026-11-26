# pj_runtime technical notes

What was observed, measured or tried behind the current code, with the conditions and when to look again. How the
code works is in [ARCHITECTURE.md](./ARCHITECTURE.md).

## Catalog success diagnostics and startup language

`PluginRuntimeCatalog` translates only the four dynamic-load success templates
in the `PJ::PluginRuntimeCatalog` context, with separate UTF-8 name/path arguments.
Use the multi-argument `QString::arg` overload: plugin names may themselves contain
`from` or `%2`, and must never be parsed or substituted a second time.
`pj_app` installs and retains `AppLanguage` before plugin validation and
`MainWindow` construction. The sink, history and JSON export retain the emitted
session-language text; they do not retranslate historical records. Stable fields
(source, id, level) and unknown error text remain unchanged. English-wording E2E
assertions select `--language en_US`; the runtime Core-only runner installs no
translator and therefore uses source-text fallback. `RuntimeCatalogLanguageTest`
scans real DSOs under all three production catalogs, including opaque Unicode
name/path arguments and unchanged discovery failures.

## Catalog rebuilds during a load

- **Observed:** loading a 30-minute ROS 1 MCAP with 117k series, `CatalogModel` rebuilt the whole catalog on most
  flushes (every 50 ms), and the rebuilds took most of the GUI thread. Deferring a rebuild that a commit triggers during
  an open ingest until four times the last rebuild's cost had passed cut GUI-thread CPU from 14.8 to 8.0 s, process CPU
  from 37.5 to 29.8 s and the load from 21.6 to 20.3 s (Linux x86_64, i7-13700H, two runs each).
- **Observed, with the rebuilds deferred:** in a profiled run of that load, the GUI thread still stopped for 150 to
  290 ms about once a second, and for 1.3 s twice near its start (gaps of a 5 ms timer; 6.9 s of GUI-thread CPU in a
  19 s load). The profile put 85% of it under `CatalogModel::rebuildNow`: deriving all 117k items and comparing them
  with the ones before, about 130 ms a rebuild, when a few topics had gained a column; adding the new rows to the
  curve tree, 2.7 s in all, of which 1.7 s finding a group by scanning its siblings (a flattened array makes
  thousands) and 0.6 s sorting the whole tree after each batch; and walking every item for the playback range on each
  progress tick, 6.5 ms a tick.
- **What the code does:** see ARCHITECTURE "`CatalogModel` rebuilds" and "`CatalogModel` rebuild timing";
  `CurveTreeView` adds a batch of rows through an index of the large groups and sorts only the parents that grew. The
  factor of four between a rebuild's cost and the gap after it (rebuilds take at most a fifth of the GUI thread, while
  one costs under 250 ms), its one-second cap (a new topic shows within a second) and the child count from which the
  tree indexes a parent (`kIndexedFrom` in `CurveTreeView::childNamed`) are reasoning: no other values of them were
  measured.
- **Result:** the same load then stops the GUI thread for 30 to 55 ms a rebuild, and for about 0.5 s twice: when the
  first tens of thousands of rows enter the tree, and at the end of the load, whose rebuild derives everything. In the
  two-run benchmark of `pj_app` TECHNICAL_NOTES "File-load flush interval" (runs other than the profiled one above),
  GUI-thread CPU went from 6.1 to 2.5 s and process CPU from 27.0 to 23.3 s; the load time, which the import thread
  sets, stayed at 19.3 s (Linux x86_64, i7-13700H).
- **Re-test:** when the first fill of the tree matters, adding its rows in slices across event-loop turns; and when a
  topic of ~10k columns that gains one is slow, deriving only its new columns (its items are derived whole, about a
  microsecond each).

## Qt's browser network backend keeps every response body (Qt 6.12.0)

- **Observed (Qt 6.12.0, WebAssembly build):** `QNetworkAccessManager` runs each request through `emscripten_fetch()`
  with `EMSCRIPTEN_FETCH_LOAD_TO_MEMORY`. `QNetworkReplyWasmImplPrivate::downloadSucceeded()` and `downloadFailed()`
  (`qtbase/src/network/access/qnetworkreplywasmimpl.cpp`) copy `fetch->data` into the reply and then set
  `reply->m_fetch = nullptr` without calling `emscripten_fetch_close()`. `QNetworkReplyWasmImpl::close()`, the only
  caller of `emscripten_fetch_close()`, then finds no fetch, so the `emscripten_fetch_t` and its body stay in the wasm
  heap for the rest of the session. A download also peaks at three copies of its body: `fetch->data`, the reply's
  buffer and the caller's `readAll()`.
- **Measured:** opening a preset with a 261 MB recording left the wasm heap at 1084 MiB; a 96 MiB recording downloaded
  and then refused left 96 MiB more in use (`tests/wasm/presets.spec.js`, "a preset recording downloads without
  passing through the wasm heap"); a robot mesh kept its whole body (`tests/wasm/scene3d_url_models.spec.js`, "a URL
  robot mesh leaves no copy in the wasm heap").
- **What the code does:** `browserFetchToFile()` (`BrowserFetch.h`) bypasses Qt: the page's `fetch()` writes each
  chunk into a MEMFS file, which MEMFS keeps as a JavaScript array outside the wasm heap; the SHA-256 is one
  `crypto.subtle.digest` over that array once the body is complete. `pj_app`'s `PresetController` streams preset
  recordings through it (a picked data file is not copied at all: `pj_app`'s `BrowserPickedFile` reads it lazily,
  where Qt's `getOpenFileContent` would hold it whole in a `QByteArray`). Every download that wants the bytes (the
  other preset files; Scene3D's `UrlFetcher` for robot URDFs, meshes and textures) goes through `HttpGet.h`'s
  `fetchBytesWithLimit()`, whose browser side is `browserFetchToBytes()`: no hashing, a scratch file read back into a
  `QByteArray`.
- **Re-test** on every Qt bump: once `downloadSucceeded()` closes the fetch, a `QNetworkAccessManager` download stops
  leaking (it still peaks at the extra copies).

## Browser resident payload pool

- **Observed:** on a 261 MB recording in the browser, playback and seeking cost the same with a 64 MiB pool of resident
  object payloads as with the desktop's 256 MiB.
- **What the code does:** `SessionManager` sizes the browser pool at a quarter of the desktop one, because the wasm
  heap never shrinks and also holds everything else. A single payload larger than the pool is never admitted, so every
  read of it re-fetches it lazily from its source.
- **Re-test** when browser recordings grow well past that size or seeking in the browser is reported slow.

## Time-sliced replay in the browser

## The browser's resident payload pool is 64 MiB

`SessionManager` keeps 64 MiB of ingested object payloads resident in the browser, a
quarter of the desktop's 256 MiB: the wasm heap never shrinks and also holds everything
else. On a 261 MB recording playback and seeking cost the same as with 256 MiB. A single
payload larger than the pool is never admitted, so every read of it re-fetches it lazily
from its source.


## Test processes own their managed marketplace profile

The managed-profile adapter and its regression targets are native-only;
WebAssembly keeps the original test entrypoints without a marketplace dependency.

An AppSession's plugin search override does not redirect its marketplace store,
pending operations, or store siblings. AppSession-bearing shared test runners
opt into `MANAGED_PROFILE`; standalone layout/loader/catalog runners install the
same `PjTestManagedProfile` before their first session. One owned profile lives
across all windows and outlives QApplication. Do not apply this adapter to
production AppProfile contract tests or initialize it once per window.

The adapter restores the prior QSettings default format and shader-disk-cache
attribute after initializing the profile. An already-selected INI user path is
recovered using a unique read-only identity and retained only with an explicitly
supplied, still-live PjTestOwnedDirectory. Its ownership token, link-free tree and
canonical path containment must verify; an unverified prior INI root fails before
profile initialization. The owner must outlive every settings user. The INI system fallback
is deliberately private. NativeFormat remains NativeFormat and Windows mains
must separately install the private HKCU guard before Qt. Fixture SetUp changes
to their own INI paths still take effect. `PlatformUtils::temporaryDir()` and
model/cache/store paths now resolve within the owned profile; external system INI
fallback content is not part of these fixture contracts. No production path API
or QtProject behavior changes.

`ManagedProfileContract_{ini,native,fail,duplicate,unverified,wrong_owner}` checks paths, initialization
failure, settings format/user/fallback, and lifetime with independent processes.
`ManagedProfile.TwoWindowsShareTheProcessStoreAndDoNotOwnItsLifetime` checks the
real shell's multi-window lifetime. Windows NativeFormat behavior and failure
paths require an actual Windows build/run, not a Linux format-only check. The
existing owned-directory helper rejects changed ownership and links before
cleanup; launcher TEMP validation must precede discovery/static initialization.

The native `pj_runtime_storage_tests` runner keeps the complete source-cache,
recording-service and recording-pipeline test translation units outside the
managed AppProfile. Their original contracts require saved directory settings,
caller-selected paths and unwritable-directory failures to remain effective;
production profile overrides would mask or break those contracts. It uses the
same `pj_runtime_tests.` CTest prefix, test macros/libraries/parser fixtures,
and a separate pre-QCoreApplication Windows HKCU guard. Recording fixtures
validate their private INI directory before setting either scope. WebAssembly
retains the original source registration conditions.

`HermeticCatalog` owns a parent before constructing its service, then passes a
new marketplace child and an absent bundled child. Marketplace-derived sibling
paths therefore remain inside the owned parent. Source-cache test cleanup also
uses an owned parent rather than deleting a merely random shared-temp name.

## Process-lifetime widget test fixtures

Windows keeps loaded widget DLL images mapped for the process lifetime. The
WidgetCatalogTest runner therefore uses a parent-owned temporary tree: the child
validates the root/ownership-token lease before allocating fixture subdirectories,
and validates its own marker and link-free tree before handing cleanup back.
Only after the child exits (or is killed and waited for on timeout) does the
parent apply its ordinary strict recursive cleanup. Static registration and
real DLL assertions remain in the child. Ordinary fixtures retain immediate
cleanup; invalid leases, changed markers, links, child failures, and cleanup
failures remain failures. `tests/test_widget_child_cleanup.py` exercises the
actual Qt helper with `PJ_QT_PREFIX` pointing at a Qt installation.

## WebAssembly materialization wakeups

`DataProcessorService` uses a single-shot zero-interval timer, rearmed only
after an unfinished slice. Qt 6.12's browser dispatcher does not count zero
timers towards the activation count used for automatic rearming; explicit
`start()` registers the next wake independently of other events. This replaces
the fork's earlier repeating one-millisecond timer; it is not layered onto it.
The slice budget, notifications, output and strict browser conditions are
unchanged. The native timer unit test pumps Qt events and cannot establish the
browser behavior: keep the actual 30,000-row acceptance with its original
heartbeat and completion bounds.
