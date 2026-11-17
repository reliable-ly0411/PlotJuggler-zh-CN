# Native regression follow-up, 2026-11-17

The input is candidate `3c471fc572bb77d06d43f0f77cd3a27bb6338a0d`,
packaging run [44098684851](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44098684851).
Both platforms built the application, ran the real ArduPilot import regression,
and passed `Prepare verified native feedback inputs`. Neither produced an
accepted package: native regression failures stopped the later packaging gates.

The fixes are based on `2459f63bf38dc0b7eddc2e8588197672afdd0ad8`, which also
contains the separately reviewed browser language assertions. No production
source, SDK/plugin pin, resource, budget, or workflow assertion changes here.

## Original failures and decisions

| Test | Linux | Windows | Resolution |
| --- | --- | --- | --- |
| `PluginDisplayMetadataTest::installedApbin` | failed | failed | Compare the admitted DSO version with the locked baseline, retaining fixed ID, author, license, repository, website and all three display languages. |
| `ScrubberBase.ReturnCommitsAndClosesEditorWithoutReopening` | failed | passed | Wait for the exposed window to become active before sending keyboard input. Require initial focus as well as all original commit, close, focus-return and reopen assertions. |
| `PreferencesLanguageTest.MinimumSizeKeepsTranslatedAppearanceControlsReachable` | failed | failed | Test the actual minimum width introduced by upstream `18ff9b061a59f3dc7dfe5af8290f6bf0986ffaa5`; retain the 420 px lower bound, 300 px height, scrolling, label/field geometry and English/Simplified/Traditional coverage. |
| `SplashMemePool.EmptyPoolFallsBackToTheSeriousSplash` | failed | failed | Check the actual English image pool, not all files including `zh_CN.json`. Explicitly request memes in English, check the nonempty serious fallback and its dimensions, then verify the original pool is restored. Use private settings. |
| `RecipeGraphTest.PythonScriptIsCompiledOncePerRevision` | passed | failed | Retain shared ownership of the original compiled handle across replacements. Comparing a freed raw address allowed allocator reuse to look like an unchanged handle. Revision, same-input reuse, changed-input identity and compile-event assertions remain. |

Linux: 6,257 CTest entries, four failed. Windows base suite: 5,743 entries,
four failed; later QRhi 217, native-window 2, widget-regression 9 and
range-slider 4 entries passed. The latter subsets are not an additional count
of unique tests. Linux X11/Wayland lifetime and all package/clean-package gates
after the failed step were not executed.

The generated APBIN identity is `ardupilot-dataflash` / `1.3.0-pj4.rc.1`,
matching `upstream-baseline.json` and source pin
`fc6065fd64305479946552a757d78e6afdd2c506`. The failed metadata assertion alone
still expected `1.2.0-pj4.rc.1`. The Linux feedback receipt binds the actual DSO
to SHA-256 `6af38f2c259f8d9bdbf00e471a64e3d545a6a277c13b49001a68610199f831c6`.

## Local verification and limits

Cloud-only focused builds use Qt 6.12.0 and SDK 1.0.1 source
`ffd749ab343c3211b5100f124f6c873667b82629`, with `-Wall -Wextra -Werror`.
The metadata/SDK harness uses `-O2 -DNDEBUG`; it does not reinterpret the
previous unrelated old-SDK `-O3` diagnostic as a passed check.

- Real APBIN DSO plus marketplace admission/UI: original assertion reproduced
  the exact version mismatch; repaired suite passed 28/28, with no skips.
- Actual splash sources/resources: original suite 9 passed / 1 failed;
  repaired suite 10/10. No image file or QRC entry was removed.
- Actual scrubber implementation: original isolated X11 case failed both
  Return and Enter focus checks; repaired case passed. Offscreen before/after
  both passed; the repaired full scrubber suite passed 8/8. This distinction
  matters: offscreen alone did not reproduce the CI failure.
- Modified recipe test translation unit compiled with the real SDK headers
  and `PJ_PYTHON_TEST_PROBE`; this is compilation, not execution of embedded
  Python. Full runtime execution and the actual Preferences dialog regression
  require the next native CI run.
- Python source suite: 801 discovered, 31 skipped, initially one environment
  error. `dpkg-deb` rejected a temporary `DEBIAN` directory created with mode
  0700 under process umask 077. The unchanged failing test passed under umask
  022. The original failure and focused replay are retained separately.
- Pre-commit checks and `git diff --check` passed after formatting.

Evidence is retained under cloud scratch
`/workspace/scratch/pj-sdk101-validation/native-regressions/`, with original
CI reports in `native3c-linux-reports/` and `native3c-windows-reports/`.
Downloaded report ZIPs were verified against the GitHub artifact digests:

- Linux `14339594584`: `c31f3cb177bd9a8d694bf1fa0b07c7b33ac72ab9ed5d234c6b139641035c1a57`.
- Windows `14340889854`: `81f019f7ac367fa41343f6d864bd621e8b908f84d82242590ed0c3ec4472f9ff`.

These focused results do not establish full native, browser, GUI, installer,
marketplace-installation or final-package acceptance. Stable/development
promotion, publication and tag changes remain outside this candidate step.
