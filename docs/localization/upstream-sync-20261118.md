# Upstream integration checkpoint (2026-11-18)

Status: conflict resolution checkpoint, **not release acceptance**. Do not promote this branch to the stable line until native and browser regression evidence is complete.

## Frozen inputs

- Localized candidate: `56d552ddd0906a4f1da2768c377bd7c7349a58bf`.
- Upstream: `aa365846c3e5f5f1ed4f17fb54845ad6413c8de3`.
- Earlier upstream baseline: `5002da40a6499cb99c1073d5b8c611f1e825cb4b`.
- SDK 1.1.0 immutable source: `d65923cd11ab7a822ef7b802523e2fc7b281f515`; archive SHA256 `57f7c40f672bdfc0d6a6cef18a27361483963e646986ff092c24ff6d87ffb4f9`.

The independent branch does not change the stable/development branches, release tags, or an in-flight packaging candidate. Packaging changes after the localized input need a separate reviewed integration.

## Merge decisions

Preserve the localized workflow policy, translation wrappers, canonical stored identifiers, UTF-8 path handling, isolated profile guards, delayed plugin loading and existing regression tests. Adopt upstream product changes outside those conflicts, including streaming fixes and usage counters. Retain both local and upstream object-binding regression coverage. Avoid a duplicate early ingest notification before loader cleanup.

The localized application defaults both startup telemetry and usage reporting to **off**. Only explicit preference acceptance enables either. Canceling the preferences dialog must not record consent. Existing explicit choices are preserved. No real telemetry endpoint was contacted during this integration. New preference and loopback-only reporter tests cover opt-in and revocation, but their native execution is still pending.

## Evidence and limitations

- Qt 6.11.1 preliminary extraction: simplified/traditional Chinese each 2169/2169 active messages, no unfinished, missing or stale entries; placeholders and rich-text attributes checked. This is not the pinned Qt 6.12 acceptance run.
- SDK snapshot checks: 4 passed.
- Localized telemetry source policy: 3 passed.
- Merged translation source check: 1 passed.
- Registry inventory checks: 5 passed.
- Official plugin patch application/idempotency/CRLF/hash checks: 4 passed, none skipped.
- Conflict markers/index and whitespace checks passed before this checkpoint.

Pending: pinned Qt 6.12 native configure/build, preference/counter/reporter tests, binding/streaming regressions, SDK and APBIN compatibility, native UI and WASM browser/size checks. No prior-head test result substitutes for final-head acceptance. Do not describe this checkpoint as fully tested or releasable.
