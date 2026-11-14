# Windows dependency source-time policy

The 3.18.1 product candidate uses the source-time fixes validated in diagnostic run
43564213375 (commit 825e84b938e096ebef677802ab603d629c595b98).
Two independent native Windows caches produced byte-identical original
DataLoadParquet, ToolboxMosaico, and ProtobufParser DLLs with no prohibited paths.
This is limited evidence, not approval of the complete product or release.

- Qt RCC receives the checked-out source commit timestamp through SOURCE_DATE_EPOCH
  and QT_RCC_SOURCE_DATE_OVERRIDE, before resource generation.
- The exact lock-pinned mimalloc 2.2.4 recipe's diagnostic version banner replaces
  volatile __DATE__/__TIME__ with “reproducible build” / “time not recorded” before
  compilation. Allocation behavior is unchanged.
- The exact-path Conan hook and its full source digest participate in package
  identity; unknown recipe source patterns fail closed.
- No DLL bytes are rewritten, normalized or excluded from existing privacy checks.
- Full native CTest suites, package identity, dependency notices, and seven-package
  verification remain required. This change does not publish automatically.
