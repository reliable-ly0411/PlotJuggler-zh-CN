# Post-4.1 forward integration candidate

## Source identity

- Development parent: `f5f3fa830fe7eb412524d61b5efe8570c3365713`.
- Upstream merge parent: `1d49adade556c122e9e3f42d5cc56a6ebd2cdfdb`.
- Merge base: `7ab23e4f71759e89a133a57d8ad0ae11d763015d`; 12 incoming upstream commits, 142 fork-only commits.
- Upstream still declares 4.1.0; this snapshot contains 55 commits after upstream's official 4.1.0, not an unchanged release.
- Candidate identity: `4.1.0-zh.1.dev.3`, Qt 6.12.0, host SDK 0.39.0.
- Selective generic repair source: `0113492d7a7f96e486de1f9adcde6e43893ab630`.
- Published `v4.1.0+zh.1`, its assets and Latest are unchanged. Stable content is not merged wholesale into development.

## Integration choices

The merge retains modern system-file-dialog APIs, MCP, plugin metadata, three-language catalogs and Copy-only file drop behavior. Scene3D exact sRGB decoding and updated goldens/exposure, pocketfft bandPower, Conda and documentation changes enter through their real upstream ancestry.

Four conflicts were resolved: Conda keeps the fork's libnanoarrow recipe while removing superseded cloudini/kissfft recipes; Nix remains manually triggered; marketplace documentation retains localized catalog and installed metadata contracts while accepting updated upstream architecture prose.

Forward ports add generic dependency identity, strict Mesa/LLVM notice and DLL checks, system D3D deployment, isolated package profiles, four original packages/six clean format-OS reports, CSV runtime localization and FileLoader evidence, Linux tool locks/retries, installer lifecycle checks, and formal localized version routing. The publisher uses numerical draft release/asset IDs and retains original upload receipts, draft/public downloaded-byte checks, old assets and Latest checks.

The SDK 0.34.1 Unicode snapshot and release-specific source-tree/run gates are not transplanted. The optional standalone Windows native kit remains deferred. No one-time recovery workflow or frozen recovery-release ID is included. Historical development candidate triggers remain unchanged; no new candidate entry is admitted.

## Validation and remaining gates

Offline Python suite: 275 executed, 261 passed, 14 skipped. Release-policy suite: 5 passed. Source-sync fixtures: 8 passed. Both language catalogs have 2,107 translated entries and no unfinished entries; this is catalog structure validation, not fresh Qt extraction. Branch-name checks pass. Whitespace inspection reports one existing blank line at EOF in the byte-hashed original Mesa notice; its original bytes are intentionally preserved. All other changed files pass the whitespace check.

Independent review identified an accidental 4.1-only candidate trigger transplant; it was removed and the development trigger allowlist restored. CSV production callers and current API signatures, four-package identity gates, modern dialog APIs and upstream rendering translation boundaries were inspected.

Native language configuration is blocked by missing Qt 6.12 development files in the isolated cloud environment. Full C++ builds, fresh Qt6 lupdate extraction, BIN/SDK runtime suites, new Qt6.12 renderer DLL identity, rendering screenshots and all final packages remain unrun. Prior 4.1 package results are not results for this tree.

The strict provenance test requires the upstream parent to be an ancestor of committed HEAD. It cannot pass before the pending ordinary merge is committed; the uncommitted MERGE_HEAD is exactly the recorded upstream parent. Do not bypass the ancestry assertion.

The development version is intentionally rejected by packaging version_map. Before producing a release candidate, choose and review a new candidate version and explicit build entry; keep development-only source testing separate. Native build/CI, final original-package acceptance and visual review are required before future promotion. No stable or published ref is moved by preparing this candidate.

## Latest upstream follow-up

After the reviewed twelve-commit integration was published as `86133d418f5d2909c1d9c99720c88cab0a3ba3fc` (the same reviewed tree `907f1390797fa9a2508ed8fb5b3bfdd090bd4440`), upstream added `8b847cb74fa7938dcfb3b2385b1c7b8db3f69bc0`. A second ordinary merge incorporates that commit without source conflicts. The full development snapshot now includes thirteen new upstream commits, 56 after official 4.1.0.

The additional upstream change is a WebAssembly-only Qt 6.12.0 compositor override, including its source-offer disclosure. The three upstream changed files are retained without modification from the automatic merge; native Linux/Windows do not compile this WASM-specific source. Browser performance and the WASM build are not verified by the native source checks. Published 4.1 assets and stable refs remain fixed.
