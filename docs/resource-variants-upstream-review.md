# Generic resource variants: official 3.17.2 merge assessment

The target is the official **3.17.2** tag of
[PlotJuggler/PlotJuggler](https://github.com/PlotJuggler/PlotJuggler/tree/034a5cc919909aebb124e0dc1abbe2029c3eed0f),
commit `034a5cc919909aebb124e0dc1abbe2029c3eed0f`. The proposed upstream unit
is the small generic patch below. The zh.4 branch is a separate integration PR
in the user's fork.

## Baseline and proposed scope

The official tag is an ancestor of the fork and is the merge base with the
reviewed image commit `eb7ff9d1f50c43fc1c95516667d2ea770e2059ff` (23 subsequent
commits at that snapshot). The tag already has 106 English JPEGs, totaling
6,745,002 bytes, and no Chinese PNG catalog or generic image helper. Its root
CMake uses CMake 3.16, C++17 and Qt5; `LICENSE.md` is MPL-2.0.

The large Chinese PNG payload and regression executable linking that payload
a second time are fork additions. Their size correction helps this edition;
it is not evidence of the same defect in unmodified upstream 3.17.2.

| Component | Recommendation for 3.17.2 | Boundary |
|---|---|---|
| Core/Gui helper | Candidate optional capability | C++17, bounded dimensions/patches, native pixels, DPR/alpha and atomic fallback. No language, meme-ID, translator, plugin or ArduPilot dependency; no plugin ABI change. |
| Focused tests | Include with the capability | Synthetic inputs plus all 106 official English images. Qt Core/Gui only, no Widgets or application/plugin dependencies. |
| Optional QRC and locale adapter | Separate feature design | An upstream adapter needs an opt-in/default-English policy and caller integration. The fork's Chinese-default policy is not part of the generic patch. |
| tests_bin and the huge-test packaging fix | Keep the specific fix in this fork | The Chinese image regression target was introduced by the fork. Upstream has no corresponding large localized test binary to remove. A general package inventory guard can be considered separately. |
| Chinese PNGs/atlases/catalog | Keep in the fork | Edition-specific data, independent provenance/rights review and locale policy. |
| ArduPilot, fork version, sync/build workflows, privacy records | Separate changes | None is required by the helper or its tests. |

## Minimal patch and default English behavior

`python scripts/export_generic_resource_patch.py --out generic-resource-variant-3172.patch`
exports exactly four new MPL-2.0 files: `plotjuggler_app/resource_image.h/.cpp`,
`tests/resource_image_variant_test.cpp`, and
`tests/resource_image_variant/CMakeLists.txt`.

The standalone test target uses the baseline's CMake 3.16, C++17 and Qt5
Core/Gui. Root/app CMake, main.cpp, resource.qrc, locale files and all English
images remain unchanged. The existing explicit application source list does
not link this utility until a caller opts in; default startup adds no loading
or composition calls.

The isolated workflow checks out the clean official tag, asserts its exact SHA,
runs `git apply --index --check`, applies the patch and verifies exactly four
additions. `scripts/check_upstream_resource_patch.py` checks the protected
application files against their Git content and all 106 English JPEG byte
hashes. Ubuntu Qt5 and Windows Qt5.15.2 jobs compile the isolated target and run
GenericResourceImage plus DefaultEnglishImages. The latter confirms that an
empty/default description leaves every official image's pixels and DPR intact.
Artifacts retain the patch, source/hash proof and CTest logs. A green run is
required before those compile/test checks are described as passed.

This builds the minimal utility/test target, not the complete official app.
The unchanged application build graph and files preserve existing default
English behavior. Any future locale/caller integration needs application-level
tests of its own.

## Performance and merge judgment

The measured A/B is **fork zh.3 versus fork zh.4**, with verified production ZIPs
and pinned render implementations. It is not a before/after timing of official
3.17.2. [The performance report](zh4-performance.md) retains eight production
processes per version/mode, 1536 render samples, percentiles, matching runtime
hashes and cache/desktop limitations.

Overlay example 26 renders in 30.951/10.979 ms in primed round-robin tests
(zh.3/zh.4). First-splash visible medians are 227.72/228.68 ms, within the 2 ms
polling interval, so a startup improvement is not established. English fresh
first-render medians increase from 6.851 to 8.210 ms and remain reported. No OS
cache was flushed; direct rendering excludes widget presentation and PNG export.
Disk savings, per-image timing and application working set are separate results.

For upstream 3.17.2, **offer the helper and focused tests as a small optional
capability after clean-tag validation**. Its dependencies and license fit the
baseline, and the additive patch preserves default English operation. Adoption
is a maintainer feature decision. Upstream does not gain the fork's Chinese-PNG
disk savings by adding an unused helper. Split/export the generic change rather
than cherry-pick the mixed fork commits and edition-specific data.

The helper/tests retain MPL-2.0 notices. Fixed source/pixel hashes retain image
derivative provenance and original English bytes/visible credits remain. Repo
licensing alone does not establish rights for every underlying meme photo;
Chinese data is outside this candidate. No new AI generation occurs in this
optimization. No upstream PR, merge, release or installation is performed.

The separately verified 4.x history/Qt6 information is retained only in
[the appendix](resource-variants-upstream-4x-appendix.md).
