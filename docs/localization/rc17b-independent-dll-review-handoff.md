# rc.17b independent DLL review handoff

Read-only audit of source `9f2169a4bf72731672da11b1ae986bbcfccfc41e`, run [43466655277](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/43466655277), artifact `14063001972`, SHA256 `e0bf7fed3ddf1eb9c8f199bf2e9dc6ddec2300e2181aeb704e1313a30659393e`.

## Verified

- Artifact, three raw DLL hashes, wrapper and two generated-source hashes match the manifest.
- Mosaico's actual RCC arrays (66 and 154 bytes) occur uniquely in PE `.rdata` at 13575552 and 13599776. The six exact timestamp offsets are 13575610, 13599834, 13599856, 13599878, 13599900, 13599922.
- A separate PE field reader recomputed canonical hashes using only the existing COFF/debug timestamp fields and the six source-derived RCC fields. Results match the collector:
  - DataLoadParquet: `26fd92b0c4370ee554e6fa85bd8f19339fe60a0cb4cec2aaa1344db2609b5d70`
  - ToolboxMosaico: `d79e7719974535783e5f01009a82547d8c8a837139cbee7265de5454b3e31441`
  - ProtobufParser: `20992485d9ce1e278fdd8034dcf55083045c56d2c9ad7511fddd50e5221af083`
- In-memory candidate identities with empty path-literal lists passed original-byte privacy scanning. The seven original negative cases were independently exercised for all three DLLs (21 rejections). Changes confined to existing reviewed timestamps retained identity. No production policy was edited.

## Not reproducible across rebuilds yet

Compared with rc.16 and rc.17, all three canonical fingerprints differ. DataLoadParquet, ProtobufParser and ToolboxMosaico contain respectively 32, 29 and 362 distinct mapped Conan paths with random cache components. The path sets match after diagnostic-only substitution of those cache components. This substitution was never added to a production fingerprint or scanner.

A finite identity record could cover these exact reviewed artifacts, but would not prove the next rebuild equivalent. Do not chase new hashes through long product runs. First validate stable compile-time path mapping in production, then independently review the resulting identities. Product licensing, source delivery, final package validation and full acceptance remain separate gates.

## Verification-tool correction

`check_metadata` returning an empty marker list is successful for no-path binaries. The real-DLL verification tool previously asserted that list and indexed the nonexistent first path literal. It now treats exceptions as rejection and uses an explicitly synthetic path for negative probes. The original seven probes remain; an eighth identity-independent legacy-style path injection ensures no empty-list record silently inherits an old exemption. Counts are derived from the actual records, not a hard-coded two DLLs/fourteen cases. CLI policy still comes only from the repository.
