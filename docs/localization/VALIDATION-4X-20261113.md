# 4.x 开发快照定向原生验证 — 2026-11-13

## 源码与合并范围

受测开发提交为 `0b4b4c29354f471d26e1b6321d72cc62e06ccebe`，tree 为
`0817a1d2e37a897075cbb46da254224149e99371`，应用版本为 `4.1.0-zh.1.dev.3`。
Qt 为 6.12.0；SDK 为 0.40.0，采用未合并 PR #226 的固定修复快照
`52cdf329adf6af3513e190fe0f8b86f19f17b051`，不是未修改的官方 SDK 发行包。
来源与许可证门禁保持不变。

本主题分支保存从稳定提交 `5ef98a97a5e08ab32482d9049bb45df102c99d05`
合并上述开发提交的提案。产品源码、构建配置、工作流、许可与子模块引用均与受测开发提交一致；
相对该提交只有本报告及两份首页文档不同。稳定线尚未晋级，正式标签
`v4.1.0+zh.1` 仍指向 `0113492d7a7f96e486de1f9adcde6e43893ab630`。
本提案不创建成品、标签或 Release，不替换既有 Latest。

## 定向结果

本轮围绕新增功能及回归风险验证，没有执行全量现代应用测试矩阵。

| 范围 | 实际结果 | 边界 |
| --- | --- | --- |
| Ubuntu 六个必要目标增量编译 | 163/163 步通过，exit 0 | 包括真实应用及运行时语言、profile、插件反馈测试目标 |
| Ubuntu DataWriter、SDK 桥接、插件目录与 profile | 132 个 CTest：131 通过、1 跳过、0 失败 | 唯一跳过要求 Debug 或 PJ_ASSERT_THROWS；当前为 RelWithDebInfo |
| Ubuntu 应用、三语、真实 BIN、APBIN/FFT | 22/22 个 CTest 通过 | 合计新增定向 CTest 为 153 通过、1 跳过，不能与容器内 GoogleTest 数混加 |
| 严格翻译检查 | 简繁各 2113/2113；缺失、陈旧和 unfinished 均为 0 | 使用固定 Qt 的真实 lupdate |
| 三语真实 BIN 恢复 | 各导入 1940 条 numeric series，初始曲线有有限可见样本，应用正常退出 | 原始解析警告保留 |
| Qt 测试截图 | 24 张逐张检查，未见明显乱码或控件遮挡 | 是测试窗口及局部控件抓图，不是安装包桌面验收 |
| 先前完成的独立语言及 SDK 原生测试 | i18n 26/26；SDK 105 个 CTest 通过 | SDK 容器内另有 1223 个 GoogleTest；保留既有结果，没有重复全量运行 |
| 合并提案源级专项 | 19 项通过；发布触发策略 5 项通过 | 对应报告加入前的两份文档合并树；此后仅调整未晋级状态说明及加入本报告 |
| Windows SDK Unicode 定向编译 | MSVC x64、RelWithDebInfo、警告视为错误；目标及依赖 DLL 构建成功 | 使用已有工具；未安装 Qt6 或新工具链；不是完整 Windows 应用构建 |
| Windows 两项原始 SDK GoogleTest | **1 通过、1 失败、0 跳过；CTest 容器失败，exit 8** | 见下节；未重试为通过，稳定晋级仍待解决 |

较早启动的全目标编译在 823/1285 步按缩小后的测试范围中止；没有编译错误结论，
全量 CTest 未启动。定向 Linux 构建完成后的编译与测试输入哈希均已核对。

## Windows 原始失败与复现条件

在 Windows 10 Pro 19045 的非交互 SYSTEM/session 0 中，使用已有 MSVC 14.44.35207、
CMake 3.31.8、Windows SDK 10.0.22621.0、Python 3.12.7，以及新隔离的中文空格构建路径。
固定 SDK 源码和 GoogleTest 1.17.0 从已核验归档展开。fmt 12.1.0、fast_float 8.1.0、
nlohmann_json 3.12.0 仅复用有清单和许可证的头文件；GoogleTest 和全部 SDK 测试 DLL 在 Windows 本机编译。
未使用 Windows native-kit 的旧批准闭包。

目标与选择器为：

```text
cmake --build <sdk-build> --config RelWithDebInfo --target plugin_catalog_test --parallel 1
GTEST_FILTER=PluginCatalogTest.UnicodeFailureDiagnosticsPreservePath:PluginCatalogTest.UnicodeExtensionPathLoadsOnWindows
GTEST_OUTPUT=xml:<中文空格测试根>/google-tests.xml
ctest --test-dir <sdk-build> -C RelWithDebInfo -R ^plugin_catalog_test$ --no-tests=error --output-on-failure --timeout 120 --output-junit <测试根>/ctest.xml
```

实际配置保留 `/utf-8 /DWIN32 /D_WINDOWS /EHsc`，并启用 `PJ_WARNINGS_AS_ERRORS=ON`。
`PluginCatalogTest.UnicodeFailureDiagnosticsPreservePath` 通过。
`PluginCatalogTest.UnicodeExtensionPathLoadsOnWindows` 在 `copy_file` 抛出“系统找不到指定的路径”异常：
源为构建目录下 `pj_plugins/RelWithDebInfo/mock_data_source_plugin.dll`，目标为临时目录下含中文的 `unicode_plugin.dll`。
收尾时源 DLL 实际存在，且为 AMD64 PE；不能把异常直接归因为缺少编译产物。
GoogleTest 随后无法打开中文根目录的 XML 输出路径，进程以失败结束。

这是未解决的环境、Unicode 路径或测试夹具问题；现有日志尚不能确立产品根因。
原始失败保留，没有修改源码、系统编码、执行策略或用 ASCII 路径掩盖结果。
此后没有重跑测试。93 项清单输入、SDK 的 489 个源码文件及 GoogleTest 的 250 个源码文件
收尾哈希均与输入一致。

在该执行前还记录了两次控制器配置失败：命令行对 vcvars 的引号处理错误；
以及直接设置 CMAKE_CXX_FLAGS 时覆盖默认异常选项。两者均发生在选定测试执行前，
后来只在新的隔离构建根修正控制器配置，未改产品或测试源码。

## 未覆盖与后续条件

- Windows Qt6 应用、交互 GUI、Windows 安装器，以及两平台新成品和干净机验收未运行。
  当前 Windows 已有 Qt5 工具不能充当 Qt6 构建环境；已有会话与其他版本程序保持原状。
- 没有执行全量 CTest、完整 RHI/2D/3D、Wayland、物理 GPU、原生 picker/portal 交互或大型双窗口生命周期测试。
- Ubuntu 宿主是 24.04、glibc 2.39；主 ELF 最高直接 GLIBC 需求为 2.38，不能证明 Ubuntu 22.04 / glibc 2.35 兼容。
- Windows 专用 native-kit 仍为 `pending-modern-native-review`。其 82 项旧源证据失配未被删除或重算为批准。
- `docs/localization/upstream-baseline.json` 顶层历史 `host_sdk_version` 仍写 0.39.0，
  与当前固定 SDK 0.40.0 存在元数据歧义；它与受测开发提交相同，未在本提案暗改。实际 SDK 以锁文件和固定来源为准。

稳定晋级必须先明确 Windows 定向失败的原因和处理结果；失败、跳过和未运行不能合并为通过。
后续只补新增功能与回归风险所需覆盖，不以恢复全量测试替代定位。

## 证据索引

Linux 完整定向记录为 `TARGETED-NATIVE-REPORT.md`、`TARGETED-FINAL-VERIFICATION.json`、
两份原始 CTest JUnit、`TARGETED-PIXEL-REVIEW.json` 和对应 24 张原始截图。
已归档为 `pj4-0b4b4c29-targeted-native-evidence-20261113.tar.gz`，SHA256：
`cd9166f008f14a7dad5c2ef356a1bff025e30762aa8b804de0b4853ec3c37f6c`。

Windows 失败原始输出、两次先行配置错误、CMakeCache、环境范围、输入清单和收尾哈希保存在
`windows-sdk-stop-handoff-evidence.zip`，SHA256：
`c4beb87e8f79c3ce81f46f312c83fa2c3b9d66977d83c716b00261aebcf904ab`。
证据归档与源码历史分开保留，不向 Git 或正式 Release 添加编译树和私人系统资料。
