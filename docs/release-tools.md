# Release maintenance helpers and historical references

The active helper is `scripts/release-tools/release_review.py`. It performs local,
offline checks only. It has no publishing mode, network client, credential handling,
tag creation, release editing, artifact download, or workflow dispatch. Its checks
remain enabled under `python -O`.

This consolidation does not enable the historical workflows, change old tags or
releases, or delete their branches. The stable/development branch policy is separate
from these helpers. Use the maintained builders and audits in `scripts/` for new
builds; the historical branch workflows must not be merged mechanically.

## Historical source mapping

Every original below is stored as an inert JSON reference under
`scripts/release-tools/archive/`. Each JSON contains the exact original text in
`content`, its original Git blob ID, full commit, source path/ref, and SHA256. These
are reference data, not runnable scripts or Actions workflow files. The snapshots
are independent of future branch movement and have no executable file permission.

| Original branch and immutable commit | Archived originals | Reusable result / disposition |
| --- | --- | --- |
| `release/backfill-zh-linux` at [`d4dc8da27b31f4e93147b6c0267537ddc9f562d6`](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/commit/d4dc8da27b31f4e93147b6c0267537ddc9f562d6) | `scripts/release-backfill/{build.sh,verify.sh,publish.py}` and `.github/workflows/zh-linux-backfill.yml` | Source/tag checks become `verify-source`; append-only asset/hash checks become `plan-assets` and `verify-preserved`. Root package installation, old distro dependency assumptions, old version formulas, publication, and release-body modification are archived only. |
| `release/backfill-zh3-linux` at [`52ad3c8c265fc026cca9636f3be816372a3b2d09`](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/commit/52ad3c8c265fc026cca9636f3be816372a3b2d09) | `.github/workflows/zh3-release-assets.yml` | Preserves both inline `PUBLISH_SCRIPT` and `PREPARE_EXISTING_SCRIPT` plus its platform jobs. Exact existing-asset checks inform `plan-assets`; run/source checks inform `verify-ci`. It also inherited the four files archived from `d4dc8da2` unchanged. |
| `release/publish-zh3-existing` at [`4fec8c6e21dd3ff3268bc55f6a2c95eda2386a99`](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/commit/4fec8c6e21dd3ff3268bc55f6a2c95eda2386a99) | `.github/workflows/zh3-existing-assets.yml` | Complete installer/portable file-set and SHA256 comparison becomes `compare-payloads`. This is the corrected historical variant: it merges Qt IFW component payloads and verifies the separately embedded `python312.zip`. It inherits the same four backfill files. |
| `automation/release-v3.18.0-zh.4` at [`7cc4cbddbc005a033c95d520d4303fb2010e9baf`](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/commit/7cc4cbddbc005a033c95d520d4303fb2010e9baf) | `.github/workflows/zh-release.yml` | Exact-source successful-run and required-job checks become `verify-ci`. Its fixed commit/PR/run, annotated-tag creation, release notes, and draft/publish jobs remain historical data only. Maintained seven-package inventory/auditing remains in `scripts/release_assets.py`. |

The archive filenames are the original basenames with `.json` appended, for
example `publish.py.json` and `zh3-existing-assets.yml.json`. None lives inside
`.github/workflows/`.

### Deliberately deprecated behavior

- The old publishers hardcode release tags, release ID `414026871`, workflow runs
  `38751849122`, `38751849476` / `38882790702`, artifact IDs, and branch-head guards.
  Those identifiers are historical evidence, not defaults for new work.
- The original backfill publisher appends release-body text; the extracted
  preservation check instead requires the body and release flags to stay unchanged.
- The original scripts use `assert` for safety checks. Active checks now raise
  exceptions explicitly so optimization cannot disable them.
- Old filename-to-file dictionary comprehensions could silently collapse duplicate
  basenames. Active planning rejects duplicates, unexpected files, symlinks, and
  changed or missing existing-asset digests.
- The old IFW extraction is not a general installer parser. It depends on the
  `3.18.0-3python312.zip` index marker and executes external extraction tools; the
  old AppImage inspection also executes the AppImage to extract itself. Both are
  archived only. `compare-payloads` accepts already-extracted payload directories.
- Do not reuse the old narrow QQ-address scan as the current privacy policy.
  `scripts/package_privacy.py` and the maintained package audits cover additional
  sensitive material and carefully reviewed public dependency markers.

## Offline commands

Python 3.9+ is sufficient. Only `verify-source` also needs Git. The examples assume
`SOURCE`, `TAG`, `VERSION`, and `REPOSITORY` are explicitly supplied for the intended
review; no historical release is selected automatically.

### Confirm unchanged source and an existing tag

```sh
python3 scripts/release-tools/release_review.py verify-source \
  --checkout /path/to/release-source --source "$SOURCE" --tag "$TAG"
```

Requires a full lowercase 40-character commit, matching `HEAD`, a matching existing
tag (annotated or lightweight), and no tracked index/worktree differences from that
commit. This neither fetches nor creates/moves refs. Untracked files are not checked;
use a clean, independently prepared source checkout for a build.

### Plan missing assets without publishing

```sh
python3 scripts/release-tools/release_review.py plan-assets \
  --artifacts /path/to/verified-software \
  --manifest /path/to/reviewed-manifest.json \
  --release /path/to/release-snapshot.json --release-id 123456
```

The manifest uses the maintained collector's fields: `source_commit`, `tag`,
`asset_count`, and `software_assets`, whose entries have `name`, `bytes`, and
`sha256`. `scripts/release_assets.py` already produces this shape for its current
seven-package policy. A deliberately scoped manifest may describe a smaller
historical backfill group; it must be reviewed separately. Every local byte must
match that manifest, and the directory must contain exactly those assets.

The release JSON is an externally obtained GitHub release snapshot. Supply its
intended numeric ID separately. Same-name assets must already be uploaded with
identical size and SHA256; differences are a hard failure, never an overwrite plan.
Unrelated existing assets remain preserved. Output lists missing candidates and
unchanged names, with `dry_run: true` and `published: false`.

This is a comparison tool, not a complete build audit. It trusts the reviewed
manifest's provenance and does not infer commit identity from filenames. A saved
snapshot cannot prove current server state, source-tag identity, or permission to
publish. Any future authorized publishing implementation must re-read live state
immediately before each append, bind the exact tag/source/run/repository, and verify
the resulting upload hashes. This helper does not implement that implementation.

### Compare before/after snapshots for preservation

```sh
python3 scripts/release-tools/release_review.py verify-preserved \
  --before /path/to/before.json --after /path/to/after.json
```

Checks release ID, tag, body, draft/prerelease flags and every pre-existing asset's
ID, size, digest, and upload state. New assets may be present; this command does not
validate their contents. It can also confirm that an unrelated operation left a
release untouched. Snapshots must contain complete asset lists.

### Verify exact-source CI evidence

```sh
python3 scripts/release-tools/release_review.py verify-ci \
  --run /path/to/run.json --jobs /path/to/all-jobs.json \
  --source "$SOURCE" --repository reliable-ly0411/PlotJuggler-zh-CN \
  --required-job verify-seven --allowed-skipped-job publish
```

`run.json` is the GitHub workflow-run object; `all-jobs.json` has `total_count` and
`jobs`. Include every page from the selected run attempt. Each job must carry its
`run_id`, `head_sha`, `name`, `status`, and `conclusion`. Incomplete or duplicate-name
job inventories fail. Repeat `--required-job` for every required gate. All other
jobs must succeed, except explicitly named skipped jobs; required jobs cannot be
in that exception set. No branch, PR, artifact expiry, workflow-definition identity,
or run-attempt freshness is established by offline JSON alone.

### Compare complete unpacked installer and portable payloads

```sh
python3 scripts/release-tools/release_review.py compare-payloads \
  --portable /path/to/portable/payload --installer /path/to/installer/payload \
  --source "$SOURCE" --version "$VERSION" \
  --repository https://github.com/reliable-ly0411/PlotJuggler-zh-CN
```

Pass the exact payload roots containing `BUILD-INFO.json` and the DataFlash plugin.
Both must report the expected commit, version, repository, and `BIN` support. File
sets, sizes, and hashes must match, including raw embedded ZIPs. No installer,
AppImage, or plugin is executed. This verifies equivalence to the supplied portable
payload, not independent completeness, provenance, architecture, privacy, or runtime
acceptance. Extraction, maintained privacy audits, native architecture checks, and
clean-runtime GUI/BIN acceptance are still required separately.

## Tests

```sh
python3 scripts/release-tools/test_release_review.py -v
python3 -O scripts/release-tools/test_release_review.py -v
```

Tests use synthetic bytes and local JSON only. Git source tests create an isolated
temporary fixture repository. The suite checks source/tag/dirty-tree guards,
complete CI identity, no-op/missing/changed asset plans, duplicate paths, symlinks,
snapshot preservation, complete payload comparison, and archive hashes. It does
not build the application, validate a real IFW extractor, or exercise GitHub writes.
