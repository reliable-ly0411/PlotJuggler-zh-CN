# Independent upstream and localized WASM validation

The branch-scoped `zh-4x-wasm-candidate.yml` controller calls the same complete
`zh-4x-wasm-lane.yml` validation twice. It does not publish, deploy or promote
branches. Source identities are full commit SHAs; the recorded upstream must
be an ancestor of the candidate. Neither a moving branch nor a release tag
replaces the source pin.

| Lane | Source | Production size gate |
|---|---|---|
| upstream | Unmodified PlotJuggler/PlotJuggler commit in `upstream-baseline.json` | Startup <= 16,932,000 B |
| localized | Exact triggering repository commit | All manifest files <= 26,000,000 B |

The original budget scripts and `wasm-ci.yml` remain unchanged. Each lane also
reports **both** actual startup and total bytes. The localized startup observation
has no invented larger startup limit and is never presented as passing the
reference budget. All images, translations, fonts, licenses and shipped feature
defaults remain in their respective source builds. No estimated resource cost is
subtracted from the localized WASM, and no required resource is relabeled as a
preset to escape a gate. Changing scope does not reduce a downloaded byte.

## Artifact identity and validation

Each lane checks out its source SHA and separately checks out the controller
into `.ci-controller` solely for validation helpers. Upstream product inputs
receive no localization patches or resources. Compiler caches use distinct lane
keys. Artifacts have distinct role, source SHA, production/acceptance kind and
attempt in their names. GitHub scopes them to the run and records archive digests;
production archives and build evidence are retained for 14 days.

`packaging/localization/wasm_receipt.py` records source/tree/controller SHA,
submodule commits, version inputs, CMake configuration, budget-script hash,
manifest/bundle identity and every delivered file's size and SHA-256. It verifies
all manifest representations against the real package before recording counts.
Capture rejects disabled required features, dirty tracked sources and a
production/probe configuration mismatch. Download verification rejects swapped
lane/source/controller/kind, changed or missing files, and added files.

Production receipts use the probes-off configuration and the complete package
with presets. Size gates never use acceptance artifacts. Chromium and Firefox
download their own probes-on acceptance artifact and verify both its ordinary
and presets package before serving either. A reference lane failure cannot
silently suppress the localized lane, but the overall workflow still fails if
any required lane or suite fails.

Each lane retains deterministic packaging, package-script tests, production
deployment/cold boot, Scene3D capability probes, complete Chromium functional
and serial suites, and both Firefox shards. The existing non-blocking Firefox
editors policy is preserved. The localized lane additionally retains its real
JPEG/composition, Chinese glyph/UI, log drag/drop and deferred-layout tests.
Serial output and failure screenshots are retained separately from other suites.

## Baseline history and unresolved acceptance

The inherited 16,932,000 B limit and current upstream script have different
origins: `5002da40` excludes on-demand Python stdlib and uses 20,000,000 B in its
own workflow. This controller keeps 16,932,000 B as its stricter reference gate;
it does not overwrite either original script or the source workflow. Replaying
the frozen pre-sync script on b8 counts Python stdlib too (25,246,085 B versus
24,578,977 B with the current script). That accounting difference is not shrinkage.

The original b8 run failed its then-combined startup gate despite passing the
localized total. Its browsers did not run. Upstream's existing run also failed
the 2000 ms anymal responsiveness assertion with a 2403 ms task. Both failures
remain in `SYNC-CANDIDATE-20261117.md`; neither is waived. Only the new exact-head
source, build, real browser, native and applicable package results can establish
acceptance. No workflow result authorizes a stable/development merge or release.
