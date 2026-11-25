# BIN curve visibility reproduction (2026-10-20)

Status: release-blocking observation; a production fix and positive final-package
regression checks are still required. Import-log and unresolved-path checks alone
are not sufficient evidence that a plotted curve has visible samples.

## Exact candidate

- Source: `743341ba8c31efe593fe7b9636a03bb104603378`.
- Candidate workflow run: [39364094473, attempt 1](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/39364094473).
- Linux package artifact: `12239413591`; archive SHA256
  `87c3c5ee0e9ba46ab54f45597c2eb735dae74103e1af60bb390f3892dce1765c`.
- Original AppImage: `PlotJuggler-4.0.0-zh.1.rc.1-x86_64-zh-CN.AppImage`,
  SHA256 `855f59bcb58a73b2b74e8749b002dac870809efa699e4734879b2dfba9a74d36`.
- Real BIN: `tests/logs/00000001.BIN` from the pinned plugin, SHA256
  `28dcbac522ceb75eee10f6af37b0d6e342c1dc79e2be1a9f766fe18a14336766`.
- Plugin gitlink: `0cc7cc10a25af3cb2ab122861b9be4fc01c99da5`.
- Original Ubuntu 22.04 clean-install report: artifact `12240219080`, ZIP SHA256
  `dbf017bbd668e38650df523de11616c5f0cb6f10a38d0c63506bab83bbf1993c`.

## Reproduction

1. Extract the original AppImage without changing its binaries. Use a fresh
   HOME/XDG configuration and launch its AppRun with `--language en_US --nosplash
   --layout original.pj4.xml`; put the real log beside the layout as `飞行日志.BIN`.
2. Wait for the log to report `ArduPilot BIN: imported 1940 numeric series`.
   The source tree exists, but the plot is blank, its vertical axis remains -1..1,
   and Zoom Out All does not reveal the curve.
3. Save the current layout before altering its curve. The saved XML contains
   `/RCOU`, field `C1&#x9;[us]`, dataset identity and a normal visible curve;
   it has no usable saved viewport. This rules out a missing curve attachment
   in this reproduction. The fixture structure matches the application's schema.
4. Open the right curve panel: `RCOU/C1 [us]` is already listed. Delete only that
   curve, then drag the same C1 field from the dataset tree to the same plot.
5. The waveform now appears immediately; Zoom Out All frames approximately
   28–81 seconds and 1000–1440 microseconds, without re-importing the file.

The original CI screenshot and an independent desktop reproduction both show
blank initial plots. The reattached screenshot below uses the same original
AppImage and BIN bytes, on Debian 13. This desktop reproduction is diagnostic;
it does not replace the clean-install evidence for the eventual release.

## Evidence and current interpretation

- [Original clean-install screenshot](initial-ci-en_US.png)
- [Same original package after removing/re-adding the curve](reattached-real-curve.png)
- [Input fixture](original.pj4.xml)
- [Layout saved while the plot was still blank](saved-empty.pj4.xml)
  (only the absolute plugin filepath has been made relative for reproducibility).

The observations demonstrate that numeric samples were imported and are
renderable. The current hypothesis is a missed cache invalidation/publication
when an adapter is created during progressive file import. This is not yet a
proven line-level root cause. A fix must retain the real BIN, exact plugin checks,
strict ROS 2 prerequisite exception, and Chinese/English visual review; it must
also assert attached curves, non-default finite viewport bounds and real finite
samples in the final package.
