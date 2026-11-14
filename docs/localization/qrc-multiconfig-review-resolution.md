# QRC review wrapper resolution

## Root cause and source basis

The rc.17 collector found the QCodeEditor 147-byte generated wrapper but treated its include as relative to the wrapper directory. That is not CMake AUTORCC's multi-configuration layout. The official implementation puts the public wrapper under `<autogen>/<checksum>/` (or `<checksum>_<config>/`) and the compiled resource source under the configured include directory, normally `<autogen>/include_Release/<checksum>/`.

Source: [CMake v3.31.6 cmQtAutoRcc.cxx](https://github.com/Kitware/CMake/blob/v3.31.6/Source/cmQtAutoRcc.cxx), `InitFromInfo`, `MultiConfigOutput`, and `GenerateWrapper`.

## Cloud reproduction, 2026-11-13

A real CMake 3.31.10 Ninja Multi-Config project with Qt 6.11.1 Core, AUTORCC and five aliased resource files was configured and built in Release. It generated:

- `qrcprobe_autogen/EWIEGA46WW_Release/qrc_qcodeeditor_resources.cpp`: 147-byte wrapper.
- `qrcprobe_autogen/include_Release/EWIEGA46WW/qrc_qcodeeditor_resources_CMAKE_.cpp`: actual generated source.

The repaired resolver selected only `cmake-release-include`; raw wrapper and actual source were retained separately. The existing RCC parser accepted version 3 and exactly five file timestamps. This reproduces and checks the layout with a real generator, not just hand-written wrapper strings. It is not a Windows Qt5 product rebuild or DLL identity approval.

## Boundaries

The additional candidate is restricted to the same `_autogen` directory, matching ten-character checksum, matching resource filename and the Release configuration used by the Windows product workflow. Both old and newer CMake public-wrapper layouts are recognized. There is no recursive include search, cross-target/configuration fallback or choice between multiple existing candidates. Existing symlink, escape, cycle, size and depth limits remain. Diagnostic records contain fixed layout labels and hashes, not private paths. Even failed resolution now preserves privacy-scanned wrapper evidence for review.

The production DLL identity/license/privacy allowlists are unchanged. The real rc.17 QCodeEditor generated source was not present in its artifact; the next isolated collection must still prove its exact array location and six combined resource timestamp offsets in the actual DLL. Unit checks cover direct includes, both CMake layouts, ambiguity, missing and foreign-config sources, unsafe paths, cycles and evidence export.
