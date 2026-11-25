# Completed 4.1.0 diagnostics and recovery archive

These files are historical evidence, not current build or publication entry points.
Do not run the recovery script against GitHub: its release IDs, source hashes,
asset inventories and acceptance inputs refer to a completed historical operation.
Archived workflows are outside `.github/workflows` and cannot trigger Actions.
The relative source layout is retained for review, not as a runnable standalone kit.

| Original branch | Head | Verified completed run | Disposition |
| --- | --- | --- | --- |
| `zh-CN-4.x-ci/release-test-inputs-4-1-0` | `60a41692ca3e3dfd283e60f71f3ae445b2631022` | [42439950954](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/42439950954) | Fixed source/BIN transfer completed successfully; archive only. |
| `zh-CN-4.x-ci/sdk-unicode-ab-696c-r2` | `a792dff5739e1d6e63317db6fbfbcc641f7e1f25` | [42784741091](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/42784741091) | SDK A/B experiment completed successfully; retain probes as evidence, not release acceptance. |
| `recover-publish-v4-1-0-draft-442876072-9666159eeee050cfb8816489488922666df2a708` | `9666159eeee050cfb8816489488922666df2a708` | [43218638173](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/43218638173) | One-shot recovery completed successfully; no further publication is requested. |

All original commits are retained through ordinary merges. The temporary catalog
test trace/catch wrapper is deliberately not applied to the maintained regression:
it adds diagnostic stages without fixing behavior or adding assertions. Existing
production assertions, Unicode fixtures and closure-policy digest remain unchanged.
The diagnostic source can be recovered from its recorded commit.

This consolidation changes no application, translations, versions, dependencies,
active workflows, release tags or asset bytes. It does not finish the separate
3.18.1 investigation or the upstream translation PR.
