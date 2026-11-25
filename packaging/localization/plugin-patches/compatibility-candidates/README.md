# CSV #397 / Log #391 compatibility patches

These fixes are integrated in the **local, uncommitted product-sync worktree**.
No published package, tag or remote integration branch is changed. See
[the exact validation report](../../../../docs/localization/SDK101-CANDIDATE-VALIDATION-20261117.md).

`provenance.json` records exact inputs, upstream fixes and SHA-256 values.
The two WASM patches are verbatim upstream diffs restricted to the owning plugin.
`cmake/PjOfficialPluginCompatibility.cmake` applies them to official plugin commit
`598e966243ef6e75b29cadd5d145559d3eb504c2` after FetchContent, checks patch hashes
and all affected result-file hashes, and accepts a second invocation only when
the result bytes still match. A corrupted source override fails closed.
This source candidate passed native CSV and actual Qt 6.12 Log Widget DSO tests;
that is not a WebAssembly or complete application build pass.

For production native rebuilds, `../csv-loader.patch` now combines the existing
localization/path repair and #397. `../source-lock.json` records its new hash;
the standalone SDK remains **0.34.1**. The strict native preflight additionally
requires `csv_source_test`. Its four #397-affected result files exactly match
the candidate tested with SDK 1.0.1 and independently with SDK 0.34.1.

`native-csv397-after-localization.patch` remains an additive review artifact.
To reproduce it, start with official plugin commit
`ba6ee417d91a01aae778a0ec3a4443a024671123`, apply the *historical* localization
patch from host commit `1613eaec28e7c4aee13f7efc72f5e2b2d73a35ae`, then this
additive patch. Its prerequisite hash is recorded in `provenance.json`.
Do not apply it on top of the current combined `../csv-loader.patch`.

The native candidate retains translated diagnostics and raw offending input,
fails before committing an empty import or asking to continue, adds a
fresh-process language regression and copies the upstream two-case real-DSO
regression unchanged. No upstream version/tag or registry archive hash is
rewritten; the resulting binary remains a recorded localized rebuild.

Preserve patch files byte-for-byte; generic trailing-whitespace hooks change
unified-diff context lines and invalidate recorded hashes. Validate syntax by
applying to the exact sources instead. Full host/FileLoader, Windows, WASM and
final-package acceptance are still required by the
[SDK/API contract](../../../../docs/localization/SDK101-INTEGRATION-CONTRACT-20261117.md).
