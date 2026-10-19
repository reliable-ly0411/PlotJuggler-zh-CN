# zh.4 audit remediation

> 历史记录：本文中的 zh.4 发布 job 与 exact-tag 触发方式已经归档，不是当前发布入口。当前稳定/开发 CI 仅构建验证；下一次发版准备与命名规范见 [分支与发布规则](BRANCHING.zh-CN.md)。

## Public CI path records

The earlier policy accepted a known DLL filename plus NUL-terminated public Arrow
source paths without checking the binary's recorded hash. That was a policy defect;
the audit did not establish a real credential leak.

`package_privacy.py` now requires either the exact previously observed DLL SHA-256
or a whole-file content fingerprint before any public CI path can be classified.
The fingerprint includes executable code, strings, resource contents, PE headers,
and trailing bytes. It excludes only PE COFF/debug timestamps and six individually
reviewed Qt RCC modification timestamps in `ToolboxMosaico.dll`. The offsets and
file lengths are fixed in `tests/data/public-build-records.json`; they are not
discovered by searching for arbitrary path strings. PE64 layout and timestamp
bounds are checked. Unknown layouts, file lengths or changed content fail closed.

The two independent Windows builds eb7ff9d1 and e340265e have identical fingerprints:

| DLL | Content SHA-256 | Variable fields |
| --- | --- | --- |
| DataLoadParquet.dll | `9a81c69db19cad03828511c79be05f26a35fccee5298501089a62098c5814b88` | COFF timestamp, debug timestamp |
| ToolboxMosaico.dll | `4442db4b37b07c4d76f875d4be048a4c8e8387ac0cebb5f47241b978a591106b` | COFF timestamp, debug timestamp, six Qt resource mtimes |

The manifest records their commits, public Actions run/artifact identities and
original DLL hashes. A changed compiler, dependency, resource layout or other
content requires separate review and a new pinned fingerprint; CI does not update
its own allowlist. The source layouts are documented in Microsoft's
[PE specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
and Qt 5.15.2's
[RCC implementation](https://github.com/qt/qtbase/blob/v5.15.2/src/tools/rcc/rcc.cpp).

All bytes are still scanned for supported GitHub token families, unknown PEM
private keys, personal contacts and unrelated private paths. An approved hash
cannot suppress those checks. `tests/check_package_privacy.py` includes the
auditor's filename/literal counterexample and bounded PE fingerprint tests.
`scripts/verify_public_binary_records.py` checks both actual packaged DLLs and
rejects code changes, appended data, synthetic known-literal files, another user's
path, a token and an unknown private key. Failures log rule/file identities rather
than matched secret material.

The ARM64 GnuTLS package is independently read from Ubuntu's official Jammy
package index: `libgnutls30_3.7.3-4ubuntu1.9_arm64.deb`, package SHA-256
`cce4bf33fa79446ddee42a992e569f12a57c1a6f8916a2e8349249be0f7ad655`.
Its six embedded private-key test vectors match the same six published GnuTLS
3.7.3 source fingerprints already used on x64. The manifest adds only the exact
official ARM64 library hash and the observed linuxdeploy-modified ARM64 library
hash, with CI/artifact provenance. The actual packaged file must still pass all
six existing DER classifications and every unrelated credential/path check.
No key fingerprint or general GnuTLS filename exception is added.

## Seven native packages

`zh-release.yml` orchestrates the reusable Windows/Linux workflows, then collects
exactly seven software files from the same source commit:

| Software | Builder |
| --- | --- |
| Windows x64 ZIP and Qt IFW installer | windows-2022, Qt 5.15.2, MSVC |
| x86_64 AppImage | native x64 runner, Ubuntu 22.04 container |
| aarch64 AppImage | native ARM runner, Ubuntu 22.04 container |
| Ubuntu 24.04 amd64 DEB | Ubuntu 24.04 container |
| Debian bookworm amd64 DEB | Debian bookworm container |
| Debian trixie amd64 DEB | Debian trixie container |

The Debian packages are compiled in their actual distributions. The package audit
records source/build OS/architecture, and DEB dependencies come from
`dpkg-shlibdeps`. The collector checks seven unique expected names, SHA-256/size
against six passing payload audits, source/version identity, native architecture
and actual DEB builder codename. Missing, relabelled, altered, failed-audit,
duplicate or extra files prevent collection. Evidence is uploaded separately
from software. It cannot become a Release attachment through a wildcard over
the evidence directories.

Container jobs scope Git's directory trust to the exact checked-out CI workspace
through that job's environment. Before compiling, the configured source revision
must match Git HEAD, preventing a silent `gsource` archive-version fallback when
Git cannot read the checkout. No host Git configuration is changed.

AppImage build tools run with inherited `APPIMAGE_EXTRACT_AND_RUN=1`, including
the Qt/output plugins spawned by linuxdeploy. A direct Qt plugin API probe is
logged before deployment. This avoids FUSE mounts and privileged container
settings; the parent tool's command-line extraction flag alone is not inherited
by its plugin subprocesses.

## Build-only validation and future tag publication

PRs, default-branch pushes and manual runs build and verify only. They cannot
publish. Publication has a separate job with `contents: write`, gated on a push
of exactly `refs/tags/v3.18.0-zh.4` in this fork. Other jobs use `contents: read`;
no PAT or privileged foreign-PR workflow is introduced. This workflow never
creates, moves or pushes a tag, and refuses to modify an existing Release.

On that separate future tag event, the publisher creates a draft from the exact
seven-file software directory, checks the uploaded asset names/count/sizes and
GitHub SHA-256 digests, then publishes the prerelease. A mismatch leaves a draft
instead of publishing a partial result. Release notes state the actual image
coverage and performance limitations. Reports, screenshots, logs, patches and
checksums remain in CI evidence or the notes; none are extra Release attachments.

Local policy tests do not prove native builds or the future publication action
succeeded. The PR's actual seven-platform CI and a renewed independent audit are
required before merge; no tag, Release or installation is performed by this
remediation work.
