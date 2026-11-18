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
