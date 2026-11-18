# Qt Installer Framework Chinese standard-page catalog

This directory redistributes the unmodified `ifw_zh_CN.ts` from Qt Installer
Framework **4.10.0**, source commit
`326d161c66eef5b02a54f01867bc593e0c5f41ac`:

https://github.com/qtproject/installer-framework/blob/326d161c66eef5b02a54f01867bc593e0c5f41ac/src/sdk/translations/ifw_zh_CN.ts

SHA-256: `647329c572956c814ba887f291782c6764423e6930467cf672539e91adce1000`.
Copyright belongs to the Qt contributors. The accompanying
`LICENSE.GPL3-EXCEPT` is the upstream license (GPLv3 with Qt Company exceptions).
The entire unmodified IFW source is available at:
https://github.com/qtproject/installer-framework/tree/326d161c66eef5b02a54f01867bc593e0c5f41ac

The packaging script compiles all 700 finished messages and embeds the result,
along with the selected Qt kit's `qtbase_zh_CN.qm`, under
`:/translations_new`. This is the documented IFW translation override mechanism.
It does not replace license agreement text or translate application payloads.

IFW 4.10.0 `src/sdk/sdk.pro` selects `*_??.ts`, which excludes the region-qualified
Chinese filename. Merely listing a component's `zh_CN.qm` does not translate
standard wizard pages. `config.xml` must not force a `<Translations>` list:
IFW interprets it as a fixed set to load, not available languages, and bypasses
`--lang` selection in that case. See upstream `src/sdk/sdkapp.h` and
https://doc.qt.io/qtinstallerframework/ifw-customizing-installers.html .

## Traditional Chinese work in progress

`ifw_zh_TW.ts` is a downstream translation derived from the same pinned
4.10.0 catalog, not an official Qt Traditional Chinese catalog. It retains
all 700 context/source entries and the accompanying upstream license.
Modifications dated 2026-11-18 translate all 700 messages into Traditional
Chinese, including 16 singular/plural entries. This completes the text catalog,
not the installer integration or runtime validation.

The pinned upstream tree has no `ifw_zh_TW.ts`; the official
[Qt translation index](https://l10n-files.qt.io/l10n-files/) also lists no
Traditional Chinese IFW catalog in its 4.11 section. QtBase has its own
Traditional Chinese catalog and must be included separately from the selected
Qt kit when this feature is enabled.

This catalog is not yet wired into packaging or the language selector.
Before enabling it, run `python scripts/test_ifw_traditional_catalog.py`, compile both IFW and
component catalogs with `lrelease`, check placeholders and markup, embed
the matching QtBase dictionary, and validate all six language-restart
directions on Windows. Preserve the upstream license and source offer when
packaging the modified catalog.

### Experimental stage preparation (not enabled for shipping)

The selected Qt 6.12.0 source contains
[qtbase_zh_TW.ts](https://github.com/qt/qttranslations/blob/v6.12.0/translations/qtbase_zh_TW.ts),
Git blob `e9eb453f90d2616d0990797259f56a469fbcef93`.
Do not substitute a binary from another Qt version. Use
`<selected-kit>/translations/qtbase_zh_TW.qm` and retain that kit's Qt
license/provenance materials. Presence of a source file is not evidence that
the installed kit includes the binary, nor that every QtBase message is translated.

`../prepare_traditional_stage.ps1` provides opt-in preparation for a disposable
fixture stage. It is deliberately not called by release or default packaging.
It requires complete 700 + 14 catalogs, the selected kit's QtBase binary and
`lrelease.exe`; compiles a merged IFW/component dictionary; embeds both
`ifw_zh_TW.qm` and the QtBase alias `qt_zh_TW.qm` under
`:/translations_new`; and only then appends the third language entry.
It records binary hashes and tool version in `traditional-stage.json`.
The checked-in two-language UI remains unchanged.

Validation sequence on a Windows runner or approved local workspace:

1. Run `python scripts/test_ifw_traditional_catalog.py` and
   `node scripts/test_installer_language.js` (35 pure-script assertions).
2. Create the existing synthetic installer fixture in a disposable stage,
   using the exact branch commit and selected Qt/IFW tools. Do not use a real
   installed application's target directory.
3. Run `prepare_traditional_stage.ps1 -QtBin <kit>/bin -StageDir <fixture-stage>`.
4. Rebuild the disposable fixture with the same binarycreator, config and
   packages, passing `-r <fixture-stage>/translations/translations.qrc`.
5. Launch English, Simplified and Traditional Chinese; inspect welcome,
   target selection, components, license navigation, ready, installation,
   completion and maintenance dialogs. Verify QtBase buttons/file dialogs too.
6. Exercise all six directed language switches, repeated selection/no-op,
   Back/Cancel and restart failure. Preserve target paths containing spaces,
   Chinese, quotes and trailing backslashes, plus existing proxy/offline
   arguments and explicit `--`. Check that no second installer survives and
   no install/uninstall action occurs merely by switching language.
7. Capture localized component metadata and screenshots, log the precise
   source commit/tool versions/hashes, and then decide whether default
   packaging may enable the third entry.

Locale mapping now distinguishes `zh_TW`, `zh_HK`, `zh_MO` and `zh_Hant`
from Simplified Chinese; language selection emits canonical `zh_TW`.
The pure mapping functions were exercised in JavaScript only. PowerShell,
Qt Linguist, binarycreator and Windows GUI checks have **not** been run in
the connector-only development environment. These steps are a pending test
plan, not a recorded pass. The restart failure message now lists only the languages present in the
staged selector, with matching English, Simplified and Traditional source keys.

Review checkpoint: all 714 messages retain exact source/context inventories;
16 plural messages each have one Traditional Chinese form; placeholders and
rich-text tags agree. Cryptographic hashes are described as 密碼學雜湊值, not
password hashes. The six direction argument-construction cases and locale aliases
passed 35 assertions in a JavaScript sandbox. The checked-in Node wrapper and
PowerShell staging validation have not yet been run on an executor.

### Actual Qt script-engine regression target

The existing `InstallerScriptQtEngine` CTest target now includes the same
35 language-direction/locale assertions in addition to its original restart
and replacement guards. This is preferable to treating a Node result as IFW
evidence: IFW uses QJSEngine and its JavaScript bindings differ.
In an existing Qt test build, build target `installer_script_test`, then run:

```text
ctest --test-dir <build> -C Release -R ^InstallerScriptQtEngine$ --output-on-failure --no-tests=error
```

Use the configuration actually built (for example RelWithDebInfo instead of
Release). The test uses production script source and mocked process/UI calls;
even a passing Qt result must not substitute for the disposable Windows wizard
and real restart matrix above. No new build has been dispatched for this edit.
