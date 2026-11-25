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


## Opt-in Traditional Chinese Windows installer QA

The downstream Traditional Chinese standard IFW dictionary preserves all 700
source entries from IFW 4.10.0 and was carried from repository commit
44ff7fce17e8f07229bf695c7f247f2e86cdcb97. Keep this modified TS source, the upstream
license and corresponding source notice with redistribution. The separate
component dictionary covers 14 PlotJuggler installer messages. Neither changes
the application's own language or translations.

The normal installer still has two choices. To stage the third choice explicitly,
use a private Windows test workspace and pass -ExperimentalTraditionalChinese
to build_windows_installer.ps1 with an already-built app and an explicit, nonexistent -StageDir.
This opts into an offline installer whose file name ends in -ifw-zhtw-qa.exe;
clean release naming and update repository arguments are disallowed. The
builder checks IFW 4.10.0. The staging script validates the selected Qt version and requires that kit's nonempty
qtbase_zh_TW.qm; it checks catalog structure, combines the IFW and component
catalogs, adds the matching QtBase resource, then adds the third dropdown entry
only in the staging copy. Missing dependencies fail rather than silently hiding
the language while claiming a three-language candidate. Do not add a fixed
Translations setting to config.xml: it bypasses IFW's --lang choice.

Static checks:
  python3 scripts/test_ifw_traditional_catalog.py
  node scripts/test_installer_language.js

Native validation still required: actual pinned Windows IFW, six language
switches between zh_CN, en_US and zh_TW, a disposable folder with synthetic
payload, PID/restart argument and target retention, actual standard/component
pages in the selected locale, restart failure and existing install guard behavior.
Production activation and release eligibility are separate.
