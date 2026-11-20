# 4.x 上游同步审查：2026-11-17

> Historical pre-commit validation record. The subsequent independent candidate and CI plan
> are recorded in [SYNC-CANDIDATE-20261117.md](SYNC-CANDIDATE-20261117.md); statements
> about an uncommitted worktree below describe that earlier stage.

状态：独立工作树的 27 个文本冲突全部解决，尚未创建合并提交或推送。
本地 SDK 元组已统一为官方 1.0.1，CSV #397 / Log #391 三份实际补丁已验证并接入构建。
完整应用、Windows、WASM 与最终包尚未验收，不能据此合并或发布。
详见 [本轮真实候选验收](SDK101-CANDIDATE-VALIDATION-20261117.md)。

## 精确边界

- 本仓开发与稳定：`1613eaec28e7c4aee13f7efc72f5e2b2d73a35ae`。
- 上游 `PlotJuggler/PlotJuggler main`：`5002da40a6499cb99c1073d5b8c611f1e825cb4b`。
- 开发线缺少 64 个上游提交；镜像 `main` 为 `8800f77ef1ca5ace1d7819d29804e6b209c579a1`，缺少 11 个。
- 本地审查分支：`zh-CN-4.x-feat/upstream-main-audit-20261117`。
- 独立工作树：`/workspace/PlotJuggler-zh-CN/.worktrees/product-sync-audit`。
- 无修改的 3.x 稳定和开发：`aa30f5a7759159b0efcb402496759d05fe482384`。

#70 已正常追加修复提交 `a1fcdb3cd2b821fdc535ff34c3af6dc63786c092` 并推送原分支，
PR 保持 draft。PR run `44043553289` 和 push run `44043546336` 均已 completed/success，
两者 API 的 head_sha 均为该提交。PR run 的 Linux job `133903646940` 执行 777 项测试
（24 skipped），Windows job `133903647400` 执行 775 项（32 skipped），无失败；
原生构建按工作流条件 skipped。本地 SDK 7 项、同步 35 项、release policy 5 项、
test.sh 入口 7 项通过，真实 SDK 归档/版本/许可证哈希和变更文件 pre-commit 通过。
本地 broad suite 初次受缺少 Xvfb 和 umask 0077 影响，Debian 测试在 umask 022 下
17 项复测通过；完整 Linux 源码结果以该新提交的 CI 为准。

试合并产生 **27 个冲突文件、68 个冲突区块**，其中 4 个文件属于 `.github`，
其余 23 个涉及产品、依赖、资源、测试或版本。不能用 #70 的 workflow 保留规则代替产品审查。

## 已解决的依赖决策

本地 Conan requirement/recipe lock、CMake 来源与归档哈希、host-sdk-source.json、
来源与许可证断言统一为 SDK 1.0.1 / ffd749ab343c3211b5100f124f6c873667b82629。
真实归档和 Conan export 验证通过。APBIN gitlink 及其独立 SDK 0.34.1 默认值不变，
宿主复用路径单独记录为 1.0.1。原生 CSV 仍使用独立 SDK 0.34.1，其补丁与哈希同步更新。
WASM 598e9662 来源保留，仅应用逐文件哈希验证的 #397/#391 修复，未整批升级官方插件来源。
[精确 SDK/API 契约](SDK101-INTEGRATION-CONTRACT-20261117.md)记录依赖与剩余门禁。

## 冲突处理矩阵

| 范围（文件数） | 合并方案 | 必须保留与验证 |
|---|---|---|
| `.github/workflows/{appimage-builder-image,linux-appimage-release,macos-release,wasm-ci}.yml`（4） | 保留可信本地 workflow 策略；上游构建所需步骤另做逐项审查 | 不引入上游发布、Depot 付费 runner 或新增写权限；不只处理这四个冲突而遗漏无冲突合入的 workflows |
| 根 `CMakeLists.txt`、`conan.lock`（2） | 已成组统一到经验证的 SDK 1.0.1；审查自动合入的 `conanfile.txt`、nanoarrow 0.9、系统依赖模式 | 源码 URL、哈希、recipe revision、构建版本完全一致；不只选择 ours 或 theirs |
| `versions.env`、`README.md`（2） | 确认实际 4.2 功能/插件最低版本后选择显式汉化开发版本；更新安装和开发状态说明 | 不把上游 `4.2.0` 直接当汉化正式版；旧 Release、标签、资产、Latest 不变 |
| `pj_app/CMakeLists.txt`（1） | 同时编译本地 AppProfile 与上游 BundledFont，审查新的静态插件注册生成流程 | 独立测试配置、Windows RC 编译参数、中文路径、原生/WASM 目标划分 |
| `pj_app/src/FileLoader.cpp`（1） | 接纳上游 `name_filter` 参数；默认 filter 仍使用本地插件显示翻译 | 自定义 side-file filter 不被覆盖；默认过滤器、中文路径、浏览器布局侧文件回放 |
| `pj_app/src/MainWindow.cpp`（1） | 保留 `openExternalUrl` 及汉化/上游双问题入口，整合上游菜单变化 | AppImage 外部 URL 环境处理；翻译提取；稳定 objectName |
| `pj_app/src/{Splashscreen.cpp,Splashscreen.h,main.cpp}`、`resources/{CMakeLists.txt,resources.qrc}`（5） | 合并本地启动模式迁移与空池 fallback；保留 CJK fallback；协调上游静态字体与中文字体资源 | 上游把英文 meme 移入桌面专用 `memes.qrc`，不能误删本地汉化池或所有原 PNG；保留原生 big-resource/PIC/资源注册断言 |
| `pj_marketplace/helper/main.cpp`、`src/core/ExtensionManager.cpp`、`src/ui/marketplace_window.cpp`（3） | 统一上游 UTF-8 路径 helper，保留本地显示元数据与可翻译诊断/Changelog | Windows 非 ASCII 安装路径、回滚诊断、HTML escaping；不得用硬编码英文替代 tr/translate |
| `pj_runtime/src/{ExtensionCatalogService.cpp,PluginRuntimeCatalog.cpp}`（2） | 接纳上游结构化 `reportAt` 与 UTF-8 路径机制，同时保留本地种子迁移/来源判定 | canonical store/staging 同文件系统、managed/bundled 优先级、来源签名、中文路径、DLL 生命周期 |
| `pj_runtime/tests/{plugin_runtime_catalog_test.cpp,plugin_runtime_catalog_widget_test.cpp}`（2） | 保留本地受控目录和 Windows 子进程退出后清理语义，吸收上游并发隔离测试意图 | 不整文件换成 QTemporaryDir 以丢掉所有权和 DLL 清理约束 |
| `pj_datastore/{CMakeLists.txt,tests/regression_test.cpp}`（2） | 保留本地启用的当前 ABI 读写回归；整合 nanoarrow target 和批量行数断言 | 不恢复上游“v4 migration 暂停测试”的注释作为功能降级；Debug/throws/Release 分支分别正确 |
| `pj_dialog_host/tests/widget_binding_test.cpp`、`pj_widgets/tests/file_dialog_test.cpp`（2） | 合并两侧仍有调用的 includes 与测试 | 字体、对话框 footer、文件选择异步/取消、真实窗口与路径回归全部保留 |

注意：无文本冲突不代表行为兼容。尤其需要复核上游 `#1588` 的桌面插件打包覆盖、
`#1538` 的浏览器 meme 排除、`#1544` 的字体策略、`#1589` 的 SDK 升级，以及
本地已经启用的 ABI、真实资源和中文路径测试。

## 本轮实施及三类清单

分类说明：A 为必须保留的本地汉化/布局/可信策略；B 为必须适配的上游接口与依赖；
C 为已形成合并方案但仍需运行时测试裁决的资源、UI、测试与版本。文本解决不等于功能验收。

| 冲突文件 | 类别 | 当前处理 |
|---|---|---|
| `.github/workflows/appimage-builder-image.yml` | A 本地保留 | 已解决 |
| `.github/workflows/linux-appimage-release.yml` | A 本地保留 | 已解决 |
| `.github/workflows/macos-release.yml` | A 本地保留 | 已解决 |
| `.github/workflows/wasm-ci.yml` | A 本地保留 | 已解决 |
| `CMakeLists.txt` | B 上游适配 | 已解决；官方 1.0.1 元组与真实来源验证一致 |
| `README.md` | A 本地保留 | 已解决 |
| `conan.lock` | B 上游适配 | 已解决；官方 1.0.1 元组与真实来源验证一致 |
| `pj_app/CMakeLists.txt` | B 上游适配 | 已解决 |
| `pj_app/src/FileLoader.cpp` | B 上游适配 | 已解决 |
| `pj_app/src/MainWindow.cpp` | A 本地保留 | 已解决 |
| `pj_app/src/Splashscreen.cpp` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `pj_app/src/Splashscreen.h` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `pj_app/src/main.cpp` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `pj_datastore/CMakeLists.txt` | A 本地保留 | 已解决 |
| `pj_datastore/tests/regression_test.cpp` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `pj_dialog_host/tests/widget_binding_test.cpp` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `pj_marketplace/helper/main.cpp` | B 上游适配 | 已解决 |
| `pj_marketplace/src/core/ExtensionManager.cpp` | B 上游适配 | 已解决 |
| `pj_marketplace/src/ui/marketplace_window.cpp` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `pj_runtime/src/ExtensionCatalogService.cpp` | A 本地保留 | 已解决 |
| `pj_runtime/src/PluginRuntimeCatalog.cpp` | B 上游适配 | 已解决 |
| `pj_runtime/tests/plugin_runtime_catalog_test.cpp` | A 本地保留 | 已解决 |
| `pj_runtime/tests/plugin_runtime_catalog_widget_test.cpp` | A 本地保留 | 已解决 |
| `pj_widgets/tests/file_dialog_test.cpp` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `resources/CMakeLists.txt` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `resources/resources.qrc` | C 测试裁决 | 已解决；原生/浏览器验证未运行 |
| `versions.env` | C 测试裁决 | 已解决并保留本地开发版本；4.2 命名待定 |

实际选择：保留完整本地 `.github`，同时编译 AppProfile/BundledFont；FileLoader 接纳
显式 name_filter，空参数才生成汉化过滤器；Splash 保留设置迁移和空池 fallback；
上游静态字体与本地 CJK fallback 并存。原生 big-resource/PIC 与浏览器目标均保留两套
meme qrc，未采用上游删除浏览器图片的行为。UTF-8 helper 迁移到上游公共头及 PJ 命名空间，
保留中文诊断、目录来源/原子 staging 和 Windows 目录所有权测试。

SDK 报告指出的 CSV #397 / Log #391 已整理为三份来源可追踪的独立候选补丁，见
[候选说明](../../packaging/localization/plugin-patches/compatibility-candidates/README.md)。
它们已接入本地构建路径，实际 DSO 回归与来源锁/哈希检查通过；真实宿主和全平台验收尚未完成。

本轮检查：

- Qt **6.12.0 lupdate 完整提取**：简繁各 2154/2154，0 unfinished、0 missing、0 stale；
  新增 21 个源消息并移除 10 个过期项，HTML、占位符、numerus 断言保留。
- 原图目录测试 4、种子身份测试 4、翻译检查测试 11 通过；翻译措辞和发布说明数量复测通过。
- 281 个原有资源图片（包括 PNG/JPEG/SVG 等）逐字节对比 HEAD 全部一致。
- 当前未改 APBIN parser 独立编译并执行 2147 检查通过；真实 BIN 为 1940 序列、444443 样本。
  此项没有测试宿主 ABI 或新 APBIN 候选。
- 三份补丁 SHA-256 与原生 CSV 重新应用后的四个结果文件哈希一致；WASM 两补丁精确基线可应用。
- 最新 Python 全套 777 项、53 skipped，零 failures/errors。先前锁文件、版本断言、Xvfb
  问题均已处理。来源/branch 检查通过；未削弱真实性、哈希、许可证或负例断言。
- 三份实际补丁在 SDK 1.0.1 下：原生汉化 CSV 8 CTest/128 用例；WASM 来源的原生
  CSV/Log DSO 与 SDK null-sample 7 CTest/138 用例均通过，包括 Qt 6.12 实际 Widget DSO。
- 原生 CSV 独立 SDK 0.34.1 的 -O3/-Werror 初次构建有旧 SDK GCC 警告失败；-O2 保留
  -Werror 后 128 用例通过。失败日志保留，不等同默认优化级别的发布构建通过。
- 完整应用、Windows、WASM 和最终包未执行。26,000,000 B 是保留的独立汉化预算约束，
  不是本次已测包大小。原始图片/旧 WASM 候选/预算门禁保持。

## WASM 候选保留及后续次序

以下提交仍可由远端分支到达，本轮未删除、改写或导入它们：

- `80a97e12d1f8faec72202a486cc6d12ff0341406`：净日志绑定/延迟恢复修复。
- `d0734db9`：JPEG、字体、布局组合与独立 `scripts/wasm_localized_size_budget.mjs`。
- `54783848d17ae0a6baaa91fe5aa6222b6399f957`：实际 Qt JPEG/atlas 视觉探针。

保留分支包括 `zh-CN-4.x-feat/wasm-log-restore-net`、`zh-CN-4.x-ci/log-net-native`、
`zh-CN-4.x-ci/wasm-localized-26mb`、`zh-CN-4.x-ci/wasm-jpeg-visual`。

先解决产品同步依赖，再对 `80a97e12` 逐个核对与新上游的等价性和生产调用，
随后独立重验 `d0734db9`，最后运行 `54783848` 的视觉读回。
汉化总包预算 **26,000,000 B** 只由独立汉化检查使用，上游预算保持自己的真实基线。
原 PNG、许可证、历史、source-qualified 绑定断言和实际图像/布局断言全部保留。
旧候选通过记录不等于新同步 head 通过。

## 可执行步骤与门禁

当前工作树已完成冲突编辑和来源一致性修复，仍保留 MERGE_HEAD，尚未提交。
不要再次启动 merge、覆盖已解决差异或把测试通过解释为允许完成合并。
先执行剩余真实宿主、Windows、WASM 与最终包门禁；真正完成集成前，再将
upstream-baseline.json 的权威 ancestry 字段更新到该次实际集成父提交；当前 pending_sync
字段明确记录目标，避免未提交工作树伪装成已经完成的合并历史。

按矩阵逐项编辑、审阅和 stage，不用整树 ours/theirs。可信 `.github` 保留应针对
合并前的完整目录，并审查所有自动合并文件；若 #70 先进入开发，重新以那个真实开发提交为基线。
在提交前更新 `docs/localization/upstream-baseline.json` 的来源与未验状态。

轻量检查顺序：

```sh
python3 scripts/check_branch_name.py zh-CN-4.x-feat/upstream-main-audit-20261117
python3 -m unittest discover -s tests -p 'test_host*.py' -v
python3 -m unittest discover -s .github/sync -p 'test_*.py' -v
python3 -m unittest discover -s .github/release_policy -p 'test_*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/check_localization_provenance.py
python3 tests/check_translations_4x.py --catalog-only
git diff --check
```

源码检查须在 Linux/Windows 精确新 head 重跑。完整翻译覆盖另用 Qt 6.12 lupdate，
catalog-only 不能代替。原生验证优先语言/资源独立目标、BIN parser 和 ABI 目标、
`FileLoader`/catalog/widget bindings/字体/启动图/布局回放相关测试，先用 `ctest --show-only=json-v1`
确认实际选择；不要盲跑全量构建。库 ABI 变化最终仍需要双平台原生验证，源码检查不能替代。
WASM 使用独立汉化预算和绑定/视觉探针的新 head 证据。未通过前不晋级稳定、不发布、不另建 PR。

## 镜像 403：已有事实与剩余诊断

`44041358097` / job `133896535619` 日志显示：

- 实际 `GITHUB_TOKEN` 权限为 `Contents: write`、`Metadata: read`。
- main-3.x 已一致；main 的 11 个上游提交是快进关系。
- `PATCH /repos/reliable-ly0411/PlotJuggler-zh-CN/git/refs/heads/main` 返回 403，未重试。
- 此范围修改 `.github/workflows/sanitizers.yml` 与 `.github/workflows/wasm-ci.yml`。
- 读取有效 rules 返回 `deletion` 和 `non_fast_forward` 两项。
- 读取经典 branch protection 被 GitHub 拒绝：HTTP 403 `Resource not accessible by integration`。
  本轮没有重试该操作，没有更换凭据、扩大权限或发起 mirror PATCH。

Workflow 修改权限是合理怀疑，尚非已证实根因；经典保护/更上层策略的细节仍不可见。
旧控制器丢弃响应 message，因此现有日志不足以判定。#70 的有界、脱敏错误消息可改善后续诊断，
但它仍未合入默认稳定分支。下一步由正常维护流程决定该诊断代码的部署，然后检查一次真实失败的
服务端 message/请求证据；不要为了诊断立即重试写入，也不要将已成功的个人凭据推送当作
Actions token 能力证明。任何凭据权限变更须另案处理，本报告不建议或执行该变更。

## 保存的本地证据

目录：`/workspace/scratch/plotjuggler-sync-20261117/`。

- `product-sync-conflicts.json`：两端 SHA、全部冲突路径及区块数。
- `product-sync-merge.log`：实际试合并输出。
- `product-conflicts.diff`：全部 combined conflict diff。
- `product-sync-build-conflicts.diff`：构建/锁文件/版本/资源冲突。
- `product-sync-status.txt`、`merged-index-files.txt`：包括自动合并文件的状态。
- `product-sync-upstream-commits.txt`：64 个上游提交清单。
- `resolved-product-sync.diff`：当前已解决文件相对 HEAD 的可审核差异（含二进制）。
- `remaining-dependency-conflicts.diff`：前一阶段两个依赖冲突的历史证据，现均已解决。
- `product-sync-*-final.log`、`product-sync-parser.log`：本轮真实检查输出。
- `verification-summary.json`：精确边界、状态、测试和图片/补丁哈希结论。

本工作树完成了上述限定 DSO/源码验证，没有原生完整构建、Windows 或 WASM 验收；独立报告证据另列于契约文档。
没有产品合并提交或远端产品分支更新。
