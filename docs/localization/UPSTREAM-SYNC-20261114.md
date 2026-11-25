# 2026-11-14 upstream synchronization

## Source scope

- Previous upstream: `8b847cb74fa7938dcfb3b2385b1c7b8db3f69bc0`.
- New upstream: `5a8f2583b0ae336930910c84307bde1a65c31fd3` (60 commits after official 4.1.0).
- Development parent: `cbb4d23f1579e4f93dc5ff1310a8be170ae61291`.
- Four incoming commits: MCP job planning documentation, marketplace admission documentation,
  C numeric locale preservation for Luau, and clearing stale cancellation before the next file load.
- The upstream merge applies without conflicts. Localization, SDK 0.40.0 reviewed snapshot,
  plugin locks, development version and release gates remain unchanged.

## Verification scope

- Translation-related Python tests: 28 passed, one PowerShell-dependent test skipped.
- Native display-language harness unit tests: 4 passed. These exercise the harness, not a native application.
- Catalog checks: zh_CN and zh_TW each 2,113 active messages translated, no unfinished entries;
  placeholders, plural forms and rich-text checks passed. Qt source extraction was not run.
- Branch name and whitespace checks passed.
- Upstream native regressions are included for decimal-comma script/filter compilation and
  cancel/reject followed by another file load. They still require native CI execution on this merged source.
- Ancestry/provenance verification must run after creating the merge commit.

This source synchronization is not a new release or final package acceptance. Published tags,
asset bytes and Latest remain unchanged. No 3.18.1 candidate or diagnostic branch is changed.
