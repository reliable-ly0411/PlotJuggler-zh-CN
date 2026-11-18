# APBIN host rebuild with SDK 1.1.0

The host rebuild uses SDK `1.1.0` at
`d65923cd11ab7a822ef7b802523e2fc7b281f515` (archive SHA-256
`57f7c40f672bdfc0d6a6cef18a27361483963e646986ff092c24ff6d87ffb4f9`).
`ardupilot_plugin.sdk_version` and `sdk_source_commit` describe this rebuild,
not the SDK of a previously published standalone plugin archive.

APBIN source remains `fc6065fd64305479946552a757d78e6afdd2c506`.
Its unchanged source manifest SHA-256 is
`f2ef42dc0d80405dbeb7e2d23cf6831f2c5f2a1c846d39b8643af3fff4b5901d`.
The standalone release `v1.3.0-pj4.rc.1`, its release commit, original
SDK 0.34.1 build configuration and archive bytes are unchanged. No plugin
release is created. The host's existing CMake integration supplies the SDK
target before adding `sdk4`, so no standalone APBIN CMake pin is rewritten.

## Executed checks

An isolated Linux GCC 14.2 Release build used the exact sources above,
`-O3`, nlohmann-json 3.12.0, and the existing SDK warning-as-error settings.
Neither source tree was patched for this build.

- `ArduPilotDataFlashParser`: 2,147 checks passed, including a real BIN with
  1,940 series and 444,443 samples.
- `ArduPilotDataFlashPlugin`: 111 checks passed through the built shared library.
- CTest: 2/2 passed, zero skipped.
- ELF export guard: all required entry points present, zero GNU UNIQUE leaks.
- Generated sidecar: ABI major 5; SDK data-source protocol remains 4.
- Main-repository provenance fixtures: 5/5 passed, including rejection of stale
  rebuild SDK versions, mismatched SDK commits, modified checkout bytes and
  incorrect manifest hashes; uniform Windows CRLF checkout still passes.

The native harness follows the production target ordering:

```cmake
cmake_minimum_required(VERSION 3.22)
project(apbin_sdk11_validation LANGUAGES CXX)
enable_testing()
set(PJ_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PJ_BUILD_PORTED_PLUGINS OFF CACHE BOOL "" FORCE)
set(PJ_INSTALL_SDK OFF CACHE BOOL "" FORCE)
add_subdirectory(../sdk sdk)
include(../sdk/cmake/PjPlugin.cmake)
set(APBIN_BUILD_PLUGIN ON CACHE BOOL "" FORCE)
set(APBIN_BUILD_TESTS ON CACHE BOOL "" FORCE)
add_subdirectory(../apbin/sdk4 apbin)
```

Configure with `CMAKE_BUILD_TYPE=Release` and a prefix containing the SDK's
required dependencies, build, then run `ctest --output-on-failure -V`.

## Separate compatibility scopes

Official localized-plugin rebuild locks retain their individual SDK versions
0.20.0, 0.32.0 and 0.34.1. Registry packages and historical provenance are not
rewritten to say 1.1.0. Their final host installation/loading tests are separate
from this APBIN source-rebuild check.

Windows APBIN source rebuild, complete-host GUI and final-package installation
have not been executed by this isolated check. Those gates remain required on
the final integrated candidate; this report is not a whole-product acceptance.
