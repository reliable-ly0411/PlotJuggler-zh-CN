# PlotJuggler 4 Chinese development

Read `CLAUDE.md`, the relevant module's `CLAUDE.md`, and
`docs/localization/README.zh-CN.md` before changing code. The upstream module,
licensing, portability, and test conventions remain applicable.

## Branches and history

- `main-4.x` is an exact upstream mirror, never a localization integration branch.
- `zh-CN-4.x` is the stable 4.x localization line. An initialized upstream-only
  branch does not imply an accepted Chinese release.
- `zh-CN-4.x-dev` is the development integration line.
- Use `zh-CN-4.x-feat/<topic>`, `zh-CN-4.x-ci/<topic>`, and
  `zh-CN-4.x-docs/<topic>` for focused changes; use
  `zh-CN-4.x-fix/<issue>-<topic>` for issue-specific repairs or diagnostics.
- Preserve meaningful commits and the real upstream ancestry. Use merge commits
  for topic-to-development and development-to-stable promotion. Do not squash,
  force-push, or rebase published history.
- Do not create `zh-CN-4.x/<topic>`: that conflicts with the long-lived Git ref.
- Keep the 3.x `zh-CN`/`zh-CN-dev` lines and historical tags/releases unchanged.
  Port reviewed modules; never merge the entire 3.x fork history into 4.x.
- Run `python3 scripts/check_branch_name.py <branch>` before publication.

## Implementation and verification

Keep English source strings and stable serialized identifiers. Use Qt translation
catalogs for UI localization; avoid changing numeric/data parsing locale. PJ3
Qt5 plugins are not ABI-compatible with the PJ4 SDK. Keep imported extension
licensing and provenance adjacent to its source.

Record the exact upstream and port-source SHAs in
`docs/localization/upstream-baseline.json`. Keep versions in `versions.env` and
use a SemVer development suffix until a release is explicitly prepared.

Run translation/branch checks, the standalone language and BIN regression
suites, and applicable full Linux/Windows builds before promotion. Distinguish
passed, failed, skipped and unrun checks. An isolated parser or language test
pass is not a whole-application build pass.

The 4.x development workflow is build/test-only with read-only repository
permissions. It must not create tags or Releases, upload production packages,
or revive version-hardcoded 3.x release flows. Publication and stable promotion
are separate operations from implementing a topic branch.

## Release and repository maintenance

Before changing versions, branches, packaging, release notes, or public issue summaries, read `RELEASING.md` and follow its repository-specific mapping. Preserve all other instructions in this file and any narrower directory instructions. Published tags and asset bytes are immutable: fix a release through a new version, never by moving a published tag or overwriting assets. Keep upstream mirrors free of fork-only policy and localization changes. Release preparation does not itself grant permission to publish, merge, delete, or change repository settings.
