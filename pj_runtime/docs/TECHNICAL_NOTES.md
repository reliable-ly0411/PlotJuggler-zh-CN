# pj_runtime technical notes

Hard-won lessons behind code in this module, written as the current state of the code.

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

## Qt's browser network backend keeps every response body (Qt 6.12.0)

**What happens.** In the WebAssembly build, `QNetworkAccessManager` runs each request
through `emscripten_fetch()` with `EMSCRIPTEN_FETCH_LOAD_TO_MEMORY`.
`QNetworkReplyWasmImplPrivate::downloadSucceeded()` (and `downloadFailed()`) in
`qtbase/src/network/access/qnetworkreplywasmimpl.cpp` copy `fetch->data` into the reply
and then set `reply->m_fetch = nullptr` without calling `emscripten_fetch_close()`.
`QNetworkReplyWasmImpl::close()`, the only caller of `emscripten_fetch_close()`, then
finds no fetch, so the `emscripten_fetch_t` and its body buffer stay in the wasm heap
for the rest of the session. A download also peaks at three copies of its body:
`fetch->data`, the reply's buffer and the caller's `readAll()`.

**Measured.** Opening a preset with a 261 MB recording left the wasm heap at 1084 MiB;
a 96 MiB recording downloaded and then refused left 96 MiB more in use (`tests/wasm/presets.spec.js`,
"a preset recording downloads without passing through the wasm heap"), and a robot mesh kept its
whole body (`tests/wasm/scene3d_url_models.spec.js`, "a URL robot mesh leaves no copy in the wasm heap").

**What the code does.** `browserFetchToFile()` (`BrowserFetch.h`) bypasses Qt: the
page's `fetch()` writes each chunk into a MEMFS file, which MEMFS keeps as a JavaScript
array outside the wasm heap; the SHA-256 is one `crypto.subtle.digest` over that array once the body is complete.
`pj_app`'s `PresetController` streams preset recordings through it (a picked data file is not copied at all:
`pj_app`'s `BrowserPickedFile` reads it lazily; Qt's `getOpenFileContent` would hold it whole in a
`QByteArray`); every download that
wants the bytes (the other preset files, Scene3D's `UrlFetcher` for robot URDFs, meshes and
textures) goes through `HttpGet.h`'s `fetchBytesWithLimit()`, whose browser side is
`browserFetchToBytes()`: no hashing, a scratch file read back into a `QByteArray`.

**Re-test** on every Qt bump: once `downloadSucceeded()` closes the fetch, a
`QNetworkAccessManager` download stops leaking (it still peaks at the extra copies).

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
